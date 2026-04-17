# Nanoappeqmu

Nanoappeqmu is a small experimental Linux virtualization helper made as an early concept project.

The idea behind it is to simplify some common host-side tasks around QEMU / KVM / libvirt into a lightweight interface.

This is **not a finished product**. It is only an early prototype and proof of concept.

---

# Personal Note

I am not a professional developer and I do not claim to be one.

This project was built as a learning process with the assistance of ChatGPT / GPT tools for guidance, structure, debugging and iteration.

It is shared openly as an experiment, not as a commercial or polished software release.

---

# Current Features

- CPU detection
- GPU detection
- IOMMU status checks
- VFIO readiness checks
- Install basic virtualization packages (depends on distro)
- Enable IOMMU boot flags
- Create test VM
- Start VM
- Stop VM (with force-stop fallback)

---

# Important Warning

## Use At Your Own Risk

This tool may run privileged system commands and may attempt to modify:

- bootloader configuration
- kernel boot flags
- virtualization services
- user group membership

There are currently:

- no snapshots
- no guaranteed rollback system
- no advanced restore points
- no full distro coverage
- no promise of safety

If something breaks, you are responsible for your own system.

Please understand what commands do before using them.

---

# Liability Disclaimer

By using this project, you accept full responsibility for anything that happens to your system, files, boot process, hardware configuration, or installed software.

I do **not** accept responsibility or liability for:

- data loss
- boot failure
- broken configurations
- package conflicts
- system instability
- VM issues
- hardware passthrough issues
- any direct or indirect damage

Use entirely at your own risk.

---

# Current State

This project is unfinished and under testing.

It should be treated as:

- an idea
- a prototype
- a learning experiment
- an early helper script with GUI

Not production software.

---

# Run

```bash
python3 app.py
