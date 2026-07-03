import json
import shutil
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


def bootstrap_default_skills(
    base_dir: Optional[str] = None,
    skills_dir: Optional[str] = None,
    config_path: Optional[str] = None,
    overwrite: bool = False,
) -> Tuple[str, str]:
    """Create local default skills and a private skills registry if missing.

    Returns `(skills_config_path, skills_folder_path)`.
    """
    base = Path(base_dir or Path.cwd()).resolve()
    skill_folder = Path(skills_dir).resolve() if skills_dir else base / "skills"
    private_dir = base / ".agent"
    skill_config = Path(config_path).resolve() if config_path else private_dir / "skills.json"

    skill_folder.mkdir(parents=True, exist_ok=True)
    private_dir.mkdir(parents=True, exist_ok=True)

    registry = {}
    for resource in iter_default_skill_files():
        destination = skill_folder / resource.name
        if overwrite or not destination.exists():
            with resources.as_file(resource) as source:
                shutil.copyfile(source, destination)
        content = destination.read_text(encoding="utf-8")
        name = _parse_frontmatter_name(content, destination.stem)
        registry[name] = {"relativePath": destination.name}

    if overwrite or not skill_config.exists():
        skill_config.write_text(
            json.dumps(registry, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    else:
        # Preserve local cached embeddings and custom entries. Add newly bundled
        # skills that are missing from an older registry.
        with skill_config.open("r", encoding="utf-8") as f:
            existing = json.load(f)
        changed = False
        for name, entry in registry.items():
            if name not in existing:
                existing[name] = entry
                changed = True
        if changed:
            skill_config.write_text(
                json.dumps(existing, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

    return str(skill_config), str(skill_folder)