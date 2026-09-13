"""Domain models. Firmware-specific field mappings belong in verified profiles."""

from dataclasses import dataclass
from enum import Enum


class Permission(str, Enum):
    READ_ONLY = "RO"
    READ_WRITE = "RW"
    DENY = "DENY"


@dataclass(frozen=True)
class User:
    username: str
    description: str = ""
    disabled: bool | None = None
    groups: tuple[str, ...] = ()
    uid: int | None = None


@dataclass(frozen=True)
class Group:
    name: str
    description: str = ""
    members: tuple[str, ...] = ()


@dataclass(frozen=True)
class Share:
    name: str
    path: str | None = None
    description: str = ""


@dataclass(frozen=True)
class SharePermission:
    share: str
    permission: Permission | None
    effective_permission: Permission | None = None


@dataclass(frozen=True)
class Quota:
    username: str
    limit_bytes: int | None = None
    used_bytes: int | None = None
