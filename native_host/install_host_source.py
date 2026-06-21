# install_host_source.py
import os
import sys
import json
import winreg

HOST_NAME = "com.harith.securepass"


def get_manifest_content(host_path):
    """Returns the manifest JSON dict pointing to the specified host_path."""
    return {
        "name": HOST_NAME,
        "description": "SecurePass Native Host (Source Mode)",
        "path": host_path,
        "type": "stdio",
        "allowed_origins": [
            "chrome-extension://bbbgcielondafboddjgaamncjnheoadh/"
        ]
    }


def register_host_in_registry(manifest_path):
    """Registers the manifest path in the Windows registry."""
    registry_key = winreg.CreateKey(winreg.HKEY_CURRENT_USER,
                                    rf"Software\Google\Chrome\NativeMessagingHosts\{HOST_NAME}")
    winreg.SetValueEx(registry_key, "", 0, winreg.REG_SZ, manifest_path)
    winreg.CloseKey(registry_key)


def install_python_mode():
    """Installs the host in Python source code mode (runs python.exe + native_host.py)."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    python_path = sys.executable
    host_py_path = os.path.join(current_dir, "native_host.py")
    bat_path = os.path.join(current_dir, f"{HOST_NAME}.bat")
    manifest_path = os.path.join(current_dir, f"{HOST_NAME}.json")

    # 1. Create the .bat wrapper dynamically using the active python interpreter
    print(f"Creating batch wrapper at: {bat_path}")
    with open(bat_path, "w") as f:
        f.write(f'@echo off\n"{python_path}" "{host_py_path}"')

    # 2. Create the manifest file
    print(f"Creating manifest at: {manifest_path}")
    manifest = get_manifest_content(bat_path)
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=4)

    # 3. Add to Windows Registry
    register_host_in_registry(manifest_path)
    print("\nRegistration successful! Chrome will run the host via your Python interpreter.")
    print(f"Manifest path: {manifest_path}")
    print(f"Points to batch file: {bat_path}")


def main():
    print("==================================================")
    print(" SecurePass Native Host Installer (Source Mode)   ")
    print("==================================================")
    try:
        install_python_mode()
        print("\nInstallation complete successfully!")
    except Exception as e:
        print(f"\nError during installation: {e}")
    input("\nPress Enter to exit...")


if __name__ == "__main__":
    main()
