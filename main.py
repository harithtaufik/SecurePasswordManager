# main.py
import tkinter as tk
from ui.login_screen import LoginScreen
from ui.vault_screen import VaultScreen


class SecurePassApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Secure Password Manager")
        self.geometry("700x550")

        self.master_key = None  # Holds key in memory while running
        self.current_frame = None

        # Start at Login
        self.show_login()

    def show_frame(self, frame_class):
        """Switches the visible screen."""
        if self.current_frame:
            self.current_frame.destroy()

        # Initialize the new frame, passing 'self' (SecurePassApp) as controller
        self.current_frame = frame_class(parent=self, controller=self)
        self.current_frame.pack(fill="both", expand=True)

    def show_login(self):
        self.master_key = None  # Clear key on logout for security
        self.show_frame(LoginScreen)

    def show_vault(self):
        self.show_frame(VaultScreen)


if __name__ == "__main__":
    app = SecurePassApp()
    app.mainloop()