"""Tape-to-cloud migration tool.

Vendor-agnostic tooling for migrating physical/virtual tape media into cloud
object storage with a verifiable chain of custody. Each menu item of the
service taxonomy maps to a submodule; ``monetize`` is the optional broker
layer (license tagging, access control, royalty reporting).
"""

from tape_to_cloud.core import MODULES, PlatformContext
from tape_to_cloud.core.registry import list_modules, submit_and_run

__all__ = ["MODULES", "PlatformContext", "list_modules", "submit_and_run"]
__version__ = "0.2.0"
