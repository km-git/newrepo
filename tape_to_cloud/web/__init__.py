"""Tape-to-cloud web layer."""

from tape_to_cloud.web.api import dispatch_platform, handle_api, platform_status, render_platform_html

__all__ = ["dispatch_platform", "handle_api", "platform_status", "render_platform_html"]
