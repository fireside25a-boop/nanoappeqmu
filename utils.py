import threading
import subprocess
import shutil
import time
import logs
import os


def run_threaded(func, *args, **kwargs):
    thread = threading.Thread(target=func, args=args, kwargs=kwargs, daemon=True)
    thread.start()
    return thread


def safe_subprocess(cmd, timeout=20, retries=0, fallback=None, log=True):
    last_error = ""

    for attempt in range(retries + 1):
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            if result.returncode == 0:
                output = (result.stdout or "").strip()
                if log:
                    logs.write(f"Command succeeded: {cmd}\n{output}")
                return output

            stderr = (result.stderr or "").strip()
            stdout = (result.stdout or "").strip()
            last_error = stderr or stdout or f"Command failed with exit code {result.returncode}"

            if attempt < retries:
                time.sleep(1)

        except subprocess.TimeoutExpired:
            last_error = f"Command timed out after {timeout}s"
            if attempt < retries:
                time.sleep(1)

    if fallback:
        try:
            result = subprocess.run(
                fallback,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            output = ((result.stdout or "").strip() or (result.stderr or "").strip())
            if log:
                logs.write(f"Fallback executed: {fallback}\n{output}")
            return output
        except subprocess.TimeoutExpired:
            if log:
                logs.write(f"Fallback failed after {timeout}s: {fallback}")
            return f"Fallback failed after {timeout}s"

    if log:
        logs.write(f"Command failed: {cmd}\n{last_error}")
    return last_error or "Command failed"


def command_exists(name):
    return shutil.which(name) is not None


def detect_init_system():
    if os.path.exists("/run/systemd/system"):
        return "systemd"
    elif os.path.exists("/run/openrc") or os.path.exists("/etc/rc.conf"):
        return "openrc"
    elif os.path.exists("/etc/init.d"):
        return "sysvinit"
    else:
        return "unknown"


def _read_os_release():
    data = {}
    try:
        with open("/etc/os-release", "r", encoding="utf-8") as f:
            for line in f:
                if "=" in line:
                    key, value = line.strip().split("=", 1)
                    data[key] = value.strip('"')
    except Exception:
        pass
    return data


def detect_distro():
    info = _read_os_release()
    distro_id = info.get("ID", "").lower()
    distro_like = info.get("ID_LIKE", "").lower()
    pretty = info.get("PRETTY_NAME", "").lower()

    if "cachyos" in distro_id or "cachyos" in pretty:
        return "cachyos"
    if distro_id:
        return distro_id
    if "arch" in distro_like:
        return "arch"
    return "unknown"


def package_manager_for_distro(distro):
    distro = (distro or "").lower()
    mapping = {
        "ubuntu": "apt",
        "debian": "apt",
        "mx": "apt",
        "fedora": "dnf",
        "centos": "yum",
        "arch": "pacman",
        "cachyos": "pacman",
        "opensuse": "zypper",
    }
    return mapping.get(distro, "unknown")


def detect_bootloader():
    if os.path.isdir("/boot/loader/entries"):
        return "systemd-boot"

    if os.path.exists("/etc/default/grub") or os.path.isdir("/boot/grub"):
        return "grub"

    return "unknown"
