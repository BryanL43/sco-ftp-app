import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

from gui.ErrorDialog import ErrorDialog
from util.AppConfig import load_app_config
from util.Logger import Logger
from util.UpdateManager import UpdateManager

app_config = load_app_config()

APP_NAME = app_config["app_name"]
SHARED_DIR = Path(r"C:\\Users\\bryan\\Desktop\\SharedDir\\sco-ftp-app-versioning")

def main():
    update_manager = UpdateManager(APP_NAME, SHARED_DIR)

    # Hidden temporary Tkinter root window for showing
    # dialogs during the update check process
    dialog_root = tk.Tk()
    dialog_root.withdraw()

    try:
        has_update, latest_version = update_manager.check_for_updates()
    except Exception as e:
        # If any error occurs during the update check,
        # show a warning but allow the user to continue using the app
        Logger.exception("Update check failed")
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
            parent=dialog_root,
        )
        if result:
            try:
                update_manager.launch_updater()
            except Exception as e:
                Logger.exception("Update failed")
                ErrorDialog.show("Update Failed", str(e), parent=dialog_root)
                dialog_root.destroy()
                return
            else:
                dialog_root.destroy()
                return

    dialog_root.destroy()

    # Attempt to clean up any leftover update files from previous runs
    # without blocking startup
    def cleanup_update_files():
        try:
            update_manager.cleanup_update_files()
        except Exception:
            Logger.exception("Update cleanup failed")

    threading.Thread(
        target=cleanup_update_files,
        daemon=True,
    ).start()

    # Create the main application UI
    local_version = update_manager.get_local_version()

    root = tk.Tk()
    root.title(APP_NAME + " v" + local_version)
    root.geometry("300x200")

    tk.Label(
        root,
        text=f"{APP_NAME}\nVersion {local_version}",
    ).pack(expand=True)

    root.mainloop()


if __name__ == "__main__":
    main()
