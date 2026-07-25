import json
from importlib import resources
from pathlib import Path
from typing import Optional, Tuple

import yaml


DEFAULT_SKILLS_PACKAGE = "disesfgewuAgent.default_skills"


def _parse_frontmatter_name(markdown: str, fallback: str) -> str:
    if markdown.startswith("---"):
        parts = markdown.split("---", 2)
        if len(parts) >= 3:
            try:
                frontmatter = yaml.safe_load(parts[1]) or {}
                return frontmatter.get("name") or fallback
            except yaml.YAMLError:
                return fallback
    return fallback


def iter_default_skill_files():
    root = resources.files(DEFAULT_SKILLS_PACKAGE)
    return sorted(
        (item for item in root.iterdir() if item.name.endswith(".md")),
        key=lambda item: item.name,
    )


def get_default_skills_dir() -> str:
    """Return the installed package directory that contains bundled skills."""
    root = resources.files(DEFAULT_SKILLS_PACKAGE)
    with resources.as_file(root) as path:
        return str(Path(path).resolve())


def bootstrap_default_skills(
    base_dir: Optional[str] = None,
    config_path: Optional[str] = None,
    overwrite: bool = False,
) -> Tuple[str, str]:
    """Create a private registry for bundled default skills if missing.

    Default skill Markdown files stay in the installed package location. The
    generated registry lives in the caller's project (./.agent/skills.json) so
    embeddings can be cached without exposing project-local config.

    Returns `(skills_config_path, installed_default_skills_folder_path)`.
    """
    base = Path(base_dir or Path.cwd()).resolve()
    skill_folder = Path(get_default_skills_dir())
    private_dir = base / ".agent"
    skill_config = Path(config_path).resolve() if config_path else private_dir / "skills.json"

    private_dir.mkdir(parents=True, exist_ok=True)

    registry = {}
    for resource in iter_default_skill_files():
        content = resource.read_text(encoding="utf-8")
        name = _parse_frontmatter_name(content, Path(resource.name).stem)
        registry[name] = {"relativePath": resource.name}

    if overwrite or not skill_config.exists():
        skill_config.write_text(
            json.dumps(registry, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    else:
        # Preserve cached embeddings for bundled skills, but keep this registry
        # scoped to package defaults. Project-local custom skills should use a
        # caller-provided skillConfigPath + skillFolderPath pair.
        with skill_config.open("r", encoding="utf-8") as f:
            existing = json.load(f)
        merged = {}
        for name, entry in registry.items():
            previous = existing.get(name, {})
            merged_entry = dict(previous) if isinstance(previous, dict) else {}
            merged_entry.update(entry)
            merged[name] = merged_entry
        if merged != existing:
            skill_config.write_text(
                json.dumps(merged, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

    return str(skill_config), str(skill_folder)


def discover_skills_in_dir(folder_path: str, config_path: Optional[str] = None) -> Tuple[str, str]:
    """Recursively discover markdown skills in folder_path and build a skills.json registry.

    Returns (skills_config_path, folder_path).
    """
    root = Path(folder_path).resolve()
    cfg_file = Path(config_path).resolve() if config_path else root / "skills.json"

    registry = {}
    for md_file in sorted(root.rglob("*.md"), key=lambda p: str(p)):
        if md_file.name == "README.md":
            continue
        try:
            content = md_file.read_text(encoding="utf-8")
        except Exception:
            continue
        rel_path = str(md_file.relative_to(root)).replace("\\", "/")
        name = _parse_frontmatter_name(content, md_file.stem)
        registry[name] = {"relativePath": rel_path}

    cfg_file.write_text(
        json.dumps(registry, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return str(cfg_file), str(root)
