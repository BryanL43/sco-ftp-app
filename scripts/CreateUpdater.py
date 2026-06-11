import argparse
import time
import psutil
import winreg
import shutil
import tempfile
from pathlib import Path

class CreateUpdater:

    def __init__(self, app_name: str, target_version: str):
        self.app_name = app_name
        self.target_version = target_version

        self.install_dir = self.get_install_dir()

        self.package_dir = (
            Path(tempfile.gettempdir())
            / f"{self.app_name}_{self.target_version}_package"
        )

        self.staging_dir = (
            Path(tempfile.gettempdir())
            / f"{self.app_name}_{self.target_version}_staging"
        )

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

        self._wait_for_app_exit()
        self._wait_for_file_unlock()
        self._extract_update()
        self._validate_update()
        self._install_update()
        self._cleanup()
        self._restart_application()

    def _wait_for_app_exit(self, timeout_seconds: int = 10) -> None:
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

    def _wait_for_file_unlock(self, timeout_seconds: int = 10) -> None:
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

    def _extract_update(self):
        if self.staging_dir.exists():
            shutil.rmtree(self.staging_dir)

        shutil.copytree(
            self.package_dir,
            self.staging_dir,
        )

    def _validate_update(self):
        """
        Validate the extracted update before installation.
        """

        if not self.staging_dir.exists():
            raise RuntimeError(
                f"Staging directory does not exist: {self.staging_dir}"
            )

        app_exe = self.staging_dir / f"{self.app_name}.exe"
        if not app_exe.exists():
            raise RuntimeError(f"Missing application executable: {app_exe}")

        bin_dir = self.staging_dir / "bin"

        if not bin_dir.exists():
            raise RuntimeError(f"Missing bin directory: {bin_dir}")

    def _install_update(self):
        pass

    def _cleanup(self):
        pass

    def _restart_application(self):
        pass


if __name__ == "__main__":
    # Parse the command line arguments to get the metadata
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--app-name",
        required=True,
    )
    parser.add_argument(
        "--target-version",
        required=True,
    )

    args = parser.parse_args()

    # Create and run the updater
    updater = CreateUpdater(
        app_name=args.app_name,
        target_version=args.target_version,
    )
    updater.run()

    print("Success")
