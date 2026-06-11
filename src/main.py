import tkinter as tk
from pathlib import Path
from tkinter import messagebox

from util.AppConfig import load_app_config
from util.UpdateManager import UpdateManager

app_config = load_app_config()

APP_NAME = app_config["app_name"]
UPDATER_NAME = app_config["updater_name"]
SHARED_DIR = Path(r"C:\\Users\\bryan\\Desktop\\SharedDir\\sco-ftp-app-versioning")

def main():
    update_manager = UpdateManager(APP_NAME, UPDATER_NAME, SHARED_DIR)

    root = tk.Tk()
    root.title(APP_NAME)
    root.geometry("300x200")

    try:
        has_update, latest_version = update_manager.check_for_updates()
    except Exception as e:
        # If any error occurs during the update check,
        # show a warning but allow the user to continue using the app
        print(f"Update check failed: {e}")
        has_update = False
        latest_version = None

    # If an update is available, prompt the user to install it
    if has_update:
        result = messagebox.askyesno(
            "Update Available",
            (
                f"A newer version is available.\n\n"
                f"Current: {update_manager.get_local_version()}\n"
                f"Latest: {latest_version}\n\n"
                f"Install update now?"
            ),
        )
        if result:
            try:
                update_manager.launch_updater(latest_version)
            except Exception as e:
                messagebox.showerror("Update Failed", str(e))
            else:
                root.destroy()
                return
    else:
        try:
            update_manager.cleanup_update_files()
        except Exception as e:
            print(f"Update cleanup failed: {e}")

    tk.Label(
        root,
        text=f"{APP_NAME}\nVersion hi {update_manager.get_local_version()}",
    ).pack(expand=True)

    root.mainloop()


if __name__ == "__main__":
    main()
