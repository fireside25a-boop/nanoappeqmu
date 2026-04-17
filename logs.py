import threading
import os

LOG_FILE = os.path.join(os.path.dirname(__file__), "nanoappeqmu.log")
_lock = threading.Lock()


def write(message):
    with _lock:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{message}\n")
            f.flush()
