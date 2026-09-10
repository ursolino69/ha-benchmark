"""Controlled public device types and conservative hardware detection."""
from __future__ import annotations

import re

DEVICE_TYPES = {
    "green": {"de": "Green", "en": "Green"},
    "yellow": {"de": "Yellow", "en": "Yellow"},
    "blue": {"de": "Blue", "en": "Blue"},
    "rpi3": {"de": "RasPi 3", "en": "RasPi 3"},
    "rpi4": {"de": "RasPi 4", "en": "RasPi 4"},
    "rpi5": {"de": "RasPi 5", "en": "RasPi 5"},
    "odroid": {"de": "ODROID", "en": "ODROID"},
    "avatto_ha80": {"de": "Avatto HA80", "en": "Avatto HA80"},
    "x86_64": {"de": "x86-64", "en": "x86-64"},
    "arm64": {"de": "ARM64", "en": "ARM64"},
    "vm": {"de": "VM", "en": "VM"},
    "other": {"de": "Sonstiges", "en": "Other"},
}

STORAGE_LABELS = {
    "unknown": "Unknown",
    "sd": "SD",
    "emmc": "eMMC",
    "sata_ssd": "SATA SSD",
    "nvme": "NVMe SSD",
    "virtual": "Virtual",
}

VIRTUAL_MARKERS = (
    "kvm", "qemu", "vmware", "virtualbox", "virtual machine", "hyper-v",
    "xen", "parallels", "bhyve", "proxmox", "openstack", "digitalocean",
)


def valid_device_type(value: object) -> bool:
    return isinstance(value, str) and value in DEVICE_TYPES


def _text(*values: object) -> str:
    return " ".join(str(value or "").lower() for value in values)


def infer_device_type(system: dict, configured: str = "auto", device_model: str = "") -> dict:
    """Return a conservative type decision with candidates for ambiguous systems."""
    if valid_device_type(configured):
        return {"device_type": configured, "confidence": "selected", "candidates": [configured]}

    machine = str(system.get("machine") or "").lower()
    architecture = str(system.get("architecture") or "").lower()
    memory = int(system.get("memory_total_mib") or 0)
    combined = _text(
        machine, architecture, system.get("cpu_model"), system.get("hardware_model"), device_model
    )

    raspberry = re.search(r"raspberry\s*pi\s*([345])|raspberrypi([345])|rpi[-_ ]?([345])", combined)
    if raspberry:
        generation = next(group for group in raspberry.groups() if group)
        kind = f"rpi{generation}"
        return {"device_type": kind, "confidence": "high", "candidates": [kind]}

    if "avatto" in combined and "ha80" in combined:
        return {"device_type": "avatto_ha80", "confidence": "high", "candidates": ["avatto_ha80"]}

    if machine == "yellow" or "home assistant yellow" in combined:
        return {"device_type": "yellow", "confidence": "high", "candidates": ["yellow"]}
    if "home assistant blue" in combined:
        return {"device_type": "blue", "confidence": "high", "candidates": ["blue"]}

    # Third-party RK3566 images can report machine=green. Green's fixed 4 GB RAM
    # makes the combination substantially safer than trusting the machine string alone.
    if machine == "green" or "home assistant green" in combined:
        if 3_500 <= memory <= 4_500:
            return {"device_type": "green", "confidence": "high", "candidates": ["green"]}
        candidates = ["avatto_ha80", "green", "arm64", "other"] if "rk3566" in combined and memory > 4_500 else ["green", "arm64", "other"]
        return {"device_type": None, "confidence": "ambiguous", "candidates": candidates}

    if machine in ("odroid-n2", "odroid-n2-plus") or "odroid n2" in combined:
        return {"device_type": None, "confidence": "ambiguous", "candidates": ["blue", "odroid"]}
    if "odroid" in combined:
        return {"device_type": "odroid", "confidence": "high", "candidates": ["odroid"]}

    if any(marker in combined for marker in VIRTUAL_MARKERS) or machine in ("ova", "qemux86-64", "qemux86"):
        return {"device_type": "vm", "confidence": "high", "candidates": ["vm"]}

    if architecture in ("x86_64", "amd64") or "generic-x86-64" in machine:
        if system.get("hardware_model"):
            return {"device_type": "x86_64", "confidence": "medium", "candidates": ["x86_64"]}
        return {"device_type": None, "confidence": "ambiguous", "candidates": ["x86_64", "vm"]}
    if architecture in ("aarch64", "arm64"):
        return {"device_type": "arm64", "confidence": "medium", "candidates": ["arm64"]}

    return {"device_type": None, "confidence": "unknown", "candidates": ["other"]}
