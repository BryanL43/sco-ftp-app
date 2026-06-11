import sys
from configparser import ConfigParser
from pathlib import Path

def _get_app_config_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "application.ini"

    return Path(__file__).resolve().parents[2] / "application.ini"

def load_app_config() -> dict[str, str]:
    """
    Load and flatten all values from application.ini.
    """

    app_config = _get_app_config_path()

    config = ConfigParser()
    if not config.read(app_config, encoding="utf-8"):
        raise FileNotFoundError(app_config)

    result = {}

    # Flatten section/key pairs into a single dictionary using
    # the format: <section>_<key>
    for section in config.sections():
        for key, value in config[section].items():
            result[f"{section}_{key}"] = value

    return result
