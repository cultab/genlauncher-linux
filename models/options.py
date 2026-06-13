from __future__ import annotations

import dataclasses
from typing import Optional

from .enums import InstallMethod


@dataclasses.dataclass
class LauncherOptions:
    install_method: InstallMethod = InstallMethod.CopyFiles
    steam_path: str = ""


@dataclasses.dataclass
class InstallationStatus:
    modded_launcher: bool = False
    gen_tool: bool = False
