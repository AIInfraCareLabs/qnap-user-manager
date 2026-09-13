"""QNAP management SDK with bundled firmware contracts and native authentication."""

from .client import QnapClient, QnapError, SessionExpired, UnverifiedOperation
from .models import Group, Permission, Quota, Share, SharePermission, User
from .profile import DEFAULT_FIRMWARE, available_profiles, get_profile

__version__ = "0.4.0"
__all__ = [
    "QnapClient",
    "QnapError",
    "SessionExpired",
    "UnverifiedOperation",
    "User",
    "Group",
    "Share",
    "Permission",
    "SharePermission",
    "Quota",
    "DEFAULT_FIRMWARE",
    "available_profiles",
    "get_profile",
    "__version__",
]
