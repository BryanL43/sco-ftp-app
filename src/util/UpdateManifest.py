from dataclasses import dataclass
from pathlib import Path

"""
Defines the UpdateManifest dataclass, which represents the structure
of the update manifest.json file used for application updates.
"""
@dataclass(frozen=True)
class UpdateManifest:

    manifest_version: int
    app_name: str
    version: str
    package_name: str
    package_sha256: str
    app_dir: str
    updater_path: str
    updater_sha256: str
    preserve: list[str] # List of relative file paths to preserve during the update process
    created_at: str

    @classmethod
    def from_dict(cls, data: dict):
        """
        Create an UpdateManifest instance from a dictionary,
        validating the required fields and their formats.

        Args:
            data (dict): The dictionary containing the manifest data.

        Returns:
            UpdateManifest: An instance of UpdateManifest with the provided data.

        Raises:
            RuntimeError: If the manifest data is invalid or missing required fields.
        """

        try:
            manifest = cls(**data)
        except TypeError as exc:
            raise RuntimeError(f"Invalid update manifest: {exc}") from exc

        # Validate manifest fields for safety and correctness
        manifest._validate_relative_path(manifest.package_name, "package_name")
        manifest._validate_relative_path(manifest.app_dir, "app_dir")
        manifest._validate_relative_path(manifest.updater_path, "updater_path")

        if not isinstance(manifest.preserve, list):
            raise RuntimeError("Update manifest preserve must be a list")

        for path_value in manifest.preserve:
            manifest._validate_relative_path(path_value, "preserve")

        return manifest

    def _validate_relative_path(self, path_value: str, field_name: str) -> None:
        """
        Validate that a given path is a relative path without any parent traversal.

        Args:
            path_value (str): The path value to validate.
            field_name (str): The name of the field being validated (for error messages).

        Raises:
            RuntimeError: If the path is absolute or contains parent traversal.
        """

        if not isinstance(path_value, str) or not path_value:
            raise RuntimeError(f"Update manifest contains invalid {field_name}: {path_value}")

        path = Path(path_value)
        if path.is_absolute() or ".." in path.parts:
            raise RuntimeError(f"Update manifest contains unsafe {field_name}: {path_value}")
