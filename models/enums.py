from enum import Enum


class ModificationType(Enum):
    Mod = "Mod"
    Addon = "Addon"
    Patch = "Patch"
    Advertising = "Advertising"


class InstallMethod(Enum):
    CopyFiles = "CopyFiles"
    SymLink = "SymLink"


class GameType(Enum):
    Gen = 1
    ZH = 2
