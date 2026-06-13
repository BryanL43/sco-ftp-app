import os
import hashlib
import hmac
import json
import shutil
import subprocess
import tempfile
import time
import zipfile
from dataclasses import asdict
from pathlib import Path

from util.ApplicationRegistry import ApplicationRegistry
from util.UpdateManifest import UpdateManifest

class UpdateManager:

    def __init__(self, app_name: str, shared_dir: Path):
        self.app_name = app_name
        self.shared_dir = shared_dir

        self._manifest_file = shared_dir / "manifest.json"
        self.manifest = self._get_manifest()

    # ========================================================================================== #
    # Public APIs
    # ========================================================================================== #

    def check_for_updates(self) -> tuple[bool, str]:
        """
        Check whether a newer version of the application is available.

        Returns:
            tuple[bool, str]: Update availability and latest version.

        Raises:
            RuntimeError: If the registry value is not found.
        """

        current_version = ApplicationRegistry.get_display_version()
        latest_version = self.manifest.version

        return (
            self._parse_version(latest_version) > self._parse_version(current_version),
            latest_version,
        )

    def launch_updater(self) -> None:
        """
        Copy the update package from the shared drive into a temporary
        staging directory, extract the content, and launch the updater.

        Raises:
            FileNotFoundError: If any required file is missing.
            RuntimeError: If any validation or hash verification fails.
        """

        # Retrieve the update package from the shared drive & verify its integrity
        source_package = self.shared_dir / self.manifest.package_name
        if not source_package.exists():
            raise FileNotFoundError(f"Update package not found: {source_package}")

        self._verify_file_hash(source_package, self.manifest.package_sha256, "Update package")

        # Create a temp staging directory for the update
        latest_version = self.manifest.version
        staging_dir = self._get_update_staging_dir(latest_version)
        if staging_dir.exists():
            shutil.rmtree(staging_dir)

        staging_dir.mkdir(parents=True)

        # Stage the update package locally so we can unzip the contents
        local_package = staging_dir / source_package.name
        shutil.copy2(source_package, local_package)
        self._verify_file_hash(local_package, self.manifest.package_sha256, "Staged update package")

        # Extract the update package into the temp staging directory
        with zipfile.ZipFile(local_package, "r") as zip_ref:
            zip_ref.extractall(staging_dir)

        # Locate the updater executable within the extracted files
        updater_path = staging_dir / self.manifest.updater_path
        if not updater_path.exists():
            raise FileNotFoundError(f"Updater executable not found in {source_package.name}: {updater_path}")

        self._verify_file_hash(updater_path, self.manifest.updater_sha256, "Updater executable")

        # Launch the updater and pass the manifest so it can
        # locate the installed application and perform the update
        payload = {
            "manifest": asdict(self.manifest),
            "application_pid": os.getpid(),
        }

        updater = subprocess.Popen(
            [str(updater_path)],
            stdin=subprocess.PIPE,
            text=True,

            # Controls where the process is running from (updater runs in staging temp dir not in the app).
            # This prevents conflict with accidental mismatch .lnk 'Start in' property.
            cwd=str(updater_path.parent),
        )

        with updater.stdin:
            json.dump(payload, updater.stdin)

    def cleanup_update_files(self, timeout_seconds: int = 5) -> None:
        """
        Remove any leftover update staging directories from previous runs.

        The staging directory is using the local version, since the cleanup
        is intended to remove files after an update attempt,
        regardless of whether the update succeeded or not.

        Args:
            timeout_seconds (int): The maximum time to wait for file locks to be released.
        """

        staging_dir = self._get_update_staging_dir(ApplicationRegistry.get_display_version())
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
        """
        Parse a version string in the format "major.minor.patch" into a tuple of integers.

        Args:
            version (str): The version string to parse.

        Returns:
            tuple[int, int, int]: A tuple containing the major, minor, and patch version.
        """

        return tuple(int(part) for part in version.strip().split("."))

    def _get_update_staging_dir(self, target_version: str) -> Path:
        """
        Get the path to the temporary staging directory for the update.

        Args:
            target_version (str): The target version being updated to.

        Returns:
            Path: The path to the temporary staging directory.
        """

        staging_dir = Path(tempfile.gettempdir())

        return staging_dir / f"{self.app_name}_{target_version}_staging"

    def _get_manifest(self) -> UpdateManifest:
        """
        Load and validate the update manifest.json from the shared drive.

        Returns:
            UpdateManifest: The loaded update manifest in a dataclass.

        Raises:
            FileNotFoundError: If the manifest file is missing.
            RuntimeError: If the manifest is invalid or fails validation.
        """

        if not self._manifest_file.exists():
            raise FileNotFoundError(f"Manifest file not found: {self._manifest_file}")

        # Using utf-8-sig encoding to tolerate potential BOM in the manifest file.
        # It still handles regular UTF-8 files correctly, but will strip the BOM if it's present,
        with open(self._manifest_file, "r", encoding="utf-8-sig") as file:
            return UpdateManifest.from_dict(json.load(file))

    def _verify_file_hash(
        self,
        file_path: Path,
        expected_hash: str,
        description: str
    ) -> None:
        """
        Compute the SHA-256 hash of the given file and compare it to the expected hash.

        Args:
            file_path (Path): The path to the file to verify.
            expected_hash (str): The expected SHA-256 hash in hexadecimal format.
            description (str): A description of the file for error messages.

        Raises:
            RuntimeError: If the computed hash does not match the expected hash.
        """

        actual_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()

        if not hmac.compare_digest(actual_hash, expected_hash.lower()):
            raise RuntimeError(f"{description} hash verification failed")
