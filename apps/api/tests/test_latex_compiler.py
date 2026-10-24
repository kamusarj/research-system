import subprocess
from pathlib import Path

import pytest

from app.services.latex_compiler import compile_latex, latex_failure_message
from app.services.object_storage import DocumentError


def test_compile_latex_returns_bounded_pdf(monkeypatch):
    monkeypatch.setattr(
        "app.services.latex_compiler.shutil.which", lambda command: f"/usr/bin/{command}"
    )

    def fake_run(*_args, **kwargs):
        Path(kwargs["cwd"], "document.pdf").write_bytes(b"%PDF-1.7\nfixture")
        return subprocess.CompletedProcess([], 0, stdout=b"")

    monkeypatch.setattr("app.services.latex_compiler.subprocess.run", fake_run)

    assert compile_latex("\\documentclass{article}\\begin{document}Hi\\end{document}").startswith(
        b"%PDF"
    )


def test_compile_latex_reports_missing_engine(monkeypatch):
    monkeypatch.setattr("app.services.latex_compiler.shutil.which", lambda _command: None)

    with pytest.raises(DocumentError) as raised:
        compile_latex("\\documentclass{article}")

    assert raised.value.code == "LATEX_COMPILER_UNAVAILABLE"
    assert raised.value.status_code == 503


def test_compile_latex_reports_timeout(monkeypatch):
    monkeypatch.setattr(
        "app.services.latex_compiler.shutil.which", lambda command: f"/usr/bin/{command}"
    )
    monkeypatch.setattr(
        "app.services.latex_compiler.subprocess.run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(subprocess.TimeoutExpired("xelatex", 20)),
    )

    with pytest.raises(DocumentError) as raised:
        compile_latex("\\documentclass{article}")

    assert raised.value.code == "LATEX_COMPILE_TIMEOUT"
    assert raised.value.status_code == 504


def test_compile_latex_reports_safe_compile_message(monkeypatch):
    monkeypatch.setattr(
        "app.services.latex_compiler.shutil.which", lambda command: f"/usr/bin/{command}"
    )
    monkeypatch.setattr(
        "app.services.latex_compiler.subprocess.run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess(
            [], 1, stdout=b"source details\n! Undefined control sequence.\n"
        ),
    )

    with pytest.raises(DocumentError) as raised:
        compile_latex("\\documentclass{article}")

    assert raised.value.code == "LATEX_COMPILE_FAILED"
    assert raised.value.message == "! Undefined control sequence."


def test_compile_latex_reports_safe_file_line_error(monkeypatch):
    monkeypatch.setattr(
        "app.services.latex_compiler.shutil.which", lambda command: f"/usr/bin/{command}"
    )
    monkeypatch.setattr(
        "app.services.latex_compiler.subprocess.run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess(
            [],
            1,
            stdout=(
                b"private source details\n"
                b"/tmp/research-latex-secret/document.tex:42: Missing $ inserted.\n"
                b"l.42 private@example.com\n"
            ),
        ),
    )

    with pytest.raises(DocumentError) as raised:
        compile_latex("\\documentclass{article}")

    assert raised.value.message == "Line 42: Missing $ inserted."
    assert "private" not in raised.value.message
    assert latex_failure_message("no useful diagnostic") == "LaTeX source could not be compiled"


def test_latex_compile_endpoint_returns_pdf(client, monkeypatch):
    monkeypatch.setattr("app.api.documents.compile_latex", lambda _source: b"%PDF-1.7\nfixture")

    response = client.post(
        "/api/v1/documents/latex/compile",
        json={"source": "\\documentclass{article}\\begin{document}Hi\\end{document}"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["cache-control"] == "no-store"
    assert response.content.startswith(b"%PDF")
