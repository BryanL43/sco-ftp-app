import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

from gui.ErrorDialog import ErrorDialog
from util.AppConfig import load_app_config
from util.ApplicationRegistry import ApplicationRegistry
from util.Logger import Logger
from util.UpdateManager import UpdateManager

app_config = load_app_config()

APP_NAME = app_config["app_name"]
APP_MAJOR = app_config["app_major"]
APP_MINOR = app_config["app_minor"]
SHARED_DIR = Path(r"C:\Users\bryan\Desktop\SharedDir\sco-ftp-app-versioning")

class Launcher:

    def __init__(self):
        self.update_manager = None

    def run(self) -> None:
        # Check for update (non-blocking if any exceptions occurs)
        if self._is_production_build():
            self._check_for_updates()

        # Clear update files
        if self.update_manager:
            self._cleanup_update_files()

        self._start_app()

    def _is_production_build(self) -> bool:
        """
        Check whether the launcher is running from a packaged executable
        rather than as a script.

        Returns:
            True if running as a frozen executable, otherwise False.
        """

        return getattr(sys, "frozen", False)

    def _check_for_updates(self) -> None:
        """
        Check for updates and, if available, prompt the user to install
        the latest version.
        """

        # Hidden temporary Tkinter root window for showing dialogs during the update check process.
        dialog_root = tk.Tk()
        dialog_root.withdraw()

        try:
            self.update_manager = UpdateManager(APP_NAME, SHARED_DIR)
            has_update, latest_version = self.update_manager.check_for_updates()
        except Exception:
            # If any error occurs during the update check,
            # show a warning but allow the user to continue using the app
            Logger.exception("Update check failed")
            dialog_root.destroy()
            return

        if not has_update:
            dialog_root.destroy()
            return

        # If an update is available, prompt the user to install it
        result = messagebox.askyesno(
            "Update Available",
            (
                f"A newer version is available.\n\n"
                f"Current: {ApplicationRegistry.get_display_version()}\n"
                f"Latest: {latest_version}\n\n"
                f"Install update now?"
            ),
            parent=dialog_root,
        )

        if not result:
            dialog_root.destroy()
            return

        try:
            self.update_manager.launch_updater()
        except Exception as e:
            Logger.exception("Update failed")
            ErrorDialog.show("Update Failed", str(e), parent=dialog_root)
            dialog_root.destroy()
            return

        dialog_root.destroy()
        sys.exit(0) # Terminate the app so that the updater can apply patch

    def _cleanup_update_files(self) -> None:
        """
        Clean up leftover update files in a background thread so startup
        is not blocked.
        """

        def cleanup_update_files():
            try:
                self.update_manager.cleanup_update_files()
            except Exception:
                Logger.exception("Update cleanup failed")

        threading.Thread(
            target=cleanup_update_files,
            daemon=True,
        ).start()

    def _start_app(self) -> None:
        """
        Main entry point for the application
        """
        local_version = self._get_display_version()

        root = tk.Tk()
        root.title(APP_NAME + " v" + local_version)
        root.geometry("300x200")

        tk.Label(
            root,
            text=f"{APP_NAME}\nVersion {local_version}",
        ).pack(expand=True)

        root.mainloop()

    def _get_display_version(self) -> str:
        if not self._is_production_build():
            return f"{APP_MAJOR}.{APP_MINOR}.dev"

        return ApplicationRegistry.get_display_version()


if __name__ == "__main__":
    Launcher().run()
