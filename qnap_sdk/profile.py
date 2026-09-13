"""Load immutable-on-disk firmware contracts from installed package resources."""

import json
from importlib.resources import files
from .client import UnverifiedOperation

DEFAULT_FIRMWARE = "QTS 5.1.9.2954"
PROFILES = {DEFAULT_FIRMWARE: "qts_5_1_9_2954.json"}


def available_profiles() -> tuple[str, ...]:
    """Return firmware names with bundled, verified contracts."""
    return tuple(PROFILES)


def get_profile(firmware: str = DEFAULT_FIRMWARE) -> dict:
    """Return a fresh contract dictionary; caller edits cannot alter other clients."""
    filename = PROFILES.get(firmware)
    if filename is None:
        raise UnverifiedOperation("No bundled profile for this firmware")
    return json.loads(files("qnap_sdk").joinpath("profiles", filename).read_text(encoding="utf-8"))
