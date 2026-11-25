"""A lock-only security update must replace persistent frontend dependencies."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[3] / "apps/web/scripts/ensure-dependencies.sh"


@pytest.mark.skipif(shutil.which("node") is None, reason="Node is required by frontend startup")
def test_dependency_sync_detects_lock_only_changes_and_failed_installs(tmp_path):
    (tmp_path / "package.json").write_text('{"dependencies":{"next":"^15.5.28"}}')
    lockfile = tmp_path / "package-lock.json"
    lockfile.write_text('{"locked":"15.5.28"}')
    tools = tmp_path / "bin"
    tools.mkdir()
    npm = tools / "npm"
    npm.write_text(
        '#!/bin/sh\n'
        'printf "%s\\n" "$*" >> npm-calls\n'
        'if [ "$1" = ci ]; then\n'
        '  [ ! -f fail-install ] || exit 1\n'
        '  mkdir -p node_modules\n'
        'fi\n'
    )
    npm.chmod(0o755)
    env = {**os.environ, "PATH": f"{tools}:{os.environ['PATH']}"}

    def sync():
        return subprocess.run(["sh", str(SCRIPT)], cwd=tmp_path, env=env, capture_output=True)

    assert sync().returncode == 0
    marker = tmp_path / "node_modules/.dependency-fingerprint"
    initial = marker.read_text()
    assert sync().returncode == 0
    assert (tmp_path / "npm-calls").read_text().count("ci --include=dev") == 1

    # Top-level semver stays satisfied, but the lockfile now requires the patched version.
    lockfile.write_text('{"locked":"15.5.29"}')
    (tmp_path / "fail-install").touch()
    assert sync().returncode != 0
    assert marker.read_text() == initial
    (tmp_path / "fail-install").unlink()
    assert sync().returncode == 0
    assert marker.read_text() != initial
    assert (tmp_path / "npm-calls").read_text().count("ci --include=dev") == 3
