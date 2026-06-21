# ui/login_screen.py
import tkinter as tk
from tkinter import messagebox, simpledialog
import pyotp
import qrcode
import io
from PIL import Image, ImageTk
import os
import time
import json
import hmac
import hashlib
import uuid
import config

from core import database
from core import utils


class LoginScreen(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.db = database.DatabaseManager()

        # --- LOCKOUT MECHANISM VARIABLES ---
        self.failed_attempts = 0
        self.max_attempts = 3
        self.lockout_duration_ms = 3 * 60 * 1000  # 3 minutes in milliseconds
        self.lockout_until = 0
        self.is_locked = False

        # State file path (saving it in the same directory as the database)
        db_dir = os.path.dirname(config.DB_FILE) or "."
        self.lockout_file = os.path.join(db_dir, "lockout_state.json")

        self.pack(fill="both", expand=True)

        # 1. Load and Verify persistent state before showing UI
        self._load_lockout_state()

        if os.path.exists(config.DB_FILE):
            self.show_login_ui()
        else:
            self.show_register_ui()

    def clear_frame(self):
        for widget in self.winfo_children():
            widget.destroy()

    # --- TAMPER-PROOF STATE MANAGEMENT ---

    def _get_hw_secret(self):
        """Generates a hardware-bound secret based on the machine's MAC address."""
        return str(uuid.getnode()).encode('utf-8')

    def _generate_signature(self, failed_attempts, lockout_until):
        """Creates an HMAC-SHA256 signature to prevent JSON tampering."""
        message = f"{failed_attempts}:{lockout_until}".encode('utf-8')
        return hmac.new(self._get_hw_secret(), message, hashlib.sha256).hexdigest()

    def _save_lockout_state(self):
        """Saves the current lockout variables and a cryptographic signature to disk."""
        state = {
            "failed_attempts": self.failed_attempts,
            "lockout_until": self.lockout_until,
            "signature": self._generate_signature(self.failed_attempts, self.lockout_until)
        }
        try:
            with open(self.lockout_file, 'w') as f:
                json.dump(state, f)
        except Exception as e:
            print(f"Error saving lockout state: {e}")

    def _load_lockout_state(self):
        """Loads state from disk, verifying the signature to detect tampering."""
        if not os.path.exists(self.lockout_file):
            return

        try:
            with open(self.lockout_file, 'r') as f:
                state = json.load(f)

            saved_attempts = state.get("failed_attempts", 0)
            saved_lockout = state.get("lockout_until", 0)
            saved_signature = state.get("signature", "")

            # Verify the signature matches the data
            expected_sig = self._generate_signature(saved_attempts, saved_lockout)

            if hmac.compare_digest(expected_sig, saved_signature):
                # Data is authentic
                self.failed_attempts = saved_attempts
                self.lockout_until = saved_lockout

                # Check if the lockout timer is still active
                current_time = time.time()
                if current_time < self.lockout_until:
                    self.is_locked = True
                    self.lockout_duration_ms = int((self.lockout_until - current_time) * 1000)
            else:
                # TAMPERING DETECTED: File was modified
                utils.log_event("SECURITY ALERT: Lockout state file tampering detected!")
                self._trigger_penalty_lockout()

        except Exception as e:
            # File corrupted or unreadable (another form of tampering/damage)
            utils.log_event("SECURITY ALERT: Lockout state file corrupted!")
            self._trigger_penalty_lockout()

    def _trigger_penalty_lockout(self):
        """Applies a stricter 5-minute penalty if tampering is detected."""
        self.failed_attempts = self.max_attempts
        self.lockout_until = time.time() + (5 * 60)  # 5 minutes
        self.is_locked = True
        self.lockout_duration_ms = 5 * 60 * 1000
        self._save_lockout_state()

    def _reset_lockout_state(self):
        """Clears the state upon a fully successful login."""
        self.failed_attempts = 0
        self.lockout_until = 0
        self._save_lockout_state()

    # --- REGISTER FLOW ---
    def show_register_ui(self):
        self.clear_frame()
        tk.Label(self, text="Create Master Password", font=("Arial", 16, "bold")).pack(pady=30)
        tk.Label(self, text="This will encrypt your database.").pack()

        self.entry = tk.Entry(self, show="*", width=30)
        self.entry.pack(pady=10)

        tk.Button(self, text="Next", command=self.on_register, width=20).pack(pady=10)

    def on_register(self):
        pw = self.entry.get()
        if len(pw) < 4:
            messagebox.showwarning("Weak", "Password must be at least 4 characters.")
            return

        if self.db.init_db(pw):
            self.controller.master_key = pw
            self.show_2fa_setup()

    def show_2fa_setup(self):
        self.clear_frame()
        tk.Label(self, text="Setup 2FA Security", font=("Arial", 14, "bold")).pack(pady=10)

        secret = pyotp.random_base32()
        self.temp_secret = secret

        uri = pyotp.TOTP(secret).provisioning_uri(name="MyVault", issuer_name="SecurePass")
        qr = qrcode.make(uri)
        img_buffer = io.BytesIO()
        qr.save(img_buffer, format="PNG")
        img_buffer.seek(0)

        img = Image.open(img_buffer).resize((200, 200))
        self.qr_photo = ImageTk.PhotoImage(img)

        tk.Label(self, image=self.qr_photo).pack(pady=5)
        tk.Label(self, text="Scan with Google Authenticator").pack()

        tk.Label(self, text="Enter Code:").pack(pady=5)
        self.code_entry = tk.Entry(self, width=10, font=("Arial", 12), justify="center")
        self.code_entry.pack()

        tk.Button(self, text="Verify & Finish", command=self.verify_setup).pack(pady=20)

    def verify_setup(self):
        code = self.code_entry.get()
        if pyotp.TOTP(self.temp_secret).verify(code):
            self.db.save_totp_secret(self.controller.master_key, self.temp_secret)
            utils.log_event("Database Created & 2FA Configured")
            messagebox.showinfo("Success", "Setup Complete! Logging in...")
            self.controller.show_vault()
        else:
            messagebox.showerror("Error", "Invalid Code")

    # --- LOGIN FLOW ---
    def show_login_ui(self):
        self.clear_frame()

        if self.is_locked:
            self.show_lockout_ui()
            return

        tk.Label(self, text="Unlock Vault", font=("Arial", 16, "bold")).pack(pady=30)

        self.entry = tk.Entry(self, show="*", width=30)
        self.entry.pack(pady=10)
        self.entry.focus()
        self.entry.bind('<Return>', lambda e: self.do_login())

        tk.Button(self, text="Unlock", command=self.do_login, width=20).pack(pady=10)

    def do_login(self, event=None):
        if self.is_locked:
            return

        pw = self.entry.get()
        if self.db.init_db(pw):
            self.controller.master_key = pw
            secret = self.db.get_totp_secret(pw)

            if secret:
                # Need 2FA, do not reset attempts yet
                self.show_2fa_input(secret)
            else:
                # Fully successful login (No 2FA)
                self._reset_lockout_state()
                utils.log_event("Successful Login (No 2FA)")
                self.controller.show_vault()
        else:
            self.handle_failed_attempt("Incorrect Master Password")

    # --- 2FA SCREEN ---
    def show_2fa_input(self, secret):
        self.clear_frame()

        if self.is_locked:
            self.show_lockout_ui()
            return

        tk.Label(self, text="Two-Factor Authentication", font=("Arial", 14, "bold")).pack(pady=30)
        tk.Label(self, text="Enter Authenticator Code:", font=("Arial", 10)).pack(pady=5)

        self.code_entry = tk.Entry(self, width=12, font=("Arial", 14), justify="center")
        self.code_entry.pack(pady=10)
        self.code_entry.focus()

        def verify_login(event=None):
            if self.is_locked:
                return

            code = self.code_entry.get()
            if pyotp.TOTP(secret).verify(code):
                # Fully successful login
                self._reset_lockout_state()
                utils.log_event("Successful Login (2FA Verified)")
                self.controller.show_vault()
            else:
                self.handle_failed_attempt("Incorrect 2FA Code")
                self.code_entry.delete(0, tk.END)

        self.code_entry.bind('<Return>', verify_login)
        tk.Button(self, text="Verify", command=verify_login, width=20).pack(pady=20)
        tk.Button(self, text="Cancel", command=self.show_login_ui, width=10, bg="#ffcccc").pack(pady=5)

    # --- LOCKOUT LOGIC ---
    def handle_failed_attempt(self, reason):
        """Processes a failed login attempt, updates state, and triggers lockout if necessary."""
        self.failed_attempts += 1
        attempts_left = self.max_attempts - self.failed_attempts

        utils.log_event(f"Failed Login Attempt ({reason}) - Attempt {self.failed_attempts}/{self.max_attempts}")

        if self.failed_attempts >= self.max_attempts:
            self.trigger_lockout()
        else:
            self._save_lockout_state()
            messagebox.showerror("Error",
                                 f"Invalid credentials.\n\nYou have {attempts_left} attempt(s) remaining before lockout.")

    def trigger_lockout(self):
        """Locks the application interface and writes to the persistent JSON file."""
        self.is_locked = True
        self.lockout_until = time.time() + (self.lockout_duration_ms / 1000)

        # Save the new locked state
        self._save_lockout_state()

        utils.log_event("SYSTEM LOCKED: Exceeded maximum login attempts")
        messagebox.showwarning("Account Locked",
                               f"Too many failed attempts.\n\nThe system is locked for {int(self.lockout_duration_ms / 60000)} minutes.")

        self.show_lockout_ui()

    # --- REAL-TIME UI COUNTDOWN ---
    def show_lockout_ui(self):
        """Displays the locked screen interface and initializes the real-time countdown."""
        self.clear_frame()

        tk.Label(self, text="System Locked 🔒", font=("Arial", 22, "bold"), fg="#c0392b").pack(pady=(60, 10))
        tk.Label(self, text="Too many unsuccessful login attempts.", font=("Arial", 12)).pack(pady=5)

        # Create an empty label to hold the timer text
        self.timer_label = tk.Label(self, text="", font=("Arial", 16, "bold"), fg="#e74c3c")
        self.timer_label.pack(pady=15)

        # Start the countdown loop
        self._update_timer_display()

    def _update_timer_display(self):
        """Calculates time remaining and updates the UI every second."""
        if not self.is_locked:
            return  # Stop the loop if the system was unlocked somehow

        # Calculate exact seconds remaining
        remaining_seconds = int(self.lockout_until - time.time())

        if remaining_seconds > 0:
            # Format time into MM:SS
            minutes, seconds = divmod(remaining_seconds, 60)
            self.timer_label.config(text=f"Time remaining: {minutes:02d}:{seconds:02d}")

            # Re-run this function after 1000 milliseconds (1 second)
            self.after(1000, self._update_timer_display)
        else:
            # Timer reached zero, remove the lockout
            self.remove_lockout()

    def remove_lockout(self):
        """Restores the application to normal login state."""
        self.is_locked = False
        self.failed_attempts = 0
        self.lockout_until = 0
        self._save_lockout_state()  # Save the unlocked state

        utils.log_event("System Unlocked: Lockout timer expired")
        self.show_login_ui()