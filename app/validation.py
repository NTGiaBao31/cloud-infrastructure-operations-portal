import ipaddress
import re

HOSTNAME_RE = re.compile(
    r"^(?=.{1,253}$)([A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)"
    r"(\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)*$"
)
TOKEN_RE = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
AZURE_ID_RE = re.compile(r"^[A-Za-z0-9._:/-]{1,512}$")
NAME_RE = re.compile(r"^[A-Za-z0-9._-]{1,120}$")


def valid_ip(value):
    try:
        ipaddress.ip_address((value or "").strip())
    except ValueError:
        return False
    return True


def valid_hostname(value):
    return bool(HOSTNAME_RE.match((value or "").strip()))


def valid_monitoring_target(value):
    text = (value or "").strip()
    if not text:
        return True
    host, separator, port = text.partition(":")
    if separator:
        if not port.isdigit() or not 1 <= int(port) <= 65535:
            return False
    return valid_hostname(host)


def valid_azure_resource_id(value):
    text = (value or "").strip()
    if not text:
        return True
    return bool(AZURE_ID_RE.match(text))


def blank_to_none(value):
    text = (value or "").strip()
    return text or None
