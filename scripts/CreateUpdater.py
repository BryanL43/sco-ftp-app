import argparse
import logging
import sys
import subprocess
import threading
import time
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
import winreg
import shutil
import tempfile
from pathlib import Path

class CreateUpdater:

    def __init__(self, app_name: str, target_version: str, app_dir: str, preserve: list[str]):
        self.app_name = app_name
        self.target_version = target_version
        self.app_dir = app_dir
        self.preserved_names = {name.lower() for name in preserve}

        self.install_dir = self.get_installed_dir()

        self.staging_dir = (
            Path(tempfile.gettempdir())
            / f"{self.app_name}_{self.target_version}_staging"
        )
        self.app_staging_dir = self.staging_dir / self.app_dir

        self.logger = self._setup_logger()

    def get_installed_dir(self) -> Path:
        """
        Retrieve the installed application directory from the Windows registry.

        Returns:
            Path: The installed application directory.

        Raises:
            RuntimeError: If the InstallLocation registry value is not found
                in the Windows registry.
        """

        key_path = (fr"Software\Microsoft\Windows\CurrentVersion\Uninstall\{self.app_name}")

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                install_dir, _ = winreg.QueryValueEx(key, "InstallLocation")

            return Path(install_dir)
        except FileNotFoundError:
            raise RuntimeError(f"InstallLocation not found in registry for {self.app_name}")

    def _setup_logger(self) -> logging.Logger:
        """
        Configure updater logging inside the installed application directory.

        Has to be baked into the updater since it does not live in the installed
        application directory.

        Returns:
            Logger: Configured logger instance for the updater.
        """

        log_dir = self.install_dir / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        logging.basicConfig(
            level=logging.INFO,
            filename=log_dir / "updater.log",
            format="[%(asctime)s] [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            force=True,
        )

        return logging.getLogger(__name__)

    def run(self) -> None:
        """Main execution point for the updater."""

        self._wait_for_file_unlock()
        self._validate_staged_payload()
        self._install_update()
        self._update_registry()

    def restart_application(self) -> None:
        """
        Launch the updated application after a successful update.

        Raises:
            RuntimeError: If the application executable is not found after the update.
        """

        app_path = self.install_dir / f"{self.app_name}.exe"
        if not app_path.exists():
            raise RuntimeError(f"Application executable not found after update: {app_path}")

        subprocess.Popen([str(app_path)], cwd=str(self.install_dir))

    def _wait_for_file_unlock(self, timeout_seconds: int = 10) -> None:
        """
        Wait for the main application executable to be unlocked (i.e. no longer in use by the system)

        Args:
            timeout_seconds (int): Maximum time to wait for the application to exit.

        Raises:
            TimeoutError: If the application process does not exit within the specified timeout.
        """

        exe_path = self.install_dir / f"{self.app_name}.exe"

        deadline = time.time() + timeout_seconds

        while time.time() < deadline:
            try:
                # Attempt to open the executable with append binary mode,
                # which will fail if the file is locked by another process
                with open(exe_path, "ab"):
                    return
            except PermissionError:
                time.sleep(0.5)

        raise TimeoutError(f"Timed out waiting for {exe_path} to unlock.")

    def _validate_staged_payload(self) -> None:
        """
        Validate the integrity of the staged update payload before attempting to install it.

        Raises:
            FileNotFoundError: If any expected files are missing from the staging directory.
        """

        if not self.staging_dir.exists():
            raise FileNotFoundError(f"Staging directory does not exist: {self.staging_dir}")

        if not self.app_staging_dir.exists():
            raise FileNotFoundError(f"Application staging directory does not exist: {self.app_staging_dir}")

        app_exe = self.app_staging_dir / f"{self.app_name}.exe"
        if not app_exe.exists():
            raise FileNotFoundError(f"Missing application executable: {app_exe}")

        bin_dir = self.app_staging_dir / "bin"
        if not bin_dir.exists():
            raise FileNotFoundError(f"Missing bin directory: {bin_dir}")

    def _install_update(self) -> None:
        """
        Install the update by copying files from the staging directory to the install directory.

        Raises:
            FileNotFoundError: If the install directory does not exist.
        """

        if not self.install_dir.exists():
            raise FileNotFoundError(f"Install directory does not exist: {self.install_dir}")

        self._clear_install_dir()

        # Copy the staged update files to the install directory
        for source_path in self.app_staging_dir.rglob("*"):
            relative_path = source_path.relative_to(self.app_staging_dir)
            target_path = self.install_dir / relative_path

            if source_path.is_dir():
                target_path.mkdir(parents=True, exist_ok=True)
                continue

            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, target_path)

    def _clear_install_dir(self) -> None:
        """
        Remove the previous application files before copying the new payload.
        Preserve files/directories listed by the update manifest.
        """

        for installed_path in self.install_dir.iterdir():
            if installed_path.name.lower() in self.preserved_names:
                continue

            if installed_path.is_dir():
                shutil.rmtree(installed_path)
                continue

            installed_path.unlink()

    def _update_registry(self) -> None:
        """Update the registry with the new version information after a successful update."""

        key_path = fr"Software\Microsoft\Windows\CurrentVersion\Uninstall\{self.app_name}"

        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                key_path,
                0,
                winreg.KEY_SET_VALUE,
            ) as key:
                winreg.SetValueEx(key,
                    "DisplayVersion",
                    0,
                    winreg.REG_SZ,
                    self.target_version,
                )
        except OSError as e:
            self.logger.exception(
                "Failed to update DisplayVersion in registry for %s: %s",
                self.app_name,
                e,
            )

    # ========================================================================================== #
    # Updater UI
    # ========================================================================================== #

    class UpdaterUI:

        def __init__(self, app_name: str):
            self.app_name = app_name
            self.stop_ui = threading.Event()
            self.root = None
            self.status_var = None

        def start(self) -> None:
            """
            Start the UI in a separate thread so it can run concurrently with the update process.
            """

            self.ui_thread = threading.Thread(target=self._show_ui, daemon=True)
            self.ui_thread.start()

        def stop(self) -> None:
            """
            Signal the UI to stop and close.
            """

            self.stop_ui.set()
            self.ui_thread.join()

        def show_error_dialog(self, message: str) -> None:
            """
            Show an error dialog with the given message.
            """

            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            root.lift()
            root.focus_force()
            messagebox.showerror("Update Failed", message, parent=root)
            root.destroy()

        def _show_ui(self) -> None:
            """
            Create and display the updater UI.
            """

            self.root = tk.Tk()
            self.root.title(f"Updating {self.app_name}")
            self.root.resizable(False, False)
            self._center_window(360, 110)
            self.root.attributes("-topmost", True)
            self.root.lift()
            self.root.focus_force()
            self.root.after(500, self.root.attributes, "-topmost", False)

            self.status_var = tk.StringVar(value="Updating")
            status_label = ttk.Label(self.root, textvariable=self.status_var, font=("Segoe UI", 11))
            status_label.pack(pady=(20, 10))

            spinner = ttk.Progressbar(self.root, mode="indeterminate", length=190)
            spinner.pack(pady=(0, 16))
            spinner.start(12)

            self._update_status()
            self.root.mainloop()

        def _center_window(self, width: int, height: int) -> None:
            """
            Center the updater window on the user's primary screen.
            """

            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            x = (screen_width - width) // 2
            y = (screen_height - height) // 2
            self.root.geometry(f"{width}x{height}+{x}+{y}")

        def _update_status(self, frame: int = 0) -> None:
            """
            Update the status text to show a simple animated ellipsis while updating.
            """

            if self.stop_ui.is_set():
                self.root.destroy()
                return

            self.status_var.set(f"Updating{'.' * (frame % 4)}")
            self.root.after(400, self._update_status, frame + 1)


