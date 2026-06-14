from __future__ import annotations

import logging
import os
import platform
import tempfile


logger = logging.getLogger(__name__)


class SymLinkService:
    @staticmethod
    def is_symlinks_supported() -> bool:
        system = platform.system()
        tmpdir = tempfile.gettempdir()
        tmpfile = os.path.join(tmpdir, os.urandom(8).hex())
        symlink = tmpfile + "_symlink"
        try:
            with open(tmpfile, "w") as f:
                f.write("test")
            os.symlink(tmpfile, symlink)
            supported = os.path.exists(symlink)
            if supported:
                os.unlink(symlink)
            os.unlink(tmpfile)
            return supported
        except (OSError, AttributeError):
            logger.warning("Symlink test failed", exc_info=True)
            try:
                if os.path.exists(symlink):
                    os.unlink(symlink)
                if os.path.exists(tmpfile):
                    os.unlink(tmpfile)
            except OSError:
                logger.warning("Symlink test cleanup failed", exc_info=True)
            return False

    @staticmethod
    def create_symlink(link_file: str, source_file: str) -> bool:
        if not SymLinkService.is_symlinks_supported():
            return False
        if os.path.islink(link_file) or os.path.exists(link_file):
            if os.path.islink(link_file):
                os.unlink(link_file)
            else:
                return False
        link_dir = os.path.dirname(link_file)
        if link_dir:
            os.makedirs(link_dir, exist_ok=True)
        os.symlink(source_file, link_file)
        return os.path.exists(link_file)
