import sys
from configparser import ConfigParser
from pathlib import Path

# Determine the project root directory based on whether the app 
# is running in a PyInstaller bundle or not
if getattr(sys, "frozen", False):
    PROJECT_ROOT = Path(sys._MEIPASS)
else:
    PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Central application metadata file shared by the application,
# updater, installer, and GitHub Actions workflow
APP_CONFIG = PROJECT_ROOT / "application.ini"

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
