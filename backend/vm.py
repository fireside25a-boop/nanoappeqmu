from utils import (
    safe_subprocess,
    detect_init_system,
    detect_distro,
    package_manager_for_distro,
    detect_bootloader,
    command_exists,
)
import os
import time
import glob
import shutil
from datetime import datetime
import logs

VM_NAME = "vfio-vm"
BACKUP_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "backups")
)


# -----------------------------
# SAFE RUNNER
# -----------------------------
def run(cmd, fallback=None, log=True, timeout=20):
    output = safe_subprocess(
        cmd,
        timeout=timeout,
        fallback=fallback,
        log=log
    )

    if log:
        logs.write(f"Command: {cmd}\nOutput: {output}")

    return output


# -----------------------------
# HELPERS
# -----------------------------
def _ensure_backup_dir():
    os.makedirs(BACKUP_DIR, exist_ok=True)


def _timestamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _contains_iommu_flag(cmdline):
    return (
        "intel_iommu=on" in cmdline or
        "amd_iommu=on" in cmdline
    )


def _clean_kernel_params(text):
    text = text.replace('"', "").replace("'", "").strip()

    params = text.split()

    remove_prefixes = (
        "intel_iommu=",
        "amd_iommu=",
        "iommu=",
        "pcie_acs_override=",
    )

    cleaned = []

    for p in params:
        if any(p.startswith(prefix) for prefix in remove_prefixes):
            continue
        cleaned.append(p)

    return cleaned


# -----------------------------
# INIT SYSTEM / DEPENDENCIES
# -----------------------------
def start_libvirt_service():
    init_system = detect_init_system()

    if init_system == "systemd":
        return run(
            "sudo systemctl enable --now libvirtd",
            fallback="sudo systemctl start libvirtd"
        )

    if init_system == "sysvinit":
        return run("sudo service libvirtd start")

    if init_system == "openrc":
        return run("sudo rc-service libvirtd start")

    return "Unknown init system"


def _package_list_for_distro(distro):
    distro = distro.lower()

    if distro in ("ubuntu", "debian", "mx"):
        return [
            "qemu-system-x86",
            "libvirt-daemon-system",
            "libvirt-clients",
            "virt-manager",
            "ovmf",
            "dnsmasq",
        ]

    if distro in ("arch", "cachyos"):
        return [
            "qemu-full",
            "libvirt",
            "virt-manager",
            "dnsmasq",
            "edk2-ovmf",
        ]

    if distro in ("fedora", "centos"):
        return [
            "qemu-kvm",
            "libvirt",
            "virt-manager",
            "dnsmasq",
            "edk2-ovmf",
        ]

    if distro == "opensuse":
        return [
            "qemu-kvm",
            "libvirt",
            "virt-manager",
            "dnsmasq",
            "qemu-ovmf-x86_64",
        ]

    return []


def check_and_install_dependencies():
    distro = detect_distro()
    pm = package_manager_for_distro(distro)
    packages = _package_list_for_distro(distro)

    if not packages:
        return f"Unknown distro '{distro}'. Install manually."

    if pm == "apt":
        cmd = (
            "sudo apt update && "
            f"sudo apt install -y {' '.join(packages)}"
        )
    elif pm in ("dnf", "yum"):
        cmd = f"sudo {pm} install -y {' '.join(packages)}"
    elif pm == "pacman":
        cmd = f"sudo pacman -S --noconfirm {' '.join(packages)}"
    elif pm == "zypper":
        cmd = f"sudo zypper install -y {' '.join(packages)}"
    else:
        return "Unknown package manager"

    return run(cmd, timeout=120)


def full_setup():
    results = [
        "Starting setup...",
        check_and_install_dependencies(),
        start_libvirt_service(),
        run(
            "sudo usermod -aG libvirt,kvm $USER",
            fallback="sudo usermod -aG libvirt $USER"
        ),
        "Setup complete. Reboot recommended."
    ]

    return "\n".join(results)


# -----------------------------
# HARDWARE DETECTION
# -----------------------------
def detect_cpu():
    return run("grep -m1 'model name' /proc/cpuinfo")


def detect_gpu():
    return run("lspci | grep -E 'VGA|3D|Display'")


def check_boot_iommu():
    return run("cat /proc/cmdline")


def detect_iommu():
    boot = check_boot_iommu()

    dmesg_out = run(
        "sudo dmesg | grep -E 'IOMMU|DMAR|AMD-Vi'",
        fallback="",
        log=False
    )

    lines = []

    if _contains_iommu_flag(boot):
        lines.append("✔ IOMMU enabled in kernel cmdline")
    else:
        lines.append("❌ IOMMU not enabled in kernel cmdline")

    if dmesg_out.strip():
        lines.append("")
        lines.append("Kernel log:")
        lines.append(dmesg_out.strip())
    else:
        lines.append("")
        lines.append("Kernel log restricted or empty")

    return "\n".join(lines)


def get_iommu_groups():
    path = "/sys/kernel/iommu_groups"

    try:
        if not os.path.exists(path):
            return ""

        groups = sorted(
            [x for x in os.listdir(path) if x.isdigit()],
            key=lambda x: int(x)
        )

        return " ".join(groups)

    except Exception:
        return ""


# -----------------------------
# STATUS
# -----------------------------
def check_vfio():
    boot = check_boot_iommu()
    groups = get_iommu_groups()

    if not _contains_iommu_flag(boot):
        return "❌ IOMMU NOT ENABLED"

    if not groups.strip():
        return "⚠ IOMMU enabled but groups not visible"

    return f"✔ VFIO READY\nIOMMU Groups:\n{groups}"


