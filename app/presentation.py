BADGE_CLASSES = {
    "online": "success",
    "warning": "warning",
    "down": "danger",
    "maintenance": "secondary",
    "unknown": "light",
    "firing": "danger",
    "acknowledged": "warning",
    "resolved": "success",
    "critical": "danger",
    "info": "info",
    "queued": "secondary",
    "running": "primary",
    "succeeded": "success",
    "failed": "danger",
    "canceled": "dark",
    "admin": "danger",
    "operator": "primary",
    "viewer": "secondary",
    "linux": "dark",
    "windows": "info",
    "mock": "secondary",
    "ansible": "dark",
    "powershell": "primary",
    "shell": "dark",
    "manual": "secondary",
    "remediation": "warning",
    "system": "info",
}


def badge_class(value):
    return BADGE_CLASSES.get(value, "secondary")
