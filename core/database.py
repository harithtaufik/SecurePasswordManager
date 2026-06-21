# database.py
import sqlite3
import config

# Try to import SQLCipher, fallback to standard SQLite
try:
    from pysqlcipher3 import dbapi2 as sqlite3
except ImportError:
    pass


class DatabaseManager:
    def __init__(self):
        self.db_file = config.DB_FILE

    def _get_connection(self, master_key):
        """Private method to create a connection."""
        conn = sqlite3.connect(self.db_file)
        # Uncomment the line below if using SQLCipher
        conn.execute(f"PRAGMA key='{master_key}'")
        return conn

    def init_db(self, master_key):
        """Creates tables if they don't exist."""
        try:
            conn = self._get_connection(master_key)
            cursor = conn.cursor()
            # Test if password is correct by running a simple query
            cursor.execute("SELECT count(*) FROM sqlite_master")

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    website TEXT NOT NULL,
                    email TEXT NOT NULL,
                    password TEXT NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS config (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            conn.commit()
            conn.close()
            return True
        except Exception:
            return False

    def save_totp_secret(self, master_key, secret):
        conn = self._get_connection(master_key)
        conn.execute("INSERT OR REPLACE INTO config (key, value) VALUES ('totp_secret', ?)", (secret,))
        conn.commit()
        conn.close()

    def get_totp_secret(self, master_key):
        try:
            conn = self._get_connection(master_key)
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM config WHERE key='totp_secret'")
            row = cursor.fetchone()
            conn.close()
            return row[0] if row else None
        except:
            return None

    # --- CRUD OPERATIONS ---
    def fetch_all(self, master_key):
        conn = self._get_connection(master_key)
        cursor = conn.cursor()
        cursor.execute("SELECT id, website, email, password FROM accounts")
        rows = cursor.fetchall()
        conn.close()
        return rows

    def insert_password(self, master_key, site, email, password):
        try:
            conn = self._get_connection(master_key)
            conn.execute("INSERT INTO accounts (website, email, password) VALUES (?, ?, ?)",
                         (site, email, password))
            conn.commit()
            conn.close()
            return True
        except:
            return False

    def update_password(self, master_key, id, site, email, password):
        try:
            conn = self._get_connection(master_key)
            conn.execute("UPDATE accounts SET website=?, email=?, password=? WHERE id=?",
                         (site, email, password, id))
            conn.commit()
            conn.close()
            return True
        except:
            return False

    def delete_password(self, master_key, id):
        try:
            conn = self._get_connection(master_key)
            conn.execute("DELETE FROM accounts WHERE id=?", (id,))
            conn.commit()
            conn.close()
            return True
        except:
            return False