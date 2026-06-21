import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import pyperclip
import os
from datetime import datetime
import config

from core import database
from core import utils
from core import gdrive_utils  # Import our new Google Drive module


class VaultScreen(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.db = database.DatabaseManager()
        self.master_key = controller.master_key

        self.sidebar = tk.Frame(self, width=220, bg="#2c3e50", height=600, relief="sunken")
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        self.content_area = tk.Frame(self, bg="white")
        self.content_area.pack(side="right", fill="both", expand=True)

        self.create_sidebar_btn("🔐", "My Vault", self.show_vault)
        self.create_sidebar_btn("🛡️", "Security Dashboard", self.show_dashboard)
        self.create_sidebar_btn("☁️", "Backup DB", self.show_backup)
        self.create_sidebar_btn("⚡", "Autofill", self.show_autofill)

        tk.Frame(self.sidebar, height=2, bg="grey").pack(fill="x", pady=20)

        def lock_vault():
            utils.log_event("Vault Manually Locked")
            self.controller.show_login()

        self.create_sidebar_btn("🚪", "Lock Vault", lock_vault, bg_color="#c0392b")

        self.show_vault()

    def create_sidebar_btn(self, icon, text, command, bg_color="#2c3e50"):
        btn = tk.Frame(self.sidebar, bg=bg_color, cursor="hand2", height=50)
        btn.pack(fill="x", pady=1)
        btn.pack_propagate(False)

        lbl_icon = tk.Label(btn, text=icon, bg=bg_color, fg="white", font=("Arial", 14), width=5, anchor="center")
        lbl_icon.pack(side="left", fill="y")

        lbl_text = tk.Label(btn, text=text, bg=bg_color, fg="white", font=("Arial", 11, "bold"), anchor="w")
        lbl_text.pack(side="left", fill="both", expand=True)

        def on_click(e):
            command()

        def on_enter(e):
            if bg_color == "#2c3e50":
                for w in (btn, lbl_icon, lbl_text): w.config(bg="#34495e")

        def on_leave(e):
            if bg_color == "#2c3e50":
                for w in (btn, lbl_icon, lbl_text): w.config(bg=bg_color)

        for widget in (btn, lbl_icon, lbl_text):
            widget.bind("<Button-1>", on_click)
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)

    def clear_content(self):
        for widget in self.content_area.winfo_children():
            widget.destroy()

    # =========================================================================
    # PAGE 1: MY VAULT
    # =========================================================================
    def show_vault(self):
        self.clear_content()
        tk.Label(self.content_area, text="My Password Vault", font=("Arial", 20, "bold"), bg="white").pack(pady=20,
                                                                                                           anchor="w",
                                                                                                           padx=20)

        form_frame = tk.Frame(self.content_area, bg="white")
        form_frame.pack(pady=5, padx=20, fill="x")

        tk.Label(form_frame, text="Website:", bg="white").grid(row=0, column=0, sticky="e")
        self.web_entry = tk.Entry(form_frame, width=25)
        self.web_entry.grid(row=0, column=1, padx=5)

        tk.Label(form_frame, text="Email:", bg="white").grid(row=0, column=2, sticky="e")
        self.email_entry = tk.Entry(form_frame, width=25)
        self.email_entry.grid(row=0, column=3, padx=5)

        tk.Label(form_frame, text="Password:", bg="white").grid(row=1, column=0, sticky="e", pady=5)
        self.pass_entry = tk.Entry(form_frame, width=25)
        self.pass_entry.grid(row=1, column=1, padx=5, pady=5)

        tk.Button(form_frame, text="Generate", command=self.generate).grid(row=1, column=2, padx=5)
        tk.Button(form_frame, text="Add Entry", command=self.add_entry, bg="#27ae60", fg="white").grid(row=1, column=3,
                                                                                                       padx=5)

        self.lbl_strength = tk.Label(form_frame, text="", bg="white", font=("Arial", 8))
        self.lbl_strength.grid(row=2, column=1, sticky="w")
        self.pass_entry.bind("<KeyRelease>", self.update_strength)

        cols = ("real_id", "real_pass", "no", "website", "email", "disp_pass")
        self.tree = ttk.Treeview(self.content_area, columns=cols, show="headings", height=10)

        self.tree.column("real_id", width=0, stretch=tk.NO)
        self.tree.column("real_pass", width=0, stretch=tk.NO)
        self.tree.heading("no", text="No.")
        self.tree.heading("website", text="Website")
        self.tree.heading("email", text="Email")
        self.tree.heading("disp_pass", text="Password")

        self.tree.column("no", width=40, anchor="center")
        self.tree.column("website", width=150)
        self.tree.column("email", width=200)
        self.tree.column("disp_pass", width=150)
        self.tree.pack(fill="both", expand=True, padx=20, pady=10)

        btn_frame = tk.Frame(self.content_area, bg="white")
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="👁 Show/Hide", command=self.toggle_pass).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Edit", command=self.edit_entry).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Delete", command=self.delete_entry, bg="#ffcccc").pack(side="left", padx=5)

        self.refresh_data()

    # =========================================================================
    # PAGE 2: DASHBOARD
    # =========================================================================
    def show_dashboard(self):
        self.clear_content()
        tk.Label(self.content_area, text="Security Dashboard", font=("Arial", 20, "bold"), bg="white").pack(pady=20,
                                                                                                            anchor="w",
                                                                                                            padx=20)

        all_entries = self.db.fetch_all(self.master_key)
        total_count = len(all_entries)

        weak_count = 0
        total_score = 0
        passwords_seen = set()
        total_length = 0

        for entry in all_entries:
            pwd = entry[3]
            score = utils.get_password_score(pwd)
            total_score += score
            total_length += len(pwd)
            if score <= 1:
                weak_count += 1
            passwords_seen.add(pwd)

        health_pct = int((total_score / (total_count * 4)) * 100) if total_count > 0 else 0
        unique_passwords = len(passwords_seen)
        avg_length = round(total_length / total_count) if total_count > 0 else 0

        db_path = config.DB_FILE
        if os.path.exists(db_path):
            c_time = os.path.getctime(db_path)
            m_time = os.path.getmtime(db_path)
            db_created = datetime.fromtimestamp(c_time).strftime("%Y-%m-%d %H:%M")
            last_saved = datetime.fromtimestamp(m_time).strftime("%Y-%m-%d %H:%M")
        else:
            db_created = "Unknown"
            last_saved = "Unknown"

        dash_frame = tk.Frame(self.content_area, bg="white")
        dash_frame.pack(fill="both", expand=True, padx=20)

        # Health Card
        health_text = f"Overall Score: {health_pct}/100\n\n"
        health_text += "Great job!" if health_pct > 75 else "Improvement Needed"
        self.create_placeholder_card(dash_frame, "Password Health", health_text, 0, 0, command=self.show_health_details)

        # Statistics Card
        stats_text = (
            f"Database Created: {db_created}\n"
            f"Last Saved: {last_saved}\n"
            f"Number of Entries: {total_count}\n"
            f"Unique Passwords: {unique_passwords}\n"
            f"Weak Passwords: {weak_count}\n"
            f"Avg Password Length: {avg_length} chars"
        )
        self.create_placeholder_card(dash_frame, "Statistics", stats_text, 0, 1)

        # HIBP Breach Check Card
        self.hibp_desc_var = tk.StringVar(value="Check if your passwords were leaked.\n\nClick 'Scan Now' to check.")
        self.hibp_btn = self.create_placeholder_card(dash_frame, "HIBP Breach Check", self.hibp_desc_var, 1, 0,
                                                     command=self.run_hibp_scan)

        # --- AUDIT LOG CARD UPDATE ---
        logs, is_secure = utils.read_audit_log()
        recent_logs = logs[-3:] if logs else ["No activity yet."]

        log_text = "Recent Activity:\n"
        for log in reversed(recent_logs):
            # Show just the message portion for the small card preview
            parts = log.split("] ", 1)
            msg = parts[1] if len(parts) > 1 else log

            # Shorten message if it's too long
            if len(msg) > 25: msg = msg[:22] + "..."
            log_text += f"• {msg}\n"

        if not is_secure:
            log_text += "\n⚠️ Warning: Log Tampered!"

        self.create_placeholder_card(dash_frame, "Audit Log", log_text.strip(), 1, 1, command=self.show_audit_details)

    def create_placeholder_card(self, parent, title, desc, row, col, command=None):
        card = tk.Frame(parent, bg="#f0f0f0", bd=2, relief="groove", width=280, height=220)
        card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
        card.grid_propagate(False)

        tk.Label(card, text=title, font=("Arial", 12, "bold"), bg="#f0f0f0").pack(pady=10)

        if isinstance(desc, tk.StringVar):
            tk.Label(card, textvariable=desc, bg="#f0f0f0", justify="left").pack(pady=5)
        else:
            tk.Label(card, text=desc, bg="#f0f0f0", justify="left").pack(pady=5)

        # Only create and pack a button if a command was provided
        if command:
            btn_text = "Scan Now" if title == "HIBP Breach Check" else "View Details"
            btn = tk.Button(card, text=btn_text, command=command)
            btn.pack(side="bottom", pady=10)
            return btn

        parent.grid_columnconfigure(0, weight=1)
        parent.grid_columnconfigure(1, weight=1)

        return None

    def run_hibp_scan(self):
        utils.log_event("Ran HIBP Password Breach Scan")  # LOGGING

        self.hibp_desc_var.set("Scanning... Please wait.\n\n(This checks the API securely)")
        self.hibp_btn.config(state="disabled", text="Scanning...")
        self.update_idletasks()

        all_entries = self.db.fetch_all(self.master_key)
        self.breached_accounts = []
        error_occurred = False

        for entry in all_entries:
            website = entry[1]
            email = entry[2]
            pwd = entry[3]

            count = utils.check_hibp_breach(pwd)
            if count > 0:
                self.breached_accounts.append((website, email, count))
            elif count == -1:
                error_occurred = True

        breached_count = len(self.breached_accounts)

        if error_occurred:
            self.hibp_desc_var.set("❌ Network Error.\nCould not connect to HIBP API.")
            self.hibp_btn.config(state="normal", text="Retry Scan", command=self.run_hibp_scan)
        elif breached_count > 0:
            self.hibp_desc_var.set(f"⚠️ {breached_count} Passwords Leaked!\n\nPlease change them immediately.")
            self.hibp_btn.config(state="normal", text="View Details", command=self.show_hibp_details, bg="#ffcccc")
        else:
            self.hibp_desc_var.set("Status: Safe ✅\n\nNo known breaches found in vault.")
            self.hibp_btn.config(state="normal", text="Scan Again", command=self.run_hibp_scan)

    def show_hibp_details(self):
        if not hasattr(self, 'breached_accounts') or not self.breached_accounts:
            return

        details_win = tk.Toplevel(self)
        details_win.title("Breach Details")
        details_win.geometry("600x400")
        details_win.transient(self)
        details_win.grab_set()

        tk.Label(details_win, text="Compromised Accounts", font=("Arial", 14, "bold"), fg="red").pack(pady=15)
        tk.Label(details_win,
                 text="The passwords for the following accounts have been found in known data breaches.\nYou should change them immediately.",
                 justify="center").pack(pady=5)

        tree_frame = tk.Frame(details_win)
        tree_frame.pack(fill="both", expand=True, padx=20, pady=10)

        tree_scroll_y = tk.Scrollbar(tree_frame)
        tree_scroll_y.pack(side="right", fill="y")

        cols = ("website", "email", "count")
        tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=8, yscrollcommand=tree_scroll_y.set)
        tree_scroll_y.config(command=tree.yview)

        tree.heading("website", text="Website")
        tree.heading("email", text="Email")
        tree.heading("count", text="Times Breached")

        tree.column("website", width=200, anchor="w")
        tree.column("email", width=200, anchor="w")
        tree.column("count", width=120, anchor="center")

        tree.pack(side="left", fill="both", expand=True)

        for account in self.breached_accounts:
            tree.insert("", "end", values=(account[0], account[1], f"{account[2]:,}"))

        tk.Button(details_win, text="Close", command=details_win.destroy, width=15).pack(pady=10)

    def show_health_details(self):
        details_win = tk.Toplevel(self)
        details_win.title("Password Health Details")
        details_win.geometry("800x500")
        details_win.transient(self)
        details_win.grab_set()

        tk.Label(details_win, text="Vulnerable Passwords Analysis", font=("Arial", 14, "bold")).pack(pady=15)

        tree_frame = tk.Frame(details_win)
        tree_frame.pack(fill="both", expand=True, padx=20, pady=5)

        tree_scroll_y = tk.Scrollbar(tree_frame)
        tree_scroll_y.pack(side="right", fill="y")

        cols = ("website", "email", "status", "reason", "guess_time")
        tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=8,
                            displaycolumns=("website", "email", "status"),
                            yscrollcommand=tree_scroll_y.set)

        tree_scroll_y.config(command=tree.yview)

        tree.heading("website", text="Website")
        tree.heading("email", text="Email")
        tree.heading("status", text="Status")

        tree.column("website", width=250, anchor="w")
        tree.column("email", width=250, anchor="w")
        tree.column("status", width=100, anchor="center")

        tree.pack(side="left", fill="both", expand=True)

        tk.Label(details_win, text="Full Feedback for Selected Item:", font=("Arial", 10, "bold")).pack(anchor="w",
                                                                                                        padx=20,
                                                                                                        pady=(10, 0))

        details_text = tk.Text(details_win, height=5, wrap="word", bg="#f9f9f9", font=("Arial", 10))
        details_text.pack(fill="x", padx=20, pady=5)
        details_text.insert("1.0", "Select a password from the list above to view analysis and crack time.")
        details_text.config(state="disabled")

        def on_tree_select(event):
            selected = tree.selection()
            if selected:
                item = tree.item(selected[0])
                full_reason = item['values'][3]
                guess_time = item['values'][4]

                output = f"⏱️ Estimated Time to Crack: {guess_time}\n"
                output += f"{'-' * 50}\n"
                output += f"📋 Analysis: {full_reason}"

                details_text.config(state="normal")
                details_text.delete("1.0", tk.END)
                details_text.insert("1.0", output)
                details_text.config(state="disabled")

        tree.bind("<<TreeviewSelect>>", on_tree_select)

        all_entries = self.db.fetch_all(self.master_key)
        for entry in all_entries:
            website = entry[1]
            email = entry[2]
            pwd = entry[3]

            score, warning, suggestions, crack_time = utils.get_password_details(pwd)

            if score < 3:
                status = "Weak" if score < 2 else "Medium"
                reason_text = ""
                if warning: reason_text += f"Warning: {warning} "
                if suggestions: reason_text += f"Tip: {suggestions}"
                if not reason_text.strip(): reason_text = "Password is too short or uses common patterns."

                tree.insert("", "end", values=(website, email, status, reason_text, crack_time))

        tk.Button(details_win, text="Close", command=details_win.destroy, width=15).pack(pady=10)

    # --- FULL AUDIT DETAILS WINDOW ---
    def show_audit_details(self):
        """Displays the complete audit log and checks system integrity."""
        logs, is_secure = utils.read_audit_log()

        audit_win = tk.Toplevel(self)
        audit_win.title("System Audit Log")
        audit_win.geometry("600x400")
        audit_win.transient(self)
        audit_win.grab_set()

        tk.Label(audit_win, text="Security Audit Log", font=("Arial", 14, "bold")).pack(pady=10)

        if is_secure:
            tk.Label(audit_win, text="Integrity Status: SECURE ✅", font=("Arial", 10, "bold"), fg="green").pack(pady=5)
        else:
            tk.Label(audit_win, text="Integrity Status: TAMPERED ❌", font=("Arial", 10, "bold"), fg="red").pack(pady=5)
            tk.Label(audit_win, text="Warning: The log file has been manually altered or corrupted.", fg="red").pack()

        text_frame = tk.Frame(audit_win)
        text_frame.pack(fill="both", expand=True, padx=20, pady=10)

        scroll_y = tk.Scrollbar(text_frame)
        scroll_y.pack(side="right", fill="y")

        log_text = tk.Text(text_frame, yscrollcommand=scroll_y.set, bg="#f9f9f9", font=("Courier", 9))
        log_text.pack(side="left", fill="both", expand=True)
        scroll_y.config(command=log_text.yview)

        # Print logs (newest first)
        for log in reversed(logs):
            log_text.insert(tk.END, log + "\n\n")

        log_text.config(state="disabled")

        tk.Button(audit_win, text="Close", command=audit_win.destroy, width=15).pack(pady=10)

    # =========================================================================
    # LOGIC
    # =========================================================================
    def update_strength(self, event=None):
        txt, color = utils.check_password_strength(self.pass_entry.get())
        self.lbl_strength.config(text=txt, fg=color)

    def generate(self):
        pw = utils.generate_secure_password()
        self.pass_entry.delete(0, tk.END)
        self.pass_entry.insert(0, pw)
        self.update_strength()
        pyperclip.copy(pw)

    def refresh_data(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        rows = self.db.fetch_all(self.master_key)
        for idx, row in enumerate(rows, start=1):
            self.tree.insert("", "end", values=(row[0], row[3], idx, row[1], row[2], "********"))

    def add_entry(self):
        web, email, pw = self.web_entry.get(), self.email_entry.get(), self.pass_entry.get()
        if not web or not email or not pw:
            messagebox.showerror("Error", "All fields required")
            return
        if self.db.insert_password(self.master_key, web, email, pw):
            utils.log_event(f"Added new password entry for {web}")  # LOGGING
            self.refresh_data()
            self.web_entry.delete(0, tk.END)
            self.pass_entry.delete(0, tk.END)
            self.lbl_strength.config(text="")
            messagebox.showinfo("Success", "Saved!")
        else:
            messagebox.showerror("Error", "Save failed")

    def toggle_pass(self):
        sel = self.tree.selection()
        if not sel: return
        vals = list(self.tree.item(sel[0])['values'])
        vals[5] = vals[1] if vals[5] == "********" else "********"
        self.tree.item(sel[0], values=vals)

    def delete_entry(self):
        sel = self.tree.selection()
        if not sel: return
        if messagebox.askyesno("Confirm", "Delete this entry?"):
            if self.db.delete_password(self.master_key, self.tree.item(sel[0])['values'][0]):
                utils.log_event(f"Deleted a password entry")  # LOGGING
                self.refresh_data()

    def edit_entry(self):
        sel = self.tree.selection()
        if not sel: return
        vals = self.tree.item(sel[0])['values']

        id_to_edit, curr_pass, _, curr_web, curr_email, _ = vals

        edit_win = tk.Toplevel(self)
        edit_win.title("Edit Entry")
        edit_win.geometry("350x250")
        edit_win.transient(self)
        edit_win.grab_set()

        tk.Label(edit_win, text="Website:").pack(pady=(15, 5))
        entry_web = tk.Entry(edit_win, width=40)
        entry_web.insert(0, curr_web)
        entry_web.pack()

        tk.Label(edit_win, text="Email:").pack(pady=5)
        entry_email = tk.Entry(edit_win, width=40)
        entry_email.insert(0, curr_email)
        entry_email.pack()

        tk.Label(edit_win, text="Password:").pack(pady=5)
        entry_pass = tk.Entry(edit_win, width=40)
        entry_pass.insert(0, curr_pass)
        entry_pass.pack()

        def save_changes():
            new_web = entry_web.get()
            new_email = entry_email.get()
            new_pass = entry_pass.get()
            if self.db.update_password(self.master_key, id_to_edit, new_web, new_email, new_pass):
                utils.log_event(f"Edited password entry for {new_web}")  # LOGGING
                self.refresh_data()
                edit_win.destroy()
                messagebox.showinfo("Success", "Updated!")
            else:
                messagebox.showerror("Error", "Update failed.", parent=edit_win)

        tk.Button(edit_win, text="Save Changes", command=save_changes, bg="#dddddd", width=20).pack(pady=20)

    # =========================================================================
    # PAGE 3: BACKUP
    # =========================================================================
    def show_backup(self):
        self.clear_content()
        utils.log_event("Opened Backup & Restore Interface")

        tk.Label(self.content_area, text="Cloud Backup & Restore", font=("Arial", 20, "bold"), bg="white").pack(pady=20,
                                                                                                                anchor="w",
                                                                                                                padx=20)

        frame = tk.Frame(self.content_area, bg="white")
        frame.pack(padx=20, fill="x")

        tk.Label(frame, text="Securely back up your encrypted database to Google Drive.", bg="white").pack(anchor="w",
                                                                                                           pady=10)

        # Status Label
        self.lbl_backup_status = tk.Label(frame, text="Status: Ready", fg="black", bg="white",
                                          font=("Arial", 10, "italic"))
        self.lbl_backup_status.pack(anchor="w", pady=5)

        # Buttons
        tk.Button(frame, text="☁️ Backup Database to Drive", command=self.do_backup, font=("Arial", 12), width=30,
                  height=2, bg="#3498db", fg="white").pack(pady=10)
        tk.Button(frame, text="📥 Restore Database from Drive", command=self.do_restore, font=("Arial", 12), width=30,
                  height=2, bg="#e67e22", fg="white").pack(pady=10)

    def do_backup(self):
        self.lbl_backup_status.config(text="Status: Authenticating & Uploading...", fg="blue")
        self.update_idletasks()
        try:
            gdrive_utils.backup_database()
            self.lbl_backup_status.config(text="Status: Backup Successful! ✅", fg="green")
            utils.log_event("Successfully backed up database to Google Drive")
            messagebox.showinfo("Success", "Database successfully backed up to Google Drive!")
        except FileNotFoundError as e:
            self.lbl_backup_status.config(text="Status: credentials.json missing ❌", fg="red")
            messagebox.showerror("Configuration Error", str(e))
        except Exception as e:
            self.lbl_backup_status.config(text="Status: Backup Failed ❌", fg="red")
            messagebox.showerror("Error", f"An error occurred during backup:\n{str(e)}")

    def do_restore(self):
        if not messagebox.askyesno("Warning",
                                   "Restoring will overwrite your current local database. Are you sure you want to continue?"):
            return

        self.lbl_backup_status.config(text="Status: Authenticating & Downloading...", fg="blue")
        self.update_idletasks()
        try:
            gdrive_utils.restore_database()
            self.lbl_backup_status.config(text="Status: Restore Successful! ✅", fg="green")
            utils.log_event("Successfully restored database from Google Drive")

            # Reconnect to the database to reflect changes
            messagebox.showinfo("Success",
                                "Database restored successfully! The application will now return to the login screen to re-authenticate.")
            self.controller.show_login()

        except FileNotFoundError as e:
            self.lbl_backup_status.config(text="Status: No backup found ❌", fg="red")
            messagebox.showerror("Error", str(e))
        except Exception as e:
            self.lbl_backup_status.config(text="Status: Restore Failed ❌", fg="red")
            messagebox.showerror("Error", f"An error occurred during restore:\n{str(e)}")

    # =========================================================================
    # PAGE 4: AUTOFILL
    # =========================================================================
    def show_autofill(self):
        self.clear_content()
        tk.Label(self.content_area, text="Autofill Feature", font=("Arial", 20, "bold"), bg="white").pack(pady=20,
                                                                                                          anchor="w",
                                                                                                          padx=20)
        frame = tk.Frame(self.content_area, bg="white")
        frame.pack(padx=20, fill="x")

        tk.Label(frame, text="How to use Autofill:", font=("Arial", 12, "bold"), bg="white").pack(anchor="w", pady=10)

        steps = "1. Install Chrome extension\n2. Open extension on login page\n3. Click Autofill"
        tk.Label(frame, text=steps, justify="left", bg="white", font=("Arial", 11)).pack(anchor="w")