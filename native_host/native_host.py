# native_host.py
import sys
import os
import json
import struct
from urllib.parse import urlparse

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import database
from core import utils  # Imported for security audit logging


def get_message():
    """Reads the JSON message sent by Chrome."""
    raw_length = sys.stdin.buffer.read(4)
    if len(raw_length) == 0:
        sys.exit(0)
    message_length = struct.unpack('@I', raw_length)[0]
    message = sys.stdin.buffer.read(message_length).decode('utf-8')
    return json.loads(message)


def send_message(message):
    """Sends a JSON message back to Chrome."""
    encoded = json.dumps(message).encode('utf-8')
    sys.stdout.buffer.write(struct.pack('@I', len(encoded)))
    sys.stdout.buffer.write(encoded)
    sys.stdout.buffer.flush()


def extract_domain(url):
    """Extracts and normalizes the exact domain (hostname) from a URL string."""
    if not url:
        return ""

    # Ensure scheme exists so urlparse handles it correctly
    # (in case the user just typed "google.com" in the DB)
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        # Remove 'www.' prefix to ensure strict but fair matching
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain
    except Exception:
        return ""


def main():
    db = database.DatabaseManager()

    while True:
        try:
            msg = get_message()
            if msg.get("action") == "get_credentials":
                url = msg.get("url", "")
                master_pw = msg.get("password", "")

                # --- STEP 1: PROTOCOL & NULL CHECK (THE BOUNCER) ---
                if not url or url.startswith("file://") or url.strip() == "":
                    utils.log_event(
                        "SECURITY ALERT: Blocked autofill request from null/local origin (Phishing Prevention).")
                    send_message({"success": False, "error": "Blocked: Invalid origin protocol."})
                    continue

                # Parse the browser's current active tab domain
                browser_domain = extract_domain(url)
                if not browser_domain:
                    utils.log_event(f"SECURITY ALERT: Could not parse browser domain from URL: {url}")
                    send_message({"success": False, "error": "Blocked: Unparseable origin."})
                    continue

                # Check if master password is correct
                if db.init_db(master_pw):
                    rows = db.fetch_all(master_pw)
                    matches = []  # Store ALL matching accounts

                    for row in rows:
                        db_url = row[1]
                        db_domain = extract_domain(db_url)

                        # --- STEP 2: STRICT ORIGIN CROSS-REFERENCING ---
                        # Instead of a loose 'in' check, we strictly match the parsed domains
                        if browser_domain == db_domain and browser_domain != "":
                            matches.append({"email": row[2], "password": row[3]})

                    if matches:
                        # Send back the whole list of exact matches
                        utils.log_event(f"Autofill authorized and served for domain: {browser_domain}")
                        send_message({"success": True, "accounts": matches})
                    else:
                        send_message({"success": False, "error": "No matching website found."})
                else:
                    send_message({"success": False, "error": "Wrong Master Password."})
        except Exception as e:
            utils.log_event(f"Native Host Error: {str(e)}")
            send_message({"success": False, "error": str(e)})
            sys.exit(0)


if __name__ == '__main__':
    main()