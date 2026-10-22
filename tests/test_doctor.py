from studio import doctor as doctor_mod


def _run(monkeypatch, login):
    monkeypatch.setattr(doctor_mod.shutil, "which", lambda _: "codex")
    monkeypatch.setattr(doctor_mod, "_codex_login", lambda _: login)
    lines = []
    return doctor_mod.doctor(log=lines.append), "\n".join(lines)


def test_doctor_ready_when_codex_logged_in(monkeypatch):
    ok, out = _run(monkeypatch, (True, "Logged in using ChatGPT"))
    assert ok and "Ready to make stickers." in out


def test_unreadable_codex_login_does_not_block(monkeypatch):
    # Inside a Codex sandbox `codex login status` prints "Not logged in" with exit code 0.
    ok, out = _run(monkeypatch, (True, "Not logged in"))
    assert ok and "sandbox" in out and "codex login" in out
