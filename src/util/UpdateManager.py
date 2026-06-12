import hashlib
import hmac
import shutil
import subprocess
import tempfile
import time
import winreg
import zipfile
from pathlib import Path

class UpdateManager:

    def __init__(self, app_name: str, shared_dir: Path):
        self.app_name = app_name
        self.shared_dir = shared_dir

        self._shared_version_file = shared_dir / "VERSION"

    # ========================================================================================== #
    # Public APIs
    # ========================================================================================== #

    def check_for_updates(self) -> tuple[bool, str]:
        current_version = self.get_local_version()
        latest_version = self.get_latest_version()

        return (
            self._parse_version(latest_version) > self._parse_version(current_version),
            latest_version,
        )

    def launch_updater(self, latest_version: str) -> None:
        """
        Copy the latest update ZIP from the shared drive into a temporary
        staging directory, extract the content/updater, and launch it.
        """

        # Get the update ZIP for the latest version in the shared directory
        source_zip = self._get_latest_zip(latest_version)

        # Create a temp staging directory for the update
        staging_dir = self._get_update_staging_dir(latest_version)
        if staging_dir.exists():
            shutil.rmtree(staging_dir)

        staging_dir.mkdir(parents=True)

        # Stage the update ZIP locally so the updater can continue even if
        # the shared drive becomes unavailable during the update
        local_zip = staging_dir / source_zip.name
        shutil.copy2(source_zip, local_zip)

        # Extract the update contents into the temp staging directory
        with zipfile.ZipFile(local_zip, "r") as zip_ref:
            zip_ref.extractall(staging_dir)

        # Locate the updater executable within the extracted files
        updater_exe_name = "updater.exe"
        updater_path = staging_dir / updater_exe_name
        if not updater_path.exists():
            raise FileNotFoundError(f"{updater_exe_name} not found in {source_zip.name}")

        self._verify_updater_hash(updater_path)

        # Launch the updater and pass the required metadata so it can
        # locate the installed application and perform the update
        subprocess.Popen([
            str(updater_path),
            "--app-name",
            self.app_name,
            "--target-version",
            latest_version,
        ])

    def get_local_version(self) -> str:
        key_path = fr"Software\Microsoft\Windows\CurrentVersion\Uninstall\{self.app_name}"

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                version, _ = winreg.QueryValueEx(key, "DisplayVersion")

            return version
        except FileNotFoundError:
            raise RuntimeError(f"DisplayVersion not found for {self.app_name}")

    def get_installed_dir(self) -> Path:
        key_path = fr"Software\Microsoft\Windows\CurrentVersion\Uninstall\{self.app_name}"

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                install_dir, _ = winreg.QueryValueEx(key, "InstallLocation")

            return Path(install_dir)
        except FileNotFoundError:
            raise RuntimeError(f"InstallLocation not found for {self.app_name}")

    def get_latest_version(self) -> str:
        return self._shared_version_file.read_text().strip()

    def cleanup_update_files(self, timeout_seconds: int = 5) -> None:
        """
        Remove any leftover update staging directories from previous runs.
        """

        staging_dir = self._get_update_staging_dir(self.get_local_version())
        if staging_dir.exists():
            deadline = time.time() + timeout_seconds

            # Attempt to remove the staging directory
            while time.time() < deadline:
                try:
                    shutil.rmtree(staging_dir)
                    return
                except (PermissionError, OSError):
                    time.sleep(0.25)

            shutil.rmtree(staging_dir)

    # ========================================================================================== #
    # Internal functions
    # ========================================================================================== #

    def _parse_version(self, version: str) -> tuple[int, int, int]:
        return tuple(int(part) for part in version.strip().split("."))

    def _get_update_staging_dir(self, target_version: str) -> Path:
        staging_dir = Path(tempfile.gettempdir())

        return staging_dir / f"{self.app_name}_{target_version}_staging"

    def _get_latest_zip(self, latest_version: str) -> Path:
        zip_files = list(self.shared_dir.glob("*.zip"))
        if not zip_files:
            raise FileNotFoundError(f"No zip file found in {self.shared_dir}")

        if len(zip_files) == 1:
            return zip_files[0]

        matching_zip_files = [zip_file for zip_file in zip_files if latest_version in zip_file.name]
        if len(matching_zip_files) == 1:
            return matching_zip_files[0]

        raise FileNotFoundError(
            f"Could not identify the zip file for version {latest_version} in {self.shared_dir}"
        )

    def _verify_updater_hash(self, updater_path: Path) -> None:
        hash_file = updater_path.with_name("updater.exe.sha256")
        if not hash_file.exists():
            raise FileNotFoundError(f"Missing updater hash file: {hash_file.name}")

        expected_hash = hash_file.read_text(encoding="utf-8").split()[0].lower()
        actual_hash = hashlib.sha256(updater_path.read_bytes()).hexdigest()

        if not hmac.compare_digest(actual_hash, expected_hash):
            raise RuntimeError("Updater executable hash verification failed")
