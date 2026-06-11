import sys
from configparser import ConfigParser
from pathlib import Path

def _get_app_config_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "application.ini"

    return Path(__file__).resolve().parents[2] / "application.ini"

# Central application metadata file shared by the application,
# updater, installer, and GitHub Actions workflow
APP_CONFIG = _get_app_config_path()

def load_app_config() -> dict[str, str]:
    """
    Load and flatten all values from application.ini.
    """

    config = ConfigParser()
    if not config.read(APP_CONFIG):
        raise FileNotFoundError(APP_CONFIG)

    result = {}

    # Flatten section/key pairs into a single dictionary using
    # the format: <section>_<key>
    for section in config.sections():
        for key, value in config[section].items():
            result[f"{section}_{key}"] = value

    return result
