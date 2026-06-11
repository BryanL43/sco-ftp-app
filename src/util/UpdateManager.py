import shutil
import subprocess
import tempfile
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
        Copy the latest release ZIP from the shared drive into a temporary
        working directory, extract the updater, and launch it.
        """

        # Locate the release ZIP corresponding to the target version
        source_zip = self._get_latest_zip(latest_version)

        # Create a fresh temporary working directory for the update
        temp_dir = Path(tempfile.gettempdir()) / f"{self.app_name}Download"
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

        temp_dir.mkdir(parents=True)

        # Copy the release ZIP locally so the updater is not dependent
        # on the shared drive remaining available
        local_zip = temp_dir / source_zip.name
        shutil.copy2(source_zip, local_zip)

        # Extract the release contents into the temporary directory
        with zipfile.ZipFile(local_zip, "r") as zip_ref:
            zip_ref.extractall(temp_dir)

        # Locate the updater executable within the extracted files
        updater_path = temp_dir / "Updater.exe"
        if not updater_path.exists():
            raise FileNotFoundError(f"Updater.exe not found in {source_zip.name}")

        # Launch the updater and pass the application name so it can
        # locate the installed application and perform the update
        subprocess.Popen([
            str(updater_path),
            "--app-name",
            self.app_name,
        ])

    def get_local_version(self) -> str:
        key_path = fr"Software\Microsoft\Windows\CurrentVersion\Uninstall\{self.app_name}"

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                version, _ = winreg.QueryValueEx(key, "AppVersion")

            return version
        except FileNotFoundError:
            raise RuntimeError(f"AppVersion not found for {self.app_name}")

    def get_latest_version(self) -> str:
        return self._shared_version_file.read_text().strip()

    # ========================================================================================== #
    # Internal functions
    # ========================================================================================== #

    def _parse_version(self, version: str) -> tuple[int, int, int]:
        return tuple(int(part) for part in version.strip().split("."))

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
