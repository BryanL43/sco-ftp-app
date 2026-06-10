from configparser import ConfigParser
from pathlib import Path
import os

project_root = Path(__file__).resolve().parent.parent

def load_build_config():
    """
    Load all values from build.ini and flatten them into a dictionary.
    """

    cfg = ConfigParser()
    cfg.read(project_root / "build.ini")

    result = {}
    for section in cfg.sections():
        for key, value in cfg[section].items():
            result[f"{section}_{key}"] = value

    return result

# When running inside GitHub Actions, export all configuration
# values as workflow outputs via the GITHUB_OUTPUT file.
if "GITHUB_OUTPUT" in os.environ:
    config = load_build_config()

    with open(os.environ["GITHUB_OUTPUT"], "a") as f:
        for key, value in config.items():
            f.write(f"{key}={value}\n")