def vfio_status():
    return check_vfio()


# -----------------------------
# BOOTLOADER HELPERS
# -----------------------------
def _backup_file(path):
    _ensure_backup_dir()

    if not os.path.exists(path):
        return ""

    name = os.path.basename(path)
    dst = os.path.join(
        BACKUP_DIR,
        f"{name}.{_timestamp()}.bak"
    )

    shutil.copy2(path, dst)
    return dst


def _grub_update_command():
    if command_exists("update-grub"):
        return "sudo update-grub"

    if command_exists("grub-mkconfig"):
        if os.path.exists("/boot/grub/grub.cfg"):
            return "sudo grub-mkconfig -o /boot/grub/grub.cfg"

        if os.path.exists("/boot/grub2/grub.cfg"):
            return "sudo grub-mkconfig -o /boot/grub2/grub.cfg"

    if command_exists("grub2-mkconfig"):
        if os.path.exists("/boot/grub2/grub.cfg"):
            return "sudo grub2-mkconfig -o /boot/grub2/grub.cfg"

    return ""


def _rewrite_grub_iommu(flags):
    grub_path = "/etc/default/grub"

    if not os.path.exists(grub_path):
        return "❌ /etc/default/grub not found"

    _backup_file(grub_path)

    with open(grub_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    new_lines = []
    found = False

    for line in lines:
        if line.startswith("GRUB_CMDLINE_LINUX_DEFAULT="):
            found = True

            current = line.split("=", 1)[1].strip()
            params = _clean_kernel_params(current)
            merged = " ".join(params + flags.split())

            new_lines.append(
                f'GRUB_CMDLINE_LINUX_DEFAULT="{merged}"\n'
            )
        else:
            new_lines.append(line)

    if not found:
        new_lines.append(
            f'\nGRUB_CMDLINE_LINUX_DEFAULT="{flags}"\n'
        )

    with open("/tmp/grub_fixed", "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    run("sudo mv /tmp/grub_fixed /etc/default/grub")

    update_cmd = _grub_update_command()

    if not update_cmd:
        return "GRUB updated but rebuild command not found."

    return run(update_cmd, timeout=120)


def _rewrite_systemd_boot_iommu(flags):
    entries = sorted(
        glob.glob("/boot/loader/entries/*.conf")
    )

    if not entries:
        return "❌ No systemd-boot entries found"

    for entry in entries:
        _backup_file(entry)

        with open(entry, "r", encoding="utf-8") as f:
            lines = f.readlines()

        new_lines = []
        found = False

        for line in lines:
            if line.startswith("options "):
                found = True
                current = line[len("options "):].strip()
                params = _clean_kernel_params(current)
                merged = " ".join(params + flags.split())
                new_lines.append(f"options {merged}\n")
            else:
                new_lines.append(line)

        if not found:
            new_lines.append(f"options {flags}\n")

        with open(entry, "w", encoding="utf-8") as f:
            f.writelines(new_lines)

    return "Updated systemd-boot entries."


# -----------------------------
# ENABLE IOMMU
# -----------------------------
def enable_iommu_grub():
    cpu = detect_cpu()

    if "Intel" in cpu:
        flags = "intel_iommu=on iommu=pt"
    else:
        flags = "amd_iommu=on iommu=pt"

    bootloader = detect_bootloader()

    if bootloader == "grub":
        result = _rewrite_grub_iommu(flags)
        return (
            "✔ IOMMU enabled for GRUB "
            "(REBOOT REQUIRED)\n\n"
            f"{result}"
        )

    if bootloader == "systemd-boot":
        result = _rewrite_systemd_boot_iommu(flags)
        return (
            "✔ IOMMU enabled for systemd-boot "
            "(REBOOT REQUIRED)\n\n"
            f"{result}"
        )

    return "❌ Unknown bootloader"


# -----------------------------
# VM CONTROL
# -----------------------------
def build_vm_xml(custom_features=""):
    return f"""
<domain type='kvm'>
  <name>{VM_NAME}</name>
  <memory unit='MiB'>4096</memory>
  <vcpu placement='static'>4</vcpu>

  <os>
    <type arch='x86_64'>hvm</type>
    <boot dev='hd'/>
  </os>

  {custom_features}
</domain>
""".strip()


def create_vm_only():
    xml = build_vm_xml(
        "<features><acpi/><apic/></features>"
    )

    with open("/tmp/vm.xml", "w", encoding="utf-8") as f:
        f.write(xml)

    return run("virsh define /tmp/vm.xml")


def start_vm_only():
    all_vms = run("virsh list --all")

    if VM_NAME not in all_vms:
        return "VM not created yet."

    state = run(
        f"virsh domstate {VM_NAME}",
        fallback="shut off"
    )

    if "running" in state.lower():
        return "VM already running"

    return run(f"virsh start {VM_NAME}")


def stop_vm():
    all_vms = run("virsh list --all")

    if VM_NAME not in all_vms:
        return "VM does not exist."

    state = run(
        f"virsh domstate {VM_NAME}",
        fallback="unknown"
    )

    if "shut off" in state.lower():
        return "VM already shut off."

    run(f"virsh shutdown {VM_NAME}")

    for _ in range(10):
        time.sleep(1)

        state = run(
            f"virsh domstate {VM_NAME}",
            fallback="unknown"
        )

        if "shut off" in state.lower():
            return "VM shut down cleanly."

    force = run(f"virsh destroy {VM_NAME}")
    return f"Forced stop executed.\n{force}"
