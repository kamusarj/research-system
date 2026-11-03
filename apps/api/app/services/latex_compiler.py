import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from app.core.config import settings
from app.services.object_storage import DocumentError

LATEX_FILE_ERROR = re.compile(r"(?:^|/)document\.tex:(\d+):\s*([^\r\n]+)")
CGROUP_PIDS_MAX = Path("/sys/fs/cgroup/pids.max")


def latex_process_limit_args() -> list[str]:
    # RLIMIT_NPROC counts threads of the host UID across containers. With multiple
    # non-root API workers it can prevent XeTeX from starting xdvipdfmx even while
    # this container has ample capacity. Use the enforced container task limit
    # when it is at most 256; retain the legacy per-UID limit elsewhere.
    try:
        if 0 < int(CGROUP_PIDS_MAX.read_text().strip()) <= 256:
            return []
    except (OSError, ValueError):
        pass
    return ["--nproc=32"]


def latex_failure_message(output: str) -> str:
    file_error = LATEX_FILE_ERROR.search(output)
    if file_error:
        line_number, reason = file_error.groups()
        return f"Line {line_number}: {reason.strip()}"[:300]
    bang_error = next(
        (line.strip() for line in output.splitlines() if line.strip().startswith("!")),
        None,
    )
    return (bang_error or "LaTeX source could not be compiled")[:300]


def compile_latex(source: str) -> bytes:
    if len(source) > settings.latex_compile_max_source_chars:
        raise DocumentError("LATEX_SOURCE_TOO_LARGE", "LaTeX source is too large", 413)
    command = shutil.which(settings.latex_compiler_command)
    if command is None:
        raise DocumentError("LATEX_COMPILER_UNAVAILABLE", "LaTeX compiler is not available", 503)
    limiter = shutil.which("prlimit")
    if limiter is None:
        raise DocumentError(
            "LATEX_COMPILER_UNAVAILABLE", "LaTeX resource limiter is not available", 503
        )

    with tempfile.TemporaryDirectory(prefix="research-latex-") as directory:
        workdir = Path(directory)
        source_path = workdir / "document.tex"
        source_path.write_text(source, encoding="utf-8")
        environment = {
            "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
            "HOME": directory,
            "TEXMFOUTPUT": directory,
            "openin_any": "p",
            "openout_any": "p",
        }
        try:
            completed = subprocess.run(
                [
                    limiter,
                    "--cpu=15",
                    "--as=805306368",
                    "--fsize=12582912",
                    "--nofile=64",
                    *latex_process_limit_args(),
                    "--",
                    command,
                    "-no-shell-escape",
                    "-interaction=nonstopmode",
                    "-halt-on-error",
                    "-file-line-error",
                    "-output-directory",
                    directory,
                    source_path.name,
                ],
                cwd=directory,
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=settings.latex_compile_timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise DocumentError(
                "LATEX_COMPILE_TIMEOUT", "LaTeX compilation timed out", 504
            ) from exc

        pdf_path = workdir / "document.pdf"
        if completed.returncode != 0 or not pdf_path.is_file():
            output = completed.stdout.decode("utf-8", errors="replace")
            raise DocumentError("LATEX_COMPILE_FAILED", latex_failure_message(output), 422)
        size = pdf_path.stat().st_size
        if size <= 0 or size > settings.latex_compile_max_pdf_bytes:
            raise DocumentError("LATEX_OUTPUT_TOO_LARGE", "Compiled PDF exceeds the limit", 422)
        return pdf_path.read_bytes()
