import winreg
from pathlib import Path

from util.AppConfig import load_app_config

app_config = load_app_config()

APP_NAME = app_config["app_name"]

class ApplicationRegistry:

    __KEY_PATH = fr"Software\Microsoft\Windows\CurrentVersion\Uninstall\{APP_NAME}"

    @staticmethod
    def get_display_version() -> str:
        """
        Retrieve the installed application version from the Windows registry.

        Raises:
            RuntimeError: If the DisplayVersion registry value is not found.
        """

        return ApplicationRegistry._get_string_value("DisplayVersion")

    @staticmethod
    def get_install_location() -> Path:
        """
        Retrieve the installed application directory from the Windows registry.

        Raises:
            RuntimeError: If the InstallLocation registry value is not found.
        """

        return Path(ApplicationRegistry._get_string_value("InstallLocation"))

    @staticmethod
    def _get_string_value(value_name: str) -> str:
        """
        Retrieve a string value from the application's uninstall registry key.

        Args:
            value_name: Name of the registry value to retrieve.

        Returns:
            The registry value as a string.

        Raises:
            RuntimeError: If the specified registry value does not exist.
        """

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, ApplicationRegistry.__KEY_PATH) as key:
                value, _ = winreg.QueryValueEx(key, value_name)

            return value
        except FileNotFoundError:
            raise RuntimeError(f"{value_name} not found for {APP_NAME}")
