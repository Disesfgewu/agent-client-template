import json
import tempfile
from pathlib import Path

import pytest

from disesfgewuAgent.defaultSkills import discover_skills_in_dir
from disesfgewuAgent.skillLoader import skillLoader


def test_hierarchical_directory_discovery():
    knowledge_root = Path(__file__).parent.parent / "knowledge"
    assert knowledge_root.exists()

    with tempfile.TemporaryDirectory() as tmpdir:
        config_path, folder_path = discover_skills_in_dir(str(knowledge_root), str(Path(tmpdir) / "skills.json"))
        assert Path(config_path).exists()

        with open(config_path, "r", encoding="utf-8") as f:
            registry = json.load(f)

        assert "forwarding" in registry
        assert "pipeline_hazard" in registry
        assert "datapath" in registry
        assert "teaching" in registry
        assert registry["forwarding"]["relativePath"].endswith("forwarding.md")


def test_dag_dependency_resolution():
    knowledge_root = Path(__file__).parent.parent / "knowledge"
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path, folder_path = discover_skills_in_dir(str(knowledge_root), str(Path(tmpdir) / "skills.json"))
        loader = skillLoader(config_path, folder_path)
        loader.load(force=True)

        matched = [loader._skill_map["forwarding"]]
        resolved = loader.resolve_dependencies(matched)

        names = [s["skill_name"] for s in resolved]
        assert "datapath" in names
        assert "pipeline_hazard" in names
        assert "forwarding" in names

        # Topological order: datapath must come before pipeline_hazard, which comes before forwarding
        assert names.index("datapath") < names.index("pipeline_hazard")
        assert names.index("pipeline_hazard") < names.index("forwarding")


def test_circular_dependency_guard():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        skill_a = tmp_path / "skill_a.md"
        skill_b = tmp_path / "skill_b.md"

        skill_a.write_text("---\nname: skill_a\nrequires:\n  - skill_b\n---\n# Skill A", encoding="utf-8")
        skill_b.write_text("---\nname: skill_b\nrequires:\n  - skill_a\n---\n# Skill B", encoding="utf-8")

        config_path, folder_path = discover_skills_in_dir(str(tmp_path))
        loader = skillLoader(config_path, folder_path)
        loader.load(force=True)

        # Must resolve safely without infinite recursion
        resolved = loader.resolve_dependencies([loader._skill_map["skill_a"]])
        resolved_names = [s["skill_name"] for s in resolved]
        assert "skill_a" in resolved_names
        assert "skill_b" in resolved_names


def test_missing_dependency_resilience():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        skill_c = tmp_path / "skill_c.md"
        skill_c.write_text("---\nname: skill_c\nrequires:\n  - non_existent_skill\n---\n# Skill C", encoding="utf-8")

        config_path, folder_path = discover_skills_in_dir(str(tmp_path))
        loader = skillLoader(config_path, folder_path)
        loader.load(force=True)

        # Must handle missing non_existent_skill gracefully
        resolved = loader.resolve_dependencies([loader._skill_map["skill_c"]])
        assert len(resolved) == 1
        assert resolved[0]["skill_name"] == "skill_c"


def test_shared_skills_auto_injection():
    knowledge_root = Path(__file__).parent.parent / "knowledge"
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path, folder_path = discover_skills_in_dir(str(knowledge_root), str(Path(tmpdir) / "skills.json"))
        loader = skillLoader(config_path, folder_path)
        loader.load(force=True)

        # Check global shared skills classification
        global_names = [s["skill_name"] for s in loader._global_skills]
        assert "teaching" in global_names
        assert "reasoning" in global_names

        # Compose with explicit topic indices
        forwarding_idx = loader._skill_map["forwarding"]["idx"]
        composed = loader.composeSkills([forwarding_idx], include_global=True)

        assert "System Guideline: teaching" in composed
        assert "System Guideline: reasoning" in composed
        assert "=== forwarding ===" in composed


def test_zero_match_shared_skills_composition():
    knowledge_root = Path(__file__).parent.parent / "knowledge"
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path, folder_path = discover_skills_in_dir(str(knowledge_root), str(Path(tmpdir) / "skills.json"))
        loader = skillLoader(config_path, folder_path)
        loader.load(force=True)

        # Empty topic indices should still output Global System Guidelines
        composed = loader.composeSkills([], include_global=True)
        assert "System Guideline: teaching" in composed
        assert "System Guideline: reasoning" in composed
