import json
import os
import sys
import uuid

import pytest

_root = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(_root, "..", "scripts"))

import session_state


def test_init_state_creates_independent_uuid_jobs(monkeypatch, tmp_path):
    monkeypatch.setenv("XIAOYI_PDF_SESSION_ROOT", str(tmp_path / "sessions"))

    first = session_state.init_state()
    second = session_state.init_state()

    assert first["PDF_JOB_ID"] != second["PDF_JOB_ID"]
    assert uuid.UUID(first["PDF_JOB_ID"])
    assert first["PDF_SESSION_DIR"] != second["PDF_SESSION_DIR"]
    assert first["PDF_CONTENT_PATH"].endswith("content.json")
    assert os.path.isfile(os.path.join(first["PDF_SESSION_DIR"], "session.json"))


def test_load_state_requires_exact_job_id(monkeypatch, tmp_path):
    monkeypatch.setenv("XIAOYI_PDF_SESSION_ROOT", str(tmp_path / "sessions"))
    created = session_state.init_state()

    assert session_state.load_state(created["PDF_JOB_ID"]) == created
    with pytest.raises(FileNotFoundError, match="任务状态不存在"):
        session_state.load_state(str(uuid.uuid4()))
    with pytest.raises(ValueError, match="有效 UUID"):
        session_state.load_state("latest")


def test_load_state_rejects_content_path_outside_job(monkeypatch, tmp_path):
    monkeypatch.setenv("XIAOYI_PDF_SESSION_ROOT", str(tmp_path / "sessions"))
    created = session_state.init_state()
    state_file = os.path.join(created["PDF_SESSION_DIR"], "session.json")
    with open(state_file, "r", encoding="utf-8") as stream:
        payload = json.load(stream)
    payload["PDF_CONTENT_PATH"] = str(tmp_path / "other-content.json")
    with open(state_file, "w", encoding="utf-8") as stream:
        json.dump(payload, stream)

    with pytest.raises(ValueError, match="内容路径不合法"):
        session_state.load_state(created["PDF_JOB_ID"])
