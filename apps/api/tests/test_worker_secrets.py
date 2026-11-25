"""The API's configured task provider must also be usable by the background worker."""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[3]


@pytest.mark.skipif(shutil.which("docker") is None, reason="Docker Compose is required")
def test_team_secret_overlay_gives_worker_the_same_task_provider_files(tmp_path):
    overlay = ROOT / "docker-compose.secrets.example.yml"
    secret = tmp_path / "synthetic-key"
    secret.write_text("synthetic-provider-key")
    variables = set(re.findall(r"\$\{([A-Z0-9_]+)_SECRET_FILE", overlay.read_text()))
    env = tmp_path / "synthetic.env"
    env.write_text(
        "COMPOSE_PROJECT_NAME=baa-secrets-test\nPUBLIC_URL=https://audit.example.test\n"
        "POSTGRES_PASSWORD=synthetic\n"
        + "".join(f"{name}_SECRET_FILE={secret}\n" for name in sorted(variables))
    )
    result = subprocess.run(
        [
            "docker",
            "compose",
            "--env-file",
            str(env),
            "-f",
            str(ROOT / "docker-compose.yml"),
            "-f",
            str(ROOT / "docker-compose.team.yml"),
            "-f",
            str(overlay),
            "config",
            "--format",
            "json",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    services = json.loads(result.stdout)["services"]
    for provider in ("openai_api_key", "deepseek_api_key", "mistral_api_key"):
        for service in ("api", "worker"):
            mounts = {entry["source"]: entry["target"] for entry in services[service]["secrets"]}
            assert mounts[provider] == f"/run/secrets/{provider}"
