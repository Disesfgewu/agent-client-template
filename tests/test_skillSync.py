import json
import tempfile
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from disesfgewuAgent.agent import AgentClient
from disesfgewuAgent.skillSync import (
    DEFAULT_SKILL_LIBRARY_REPO,
    SkillSyncError,
    SkillSyncer,
    _normalize_github_repo,
    sync_skills,
)


def test_normalize_github_repo():
    owner, repo = _normalize_github_repo("Disesfgewu/skill-library")
    assert owner == "Disesfgewu"
    assert repo == "skill-library"

    owner, repo = _normalize_github_repo("https://github.com/Disesfgewu/skill-library.git")
    assert owner == "Disesfgewu"
    assert repo == "skill-library"

    with pytest.raises(SkillSyncError):
        _normalize_github_repo("invalid_format_string")


def test_sync_skills_success():
    fake_registry = {
        "docx": {
            "relativePath": "skills/docx.md",
            "description": "Word doc processing",
        }
    }
    fake_skill_content = "---\nname: docx\ndescription: Word document processing\n---\n# Docx Context"

    def fake_urlopen(req, timeout=10.0):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        mock_resp = MagicMock()
        mock_resp.status = 200
        if "registry.json" in url or "skills.json" in url:
            mock_resp.read.return_value = json.dumps(fake_registry).encode("utf-8")
        else:
            mock_resp.read.return_value = fake_skill_content.encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        return mock_resp

    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            config_path, folder_path = sync_skills(
                source="Disesfgewu/skill-library",
                base_dir=tmpdir,
            )

        assert Path(config_path).exists()
        assert Path(folder_path).exists()
        assert (Path(folder_path) / "docx.md").exists()

        with open(config_path, "r", encoding="utf-8") as f:
            saved_config = json.load(f)
        assert "docx" in saved_config
        assert saved_config["docx"]["relativePath"] == "docx.md"


def test_sync_skills_network_failure():
    def fake_urlopen_fail(req, timeout=10.0):
        raise urllib.error.URLError("Connection refused")

    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("urllib.request.urlopen", side_effect=fake_urlopen_fail):
            with pytest.raises(SkillSyncError):
                sync_skills(source="Disesfgewu/skill-library", base_dir=tmpdir)


def test_agent_client_sync_default_skills_offline_fallback():
    dummy_api_config = [
        {
            "provider": "test",
            "protocol": "openai",
            "endpointUrl": "http://localhost/v1/chat/completions",
            "modelName": "test-model",
            "maxInputToken": 16000,
            "maxOutputToken": 2048,
            "apiKey": "",
        }
    ]

    with patch("disesfgewuAgent.agent.sync_skills", side_effect=SkillSyncError("Offline")):
        with patch("disesfgewuAgent.agent.skillLoader") as mock_loader_cls:
            mock_loader_instance = MagicMock()
            mock_loader_cls.return_value = mock_loader_instance

            client = AgentClient(apiConfig=dummy_api_config)
            cfg_path, folder_path = client.syncDefaultSkills(source="Disesfgewu/skill-library")

            assert cfg_path is not None
            assert folder_path is not None
            # Verified it fallback bootstrapped default skills without crashing


def test_agent_client_init_with_skill_source_offline_fallback():
    dummy_api_config = [
        {
            "provider": "test",
            "protocol": "openai",
            "endpointUrl": "http://localhost/v1/chat/completions",
            "modelName": "test-model",
            "maxInputToken": 16000,
            "maxOutputToken": 2048,
            "apiKey": "",
        }
    ]

    with patch("disesfgewuAgent.agent.sync_skills", side_effect=SkillSyncError("Offline network error")):
        with patch("disesfgewuAgent.agent.skillLoader") as mock_loader_cls:
            mock_loader_instance = MagicMock()
            mock_loader_cls.return_value = mock_loader_instance

            # Client should fall back to bootstrap_default_skills seamlessly
            client = AgentClient(apiConfig=dummy_api_config, skillSource="Disesfgewu/skill-library")
            assert client._skillSource == "Disesfgewu/skill-library"


def test_agent_client_init_with_skill_source_success():
    dummy_api_config = [
        {
            "provider": "test",
            "protocol": "openai",
            "endpointUrl": "http://localhost/v1/chat/completions",
            "modelName": "test-model",
            "maxInputToken": 16000,
            "maxOutputToken": 2048,
            "apiKey": "",
        }
    ]

    with patch("disesfgewuAgent.agent.sync_skills", return_value=("/fake/skills.json", "/fake/skills")) as mock_sync:
        with patch("disesfgewuAgent.agent.skillLoader") as mock_loader_cls:
            client = AgentClient(apiConfig=dummy_api_config, skillSource="Disesfgewu/skill-library")
            mock_sync.assert_called_once_with(source="Disesfgewu/skill-library")
            mock_loader_cls.assert_called_once_with("/fake/skills.json", "/fake/skills")
