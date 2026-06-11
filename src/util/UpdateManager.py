import shutil
import subprocess
import tempfile
import winreg
import zipfile
from pathlib import Path

class UpdateManager:

    def __init__(self, app_name: str, updater_name: str, shared_dir: Path):
        self.app_name = app_name
        self.updater_name = updater_name
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
        temp_dir = Path(tempfile.gettempdir()) / f"{self.app_name}_{latest_version}_package"
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
        updater_exe_name = f"{self.updater_name}.exe"
        updater_path = temp_dir / updater_exe_name
        if not updater_path.exists():
            raise FileNotFoundError(f"{updater_exe_name} not found in {source_zip.name}")

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
                version, _ = winreg.QueryValueEx(key, "AppVersion")

            return version
        except FileNotFoundError:
            raise RuntimeError(f"AppVersion not found for {self.app_name}")

    def get_latest_version(self) -> str:
        return self._shared_version_file.read_text().strip()

    def cleanup_update_files(self) -> None:
        for temp_dir in self._get_update_temp_dirs(self.get_local_version()):
            if temp_dir.exists():
                shutil.rmtree(temp_dir)

    # ========================================================================================== #
    # Internal functions
    # ========================================================================================== #

    def _parse_version(self, version: str) -> tuple[int, int, int]:
        return tuple(int(part) for part in version.strip().split("."))

    def _get_update_temp_dirs(self, target_version: str) -> tuple[Path, Path]:
        temp_dir = Path(tempfile.gettempdir())

        return (
            temp_dir / f"{self.app_name}_{target_version}_package",
            temp_dir / f"{self.app_name}_{target_version}_staging",
        )

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
