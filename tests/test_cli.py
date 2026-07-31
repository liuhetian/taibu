from __future__ import annotations

import json
from pathlib import Path

import pytest

from suanming import cli


def _json_stream(text: str) -> dict[str, object]:
    value = json.loads(text)
    assert isinstance(value, dict)
    return value


def test_list_command_writes_json_to_stdout(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["list"]) == 0

    captured = capsys.readouterr()
    payload = _json_stream(captured.out)
    assert len(payload["pipelines"]) == 26
    assert captured.err == ""


def test_schema_command_supports_pretty_output(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(["schema", "bazi", "--kind", "input", "--pretty"]) == 0

    captured = capsys.readouterr()
    assert "\n  " in captured.out
    assert _json_stream(captured.out)["type"] == "object"


def test_run_command_accepts_inline_json(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert (
        cli.main(
            [
                "run",
                "tarot",
                "--seed",
                "cli-test",
                "--input",
                '{"spread":"single"}',
            ]
        )
        == 0
    )

    captured = capsys.readouterr()
    payload = _json_stream(captured.out)
    assert payload["pipeline"]["id"] == "tarot"
    assert captured.err == ""


def test_run_command_reads_stdin(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr("sys.stdin.read", lambda: '{"birth_date":"1990-05-15"}')

    assert cli.main(["run", "numerology", "--input", "-"]) == 0
    assert _json_stream(capsys.readouterr().out)["pipeline"]["id"] == "numerology"


def test_empty_stdin_uses_an_empty_request(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr("sys.stdin.read", lambda: "")

    assert cli.main(["run", "tarot", "--seed", "empty-stdin"]) == 0
    assert _json_stream(capsys.readouterr().out)["request"] == {
        "spread": "single",
        "allow_reversed": True,
        "reversal_rate": 0.5,
    }


def test_run_command_reads_utf8_json_file(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    request_path = tmp_path / "request.json"
    request_path.write_text('{"birth_date":"1990-05-15"}', encoding="utf-8")

    assert cli.main(["run", "numerology", "--input", f"@{request_path}"]) == 0
    assert _json_stream(capsys.readouterr().out)["pipeline"]["id"] == "numerology"


def test_missing_input_file_is_reported(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    missing_path = tmp_path / "missing.json"

    assert cli.main(["run", "tarot", "--input", f"@{missing_path}"]) == 2
    payload = _json_stream(capsys.readouterr().err)
    assert payload["error"]["code"] == "input_decode_error"


def test_invalid_json_is_reported_on_stderr(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(["run", "tarot", "--input", "{"]) == 2

    captured = capsys.readouterr()
    payload = _json_stream(captured.err)
    assert payload["error"]["code"] == "input_decode_error"
    assert captured.out == ""


def test_json_array_is_rejected(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["run", "tarot", "--input", "[]"]) == 2

    payload = _json_stream(capsys.readouterr().err)
    assert payload["error"]["code"] == "input_decode_error"


def test_unknown_pipeline_is_a_domain_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(["schema", "missing"]) == 2

    captured = capsys.readouterr()
    assert _json_stream(captured.err)["error"]["code"] == "unknown_pipeline"


def test_assets_verify_command(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["assets", "--verify"]) == 0

    payload = _json_stream(capsys.readouterr().out)
    assert payload["ok"] is True


def test_unexpected_exception_uses_internal_error(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fail() -> list[dict[str, object]]:
        raise RuntimeError("test failure")

    monkeypatch.setattr(cli, "describe_pipelines", fail)

    assert cli.main(["list"]) == 1
    payload = _json_stream(capsys.readouterr().err)
    assert payload["error"]["code"] == "internal_error"
