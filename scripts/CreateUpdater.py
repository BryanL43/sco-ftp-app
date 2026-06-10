import shutil
import subprocess
import tempfile
import time
import zipfile
from pathlib import Path
import psutil
import requests
from packaging.version import Version
from configparser import ConfigParser

from ExportBuildConfig import load_build_config

config = load_build_config()
APP_NAME = config["app_name"]
APP_EXE = config["app_exe"]

GITHUB_OWNER = "BryanL43"
GITHUB_REPO = "sco-ftp-app"

GITHUB_LATEST_URL = (
    f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
)

def get_latest_release():
    response = requests.get(GITHUB_LATEST_URL, timeout=30)
    response.raise_for_status()

    release = response.json()

    return {
        "version": release["tag_name"].lstrip("v"),
        "assets": release["assets"],
    }


def is_update_available(current_version: str):
    latest = get_latest_release()

    return Version(latest["version"]) > Version(current_version), latest


def find_zip_asset(release: dict):
    for asset in release["assets"]:
        if asset["name"].endswith(".zip"):
            return asset

    raise RuntimeError("No ZIP asset found in release")


def download_asset(asset: dict, destination: Path):
    response = requests.get(
        asset["browser_download_url"],
        stream=True,
        timeout=300,
    )
    response.raise_for_status()

    with open(destination, "wb") as file:
        for chunk in response.iter_content(1024 * 1024):
            if chunk:
                file.write(chunk)

    return destination


def wait_for_process_exit(pid: int, timeout: int = 60):
    try:
        process = psutil.Process(pid)
        process.wait(timeout=timeout)
    except psutil.NoSuchProcess:
        return


def extract_zip(zip_path: Path, destination: Path):
    with zipfile.ZipFile(zip_path, "r") as archive:
        archive.extractall(destination)


def replace_installation(source_dir: Path, install_dir: Path):
    install_dir.mkdir(parents=True, exist_ok=True)

    for item in source_dir.iterdir():
        destination = install_dir / item.name

        if destination.exists():
            if destination.is_dir():
                shutil.rmtree(destination)
            else:
                destination.unlink()

        if item.is_dir():
            shutil.copytree(item, destination)
        else:
            shutil.copy2(item, destination)


def restart_application(install_dir: Path):
    exe_path = install_dir / APP_EXE

    subprocess.Popen(
        [str(exe_path)],
        cwd=str(install_dir),
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
    )


def perform_update(current_pid: int, install_dir: str):
    temp_dir = Path(tempfile.mkdtemp(prefix="scodex_update_"))

    release = get_latest_release()

    asset = find_zip_asset(release)

    zip_path = temp_dir / asset["name"]

    download_asset(asset, zip_path)

    extract_dir = temp_dir / "extract"

    extract_dir.mkdir()

    extract_zip(zip_path, extract_dir)

    wait_for_process_exit(current_pid)

    replace_installation(
        source_dir=extract_dir,
        install_dir=Path(install_dir),
    )

    restart_application(Path(install_dir))


def cleanup_temp_directory(path: Path):
    try:
        shutil.rmtree(path)
    except Exception:
        pass
