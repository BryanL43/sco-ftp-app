import argparse
import time
import psutil
import winreg
import shutil
import tempfile
from pathlib import Path

class CreateUpdater:

    def __init__(self, app_name: str):
        self.app_name = app_name
        self.install_dir = self.get_install_dir()

    def get_install_dir(self) -> Path:
        """
        Retrieve the installation directory of the application from the Windows registry.
        """

        key_path = (fr"Software\Microsoft\Windows\CurrentVersion\Uninstall\{self.app_name}")

        try:
            # Open the registry key for the application and read the InstallLocation value
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                install_dir, _ = winreg.QueryValueEx(key, "InstallLocation")

            return Path(install_dir)
        except FileNotFoundError:
            raise RuntimeError(f"InstallLocation not found in registry for {self.app_name}")

    def run(self):
        """
        Main execution point for the updater. It will perform the following steps sequentially.
        """

        self.wait_for_app_exit()
        self.wait_for_file_unlock()
        self.extract_update()
        self.validate_update()
        self.install_update()
        self.cleanup()
        self.restart_application()

    def wait_for_app_exit(self, timeout_seconds: int = 10) -> None:
        deadline = time.time() + timeout_seconds

        while time.time() < deadline:
            is_running = False

            for proc in psutil.process_iter(["name"]):
                try:
                    if (
                        proc.info["name"]
                        and proc.info["name"].lower()
                        == f"{self.app_name}.exe".lower()
                    ):
                        is_running = True
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            if not is_running:
                return

            time.sleep(0.5)

        raise TimeoutError(
            f"Timed out waiting for {self.app_name}.exe to exit."
        )

    def wait_for_file_unlock(self, timeout_seconds: int = 10) -> None:
        exe_path = self.install_dir / f"{self.app_name}.exe"

        deadline = time.time() + timeout_seconds

        while time.time() < deadline:
            try:
                with open(exe_path, "ab"):
                    return
            except PermissionError:
                time.sleep(0.5)

        raise TimeoutError(
            f"Timed out waiting for {exe_path} to unlock."
        )

    def extract_update(self):
        update_source_dir = (Path(tempfile.gettempdir()) / "ScoFTPToolDownload")

        self.staging_dir = (Path(tempfile.gettempdir()) / f"{self.app_name}_Update")
        if self.staging_dir.exists():
            shutil.rmtree(self.staging_dir)

        shutil.copytree(update_source_dir, self.staging_dir)

    def validate_update(self):
        pass

    def install_update(self):
        pass

    def cleanup(self):
        pass

    def restart_application(self):
        pass


if __name__ == "__main__":
    # Parse the command line arguments to get the metadata
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--app-name",
        required=True,
    )
    args = parser.parse_args()

    # Create and run the updater
    updater = CreateUpdater(app_name=args.app_name)
    updater.run()

    print("Success")
