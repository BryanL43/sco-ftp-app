import os
from configparser import ConfigParser
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

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

    for section in config.sections():
        for key, value in config[section].items():
            result[f"{section}_{key}"] = value

    return result

def main():
    if "GITHUB_OUTPUT" not in os.environ:
        raise RuntimeError("GITHUB_OUTPUT not found")

    config = load_app_config()

    # When running inside GitHub Actions, export all configuration
    # values as workflow outputs via the GITHUB_OUTPUT file
    with open(os.environ["GITHUB_OUTPUT"], "a") as f:
        for key, value in config.items():
            f.write(f"{key}={value}\n")


if __name__ == "__main__":
    main()
