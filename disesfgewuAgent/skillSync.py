import json
import logging
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, Optional, Tuple

from disesfgewuAgent.defaultSkills import _parse_frontmatter_name

logger = logging.getLogger(__name__)

DEFAULT_SKILL_LIBRARY_REPO = "Disesfgewu/skill-library"


class SkillSyncError(Exception):
    """Raised when syncing skills from a remote repository fails."""

    pass


def _normalize_github_repo(source: str) -> Tuple[str, str]:
    """Parse 'owner/repo' or full GitHub URL into (owner, repo)."""
    src = source.strip()
    if src.startswith("https://github.com/"):
        src = src[len("https://github.com/") :]
    elif src.startswith("http://github.com/"):
        src = src[len("http://github.com/") :]

    src = src.rstrip("/").removesuffix(".git")
    parts = [p for p in src.split("/") if p]
    if len(parts) >= 2:
        return parts[0], parts[1]
    raise SkillSyncError(f"Invalid GitHub repository source format: '{source}'. Expected 'owner/repo'.")


class SkillSyncer:
    """Synchronizes default/remote skills from a GitHub skill library repository."""

    def __init__(
        self,
        source: str = DEFAULT_SKILL_LIBRARY_REPO,
        branch: str = "main",
        timeout: float = 10.0,
    ):
        self.source = source
        self.branch = branch
        self.timeout = timeout

    def _fetch_url(self, url: str) -> str:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "disesfgewuAgent-SkillSync/1.4.1",
                "Accept": "application/json, text/plain, */*",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                if resp.status != 200:
                    raise SkillSyncError(f"HTTP {resp.status} while fetching {url}")
                return resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            raise SkillSyncError(f"HTTP error {e.code} while fetching {url}: {e.reason}") from e
        except urllib.error.URLError as e:
            raise SkillSyncError(f"Network error while connecting to {url}: {e.reason}") from e
        except Exception as e:
            raise SkillSyncError(f"Failed to fetch {url}: {e}") from e

    def sync(
        self,
        base_dir: Optional[str] = None,
        config_path: Optional[str] = None,
        overwrite: bool = False,
    ) -> Tuple[str, str]:
        """Download remote skills and update local `.agent/skills.json`.

        Returns `(skills_config_path, synced_skills_folder_path)`.
        Raises `SkillSyncError` if network fetch fails.
        """
        owner, repo = _normalize_github_repo(self.source)
        raw_base_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{self.branch}/"

        # Try fetching registry.json or fallback to skills.json
        registry_url = raw_base_url + "registry.json"
        try:
            registry_content = self._fetch_url(registry_url)
        except SkillSyncError:
            registry_url = raw_base_url + "skills.json"
            registry_content = self._fetch_url(registry_url)

        try:
            remote_registry: Dict = json.loads(registry_content)
        except json.JSONDecodeError as e:
            raise SkillSyncError(f"Invalid JSON registry returned from {registry_url}: {e}") from e

        base = Path(base_dir or Path.cwd()).resolve()
        private_dir = base / ".agent"
        synced_dir = private_dir / "synced_skills"
        skill_config = Path(config_path).resolve() if config_path else private_dir / "skills.json"

        private_dir.mkdir(parents=True, exist_ok=True)
        synced_dir.mkdir(parents=True, exist_ok=True)

        existing_config = {}
        if skill_config.exists():
            try:
                with skill_config.open("r", encoding="utf-8") as f:
                    existing_config = json.load(f)
            except Exception:
                existing_config = {}

        new_registry = {}
        for skill_name, skill_info in remote_registry.items():
            if isinstance(skill_info, str):
                rel_path = skill_info
            elif isinstance(skill_info, dict):
                rel_path = skill_info.get("relativePath") or f"skills/{skill_name}.md"
            else:
                rel_path = f"skills/{skill_name}.md"

            skill_url = raw_base_url + rel_path
            skill_content = self._fetch_url(skill_url)

            filename = Path(rel_path).name
            target_file = synced_dir / filename
            target_file.write_text(skill_content, encoding="utf-8")

            parsed_name = _parse_frontmatter_name(skill_content, skill_name)

            previous_entry = existing_config.get(parsed_name, {})
            entry = dict(previous_entry) if isinstance(previous_entry, dict) else {}
            entry["relativePath"] = filename

            new_registry[parsed_name] = entry

        skill_config.write_text(
            json.dumps(new_registry, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        logger.info(f"Successfully synced {len(new_registry)} skills from {self.source} to {synced_dir}")
        return str(skill_config), str(synced_dir)


def sync_skills(
    source: str = DEFAULT_SKILL_LIBRARY_REPO,
    base_dir: Optional[str] = None,
    config_path: Optional[str] = None,
    branch: str = "main",
    timeout: float = 10.0,
    overwrite: bool = False,
) -> Tuple[str, str]:
    """Helper function to sync default skills from remote GitHub repository."""
    syncer = SkillSyncer(source=source, branch=branch, timeout=timeout)
    return syncer.sync(base_dir=base_dir, config_path=config_path, overwrite=overwrite)