if __name__ == "__main__":
    """
    Parse the command line arguments to get the metadata.
    The updater is a standalone executable that receives the
    update metadata as command line arguments from the main
    application process before execution.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--app-name",
        required=True,
    )
    parser.add_argument(
        "--target-version",
        required=True,
    )
    parser.add_argument(
        "--app-dir",
        required=True,
    )
    parser.add_argument(
        "--preserve",
        nargs="*",
        default=[],
    )

    args = parser.parse_args()

    # Create and run the updater
    updater = CreateUpdater(
        app_name=args.app_name,
        target_version=args.target_version,
        app_dir=args.app_dir,
        preserve=args.preserve,
    )

    # Start the visual front updater UI in a separate thread
    updater_ui = CreateUpdater.UpdaterUI(args.app_name)
    updater_ui.start()
    ui_started_at = time.monotonic()

    update_successful = False

    try:
        try:
            updater.run()
            update_successful = True
        finally:
            # Induce a tiny delay to reduce the jarring UI transition for the user
            time.sleep(max(0, 2 - (time.monotonic() - ui_started_at)))
            updater_ui.stop()

        if update_successful:
            updater.restart_application()
    except Exception as exc:
        updater.logger.exception("Update failed")
        updater_ui.show_error_dialog(str(exc))
        sys.exit(1)
