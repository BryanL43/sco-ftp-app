import logging
import os
from datetime import datetime

# This maps to the log directory in the installed app directory
LOG_FILE = r"..\\logs\\app.log"
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    filename=LOG_FILE,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

class Logger:

    @staticmethod
    def log_message(message: str, time_stamp: bool = True):
        logger.info(message)

        if time_stamp:
            print(f"[{Logger._get_current_timestamp()}] ", end="")
        print(message)

    @staticmethod
    def exception(message: str):
        logger.exception(message)

    @staticmethod
    def _get_current_timestamp() -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
