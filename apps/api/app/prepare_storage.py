"""Prepare only the document volume before starting unprivileged application processes."""

import os
import stat
from pathlib import Path

STORAGE_ROOT = Path("/var/lib/research-system/objects")
RUNTIME_UID = 10001
RUNTIME_GID = 10001


def prepare_storage(root: Path, uid: int = RUNTIME_UID, gid: int = RUNTIME_GID) -> int:
    """Preserve contents/modes and never follow symlinks, including the volume root.

    Directory descriptors keep ownership changes anchored inside the opened volume,
    even if a name changes during traversal. Correctly owned entries are left alone.
    """
    changed = 0
    root_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for _, directories, files, directory_fd in os.fwalk(
            ".", topdown=False, follow_symlinks=False, dir_fd=root_fd
        ):
            for name in directories + files:
                metadata = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
                if stat.S_ISLNK(metadata.st_mode):
                    continue
                if (metadata.st_uid, metadata.st_gid) != (uid, gid):
                    os.chown(name, uid, gid, dir_fd=directory_fd, follow_symlinks=False)
                    changed += 1
            metadata = os.fstat(directory_fd)
            if (metadata.st_uid, metadata.st_gid) != (uid, gid):
                os.fchown(directory_fd, uid, gid)
                changed += 1
    finally:
        os.close(root_fd)
    return changed


if __name__ == "__main__":
    print(f"Document storage ready; ownership updates: {prepare_storage(STORAGE_ROOT)}")
