"""Tests for the one-command launcher configuration."""

import stat

from dotenv import dotenv_values

from ticketing_system import run


def test_existing_api_key_skips_prompt(monkeypatch):
    monkeypatch.setattr(run, "load_dotenv", lambda **kwargs: None)
    monkeypatch.setenv("OPENAI_API_KEY", "configured-key")
    monkeypatch.setattr(
        run.getpass,
        "getpass",
        lambda prompt: (_ for _ in ()).throw(AssertionError("Unexpected prompt")),
    )

    assert run.ensure_api_key() is True


def test_example_key_is_saved_without_printing_key(monkeypatch, capsys, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(
        "OPENAI_API_KEY=your_api_key_here\nOPENAI_MODEL=gpt-6-luna\n"
    )
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(run.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(run.getpass, "getpass", lambda prompt: "entered-test-key")

    assert run.ensure_api_key() is True
    assert run.os.environ["OPENAI_API_KEY"] == "entered-test-key"
    assert dotenv_values(tmp_path / ".env") == {
        "OPENAI_API_KEY": "entered-test-key",
        "OPENAI_MODEL": "gpt-6-luna",
    }
    assert stat.S_IMODE((tmp_path / ".env").stat().st_mode) == 0o600
    assert "entered-test-key" not in capsys.readouterr().out


def test_missing_env_file_is_created(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env.example").write_text(
        "OPENAI_API_KEY=your_api_key_here\n"
        "OPENAI_BASE_URL=https://example.test/openai/v1\n"
        "OPENAI_MODEL=test-model\n"
    )
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(run.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(run.getpass, "getpass", lambda prompt: "entered-test-key")

    assert run.ensure_api_key() is True
    assert dotenv_values(tmp_path / ".env") == {
        "OPENAI_API_KEY": "entered-test-key",
        "OPENAI_BASE_URL": "https://example.test/openai/v1",
        "OPENAI_MODEL": "test-model",
    }
    assert stat.S_IMODE((tmp_path / ".env").stat().st_mode) == 0o600


def test_missing_key_without_terminal_exits_cleanly(monkeypatch, capsys):
    monkeypatch.setattr(run, "load_dotenv", lambda **kwargs: None)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(run.sys.stdin, "isatty", lambda: False)

    assert run.ensure_api_key() is False
    assert "Missing OPENAI_API_KEY" in capsys.readouterr().out
