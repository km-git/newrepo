"""Tape-to-cloud migration tool.

Vendor-agnostic tooling for migrating physical/virtual tape media into cloud
object storage with a verifiable chain of custody. Each menu item of the
service taxonomy maps to a submodule; ``monetize`` is the optional broker
layer (license tagging, access control, royalty reporting).
"""

__all__ = ["monetize"]
__version__ = "0.1.0"
