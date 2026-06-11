import os
import logging
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

from util.AppConfig import load_app_config
from util.UpdateManager import UpdateManager

app_config = load_app_config()

APP_NAME = app_config["app_name"]
SHARED_DIR = Path(r"C:\\Users\\bryan\\Desktop\\SharedDir\\sco-ftp-app-versioning")

# Ensure the log directory exists before configuring logging
LOG_FILE = r"..\\logs\\app.log"
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    filename=LOG_FILE,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

def cleanup_update_files(update_manager: UpdateManager):
    try:
        update_manager.cleanup_update_files()
    except Exception:
        logger.exception("Update cleanup failed")

def main():
    update_manager = UpdateManager(APP_NAME, SHARED_DIR)
    dialog_root = tk.Tk()
    dialog_root.withdraw()

    try:
        has_update, latest_version = update_manager.check_for_updates()
    except Exception as e:
        # If any error occurs during the update check,
        # show a warning but allow the user to continue using the app
        logger.exception("Update check failed")
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
                update_manager.launch_updater(latest_version)
            except Exception as e:
                logger.exception("Update failed")
                messagebox.showerror("Update Failed", str(e), parent=dialog_root)
                dialog_root.destroy()
                return
            else:
                dialog_root.destroy()
                return

    dialog_root.destroy()

    # Attempt to clean up any leftover update files from previous runs
    # without blocking startup
    threading.Thread(
        target=cleanup_update_files,
        args=(update_manager,),
        daemon=True,
    ).start()

    # Create the main application UI
    root = tk.Tk()
    root.title(APP_NAME)
    root.geometry("300x200")

    tk.Label(
        root,
        text=f"{APP_NAME}\nVersion {update_manager.get_local_version()}",
    ).pack(expand=True)

    root.mainloop()


if __name__ == "__main__":
    main()
