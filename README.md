# SecurePass Password Manager

This project is structured into **two separate versions** depending on your needs:

1. **🐍 Source Code Version (Current Page):** Best for project assessors, lecturers, and developers who want to view, inspect, and run the Python code using **PyCharm** or another IDE. (Follow the guide below).
2. **🚀 Standalone Executable Version (.EXE):** Best for users who want to double-click and run the application instantly on Windows without installing Python or setting up an IDE. You can download it directly from the **[GitHub Releases Page](https://github.com/harithtaufik/SecurePasswordManager/releases/tag/v1.0.0)**.

---


## 🛠️ Prerequisites

* **Python 3.11.9** installed on your system (Recommended, version used during development).
* **Google Chrome** browser (for testing the Chrome extension autofill feature).

---

## 🚀 Setup and Installation Steps

Follow these steps to get the application running from source code:

### Step 1: Open the Project
Open the `Source_Code_Version` folder in PyCharm or your preferred Python IDE.

### Step 2: Install Dependencies
Open your IDE terminal (or system command prompt navigated to this directory) and install the required Python packages:
```bash
pip install -r requirements.txt
```
*(Dependencies include `cryptography`, `google-api-python-client`, `google-auth-oauthlib`, etc.)*

### Step 3: Register the Chrome Native Messaging Host
Chrome needs to be registered to allow the browser extension to communicate with the Python backend (`native_host.py`).
1. Navigate to the `native_host` directory or run the script from the root:
   ```bash
   python native_host/install_host_source.py
   ```
2. The script will automatically:
   * Detect your current folder location.
   * Locate your active Python interpreter.
   * Generate the necessary `.bat` and `.json` files.
   * Register the host inside the Windows Registry.

### Step 4: Install the Chrome Extension
1. Open Google Chrome and go to: `chrome://extensions/`
2. Enable **Developer mode** (toggle switch in the top-right corner).
3. Click **Load unpacked** (button in the top-left corner).
4. Select the **`extension`** folder located inside this project directory.
5. The extension will load, and its ID will be `bbbgcielondafboddjgaamncjnheoadh` (pre-configured to match the native host).

---

## 🏃 Running the Application

1. Run the main GUI script:
   ```bash
   python main.py
   ```
2. The SecurePass Desktop GUI will launch. You can register/login, add passwords, and test the autofill feature in Chrome!

---

## 🔄 Switching Google Drive Accounts

If you ever want to change the Google Drive account used for backups:
1. Navigate to the **`credentials`** folder inside this directory.
2. Delete the **`token.json`** file.
3. The next time you click **Backup** or **Restore** in the application, a new Google sign-in page will automatically open in your browser, allowing you to log in with a different Google account.

