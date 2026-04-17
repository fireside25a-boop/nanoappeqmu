import tkinter as tk
import queue
from backend.vm import (
    detect_cpu,
    detect_gpu,
    detect_iommu,
    check_vfio,
    full_setup,
    enable_iommu_grub,
    vfio_status,
    create_vm_only,
    start_vm_only,
    stop_vm,
)
from utils import run_threaded
import logs


class NanoQEMUApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Nanoappeqmu")
        self.ui_queue = queue.Queue()

        self.log_text = tk.Text(root, height=22, width=100, wrap=tk.WORD)
        self.log_text.pack(padx=10, pady=10)

        frame = tk.Frame(root)
        frame.pack(padx=10, pady=5)

        tk.Button(
            frame,
            text="Scan CPU/GPU",
            width=24,
            command=lambda: self.run_bg(self.scan_cpu_gpu)
        ).grid(row=0, column=0, padx=5, pady=5)

        tk.Button(
            frame,
            text="Scan IOMMU",
            width=24,
            command=lambda: self.run_bg(self.scan_iommu)
        ).grid(row=0, column=1, padx=5, pady=5)

        tk.Button(
            frame,
            text="VFIO Check",
            width=24,
            command=lambda: self.run_bg(check_vfio)
        ).grid(row=1, column=0, padx=5, pady=5)

        tk.Button(
            frame,
            text="Install",
            width=24,
            command=lambda: self.run_bg(full_setup)
        ).grid(row=1, column=1, padx=5, pady=5)

        tk.Button(
            frame,
            text="Enable IOMMU",
            width=24,
            command=lambda: self.run_bg(enable_iommu_grub)
        ).grid(row=2, column=0, padx=5, pady=5)

        tk.Button(
            frame,
            text="GPU Status",
            width=24,
            command=lambda: self.run_bg(vfio_status)
        ).grid(row=2, column=1, padx=5, pady=5)

        tk.Button(
            frame,
            text="Create VM",
            width=24,
            command=lambda: self.run_bg(create_vm_only)
        ).grid(row=3, column=0, padx=5, pady=5)

        tk.Button(
            frame,
            text="Start VM",
            width=24,
            command=lambda: self.run_bg(start_vm_only)
        ).grid(row=3, column=1, padx=5, pady=5)

        tk.Button(
            frame,
            text="Stop VM",
            width=24,
            command=lambda: self.run_bg(stop_vm)
        ).grid(row=3, column=2, padx=5, pady=5)

        self.root.after(100, self.process_ui_queue)

    # -----------------------------
    # THREAD / UI SAFE HELPERS
    # -----------------------------
    def run_bg(self, func):
        def worker():
            try:
                result = func()
            except Exception as e:
                result = f"ERROR: {e}"
            self.ui_queue.put(result)

        run_threaded(worker)

    def process_ui_queue(self):
        try:
            while True:
                msg = self.ui_queue.get_nowait()
                self.log(msg)
        except queue.Empty:
            pass

        self.root.after(100, self.process_ui_queue)

    # -----------------------------
    # LOGGING
    # -----------------------------
    def log(self, msg):
        self.log_text.insert(tk.END, str(msg) + "\n\n")
        self.log_text.see(tk.END)
        logs.write(msg)

    # -----------------------------
    # ACTIONS
    # -----------------------------
    def scan_cpu_gpu(self):
        return f"CPU:\n{detect_cpu()}\n\nGPU:\n{detect_gpu()}"

    def scan_iommu(self):
        return detect_iommu()


if __name__ == "__main__":
    root = tk.Tk()
    app = NanoQEMUApp(root)
    root.mainloop()
