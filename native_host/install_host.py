# install_host.py
import os
import sys
import json
import winreg

HOST_NAME = "com.harith.securepass"


def install():
    # Determine the dist_dir based on how the script is running
    if getattr(sys, 'frozen', False):
        # Running as a compiled .exe
        # sys.executable points to the .exe file itself (e.g., dist\install_host.exe)
        dist_dir = os.path.dirname(sys.executable)
    else:
        # Running as a normal Python script
        current_dir = os.path.dirname(os.path.abspath(__file__))
        dist_dir = os.path.join(os.path.dirname(current_dir), "dist")

    # Point directly to the new compiled executable
    host_exe_path = os.path.join(dist_dir, "native_host.exe")

    if not os.path.exists(host_exe_path):
        print("Error: native_host.exe not found in dist folder. Compile it first!")
        # Pause so you can see the error if you double-clicked the exe
        input("Press Enter to exit...")
        return

    # Create the manifest file
    manifest_path = os.path.join(dist_dir, f"{HOST_NAME}.json")
    manifest = {
        "name": HOST_NAME,
        "description": "SecurePass Native Host",
        "path": host_exe_path,  # Points directly to the .exe now
        "type": "stdio",
        "allowed_origins": [
            "chrome-extension://bbbgcielondafboddjgaamncjnheoadh/"
        ]
    }

    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=4)

    # Add to Windows Registry
    registry_key = winreg.CreateKey(winreg.HKEY_CURRENT_USER,
                                    rf"Software\Google\Chrome\NativeMessagingHosts\{HOST_NAME}")
    winreg.SetValueEx(registry_key, "", 0, winreg.REG_SZ, manifest_path)
    winreg.CloseKey(registry_key)

    print(f"Setup complete! Manifest created at: {manifest_path}")
    print(f"Registry key points to the executable at: {host_exe_path}")

    # Pause so you can see the success message if you double-clicked the exe
    if getattr(sys, 'frozen', False):
        input("Press Enter to exit...")


if __name__ == "__main__":
    install()