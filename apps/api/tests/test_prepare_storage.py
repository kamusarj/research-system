import os
import stat

import pytest

from app.prepare_storage import prepare_storage


def test_preparation_preserves_content_modes_and_is_idempotent(tmp_path):
    source = tmp_path / "documents" / "original.pdf"
    source.parent.mkdir(mode=0o700)
    source.write_bytes(b"original binary fixture")
    source.chmod(0o640)

    assert prepare_storage(tmp_path, os.getuid(), os.getgid()) == 0
    assert prepare_storage(tmp_path, os.getuid(), os.getgid()) == 0
    assert source.read_bytes() == b"original binary fixture"
    assert stat.S_IMODE(source.stat().st_mode) == 0o640
    assert stat.S_IMODE(source.parent.stat().st_mode) == 0o700


def test_preparation_skips_file_directory_and_broken_symlinks(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / "sentinel"
    sentinel.write_bytes(b"untouched")
    sentinel.chmod(0o600)
    before = sentinel.stat()
    volume = tmp_path / "volume"
    volume.mkdir()
    (volume / "file-link").symlink_to(sentinel)
    (volume / "directory-link").symlink_to(outside, target_is_directory=True)
    (volume / "broken-link").symlink_to(outside / "missing")

    prepare_storage(volume, os.getuid(), os.getgid())

    assert sentinel.read_bytes() == b"untouched"
    after = sentinel.stat()
    assert (after.st_uid, after.st_gid, after.st_mode, after.st_mtime_ns) == (
        before.st_uid, before.st_gid, before.st_mode, before.st_mtime_ns
    )
    assert all(path.is_symlink() for path in volume.iterdir())


def test_preparation_refuses_symlink_root(tmp_path):
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "link"
    link.symlink_to(target, target_is_directory=True)
    with pytest.raises(OSError):
        prepare_storage(link, os.getuid(), os.getgid())


def test_preparation_refuses_missing_volume(tmp_path):
    with pytest.raises(FileNotFoundError):
        prepare_storage(tmp_path / "missing", os.getuid(), os.getgid())
