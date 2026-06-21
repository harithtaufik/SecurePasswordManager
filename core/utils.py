# utils.py
import string
import secrets
import random
import hashlib
import requests
import datetime
import os
from zxcvbn import zxcvbn

import config

AUDIT_FILE = os.path.join(config.DATA_DIR, "audit_log.txt")


def check_password_strength(password):
    if not password:
        return "", "SystemButtonFace"

    results = zxcvbn(password)
    score = results['score']

    strength_map = {
        0: ("Very Weak", "red"),
        1: ("Weak", "red"),
        2: ("Medium", "#FFAA00"),
        3: ("Strong", "blue"),
        4: ("Strong!", "green")
    }
    return strength_map.get(score, ("Weak", "red"))


def get_password_score(password):
    if not password:
        return 0
    return zxcvbn(password)['score']


def get_password_details(password):
    if not password:
        return 0, "No password provided", "", "Instant"

    results = zxcvbn(password)
    score = results['score']
    feedback = results.get('feedback', {})
    warning = feedback.get('warning', '')
    suggestions = " ".join(feedback.get('suggestions', []))
    crack_time = results.get('crack_times_display', {}).get('offline_slow_hashing_1e4_per_second', 'Unknown')

    return score, warning, suggestions, crack_time


def generate_secure_password():
    letters = string.ascii_letters
    numbers = string.digits
    symbols = string.punctuation

    num_letters = 8 + secrets.randbelow(3)
    num_symbols = 2 + secrets.randbelow(3)
    num_numbers = 2 + secrets.randbelow(3)

    pw_list = [secrets.choice(letters) for _ in range(num_letters)]
    pw_list += [secrets.choice(symbols) for _ in range(num_symbols)]
    pw_list += [secrets.choice(numbers) for _ in range(num_numbers)]

    random.SystemRandom().shuffle(pw_list)
    return "".join(pw_list)


def check_hibp_breach(password):
    if not password:
        return 0

    sha1_hash = hashlib.sha1(password.encode('utf-8')).hexdigest().upper()
    prefix = sha1_hash[:5]
    suffix = sha1_hash[5:]

    url = f"https://api.pwnedpasswords.com/range/{prefix}"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code != 200:
            return -1
    except requests.RequestException as e:
        # ---> ADDED THIS PRINT STATEMENT FOR THE PENTEST <---
        print(f"\n[!!!] RAW SSL ERROR INTERCEPTED: {e}\n")
        return -1

    hashes = (line.split(':') for line in response.text.splitlines())
    for h, count in hashes:
        if h == suffix:
            return int(count)

    return 0


# --- SECURE AUDIT LOGGING ---
def log_event(event_description):
    """Securely logs an event with an SHA-256 hash to prevent tampering."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {event_description}"

    # Create a hash of the text entry
    entry_hash = hashlib.sha256(log_entry.encode('utf-8')).hexdigest()

    # Save both the entry and the hash side-by-side
    secure_line = f"{log_entry} | HASH:{entry_hash}\n"

    with open(AUDIT_FILE, "a", encoding="utf-8") as f:
        f.write(secure_line)


def read_audit_log():
    """Reads the log, verifies integrity, and returns (logs_list, is_secure)."""
    if not os.path.exists(AUDIT_FILE):
        return [], True

    logs = []
    is_secure = True

    with open(AUDIT_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            try:
                # Split by the hash separator
                content, stored_hash = line.rsplit(" | HASH:", 1)

                # Re-verify the hash locally
                expected_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
                if expected_hash != stored_hash:
                    is_secure = False
                    content += " [⚠️ TAMPERED]"

                logs.append(content)
            except ValueError:
                # If someone deletes the hash entirely, flag it
                is_secure = False
                logs.append(f"{line} [⚠️ TAMPERED/MALFORMED]")

    return logs, is_secure