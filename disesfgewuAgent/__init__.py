"""disesfgewuAgent - a skills-driven, multi-provider LLM agent client."""

from disesfgewuAgent.agent import AgentClient
from disesfgewuAgent.defaultSkills import bootstrap_default_skills, get_default_skills_dir, discover_skills_in_dir
from disesfgewuAgent.llmRouter import llmRouter
from disesfgewuAgent.skillLoader import skillLoader
from disesfgewuAgent.inputFileManager import inputFileManager
from disesfgewuAgent.skillSync import sync_skills, SkillSyncer, SkillSyncError, DEFAULT_SKILL_LIBRARY_REPO

__version__ = "1.5.0"

__all__ = [
    "AgentClient",
    "bootstrap_default_skills",
    "get_default_skills_dir",
    "discover_skills_in_dir",
    "llmRouter",
    "skillLoader",
    "inputFileManager",
    "sync_skills",
    "SkillSyncer",
    "SkillSyncError",
    "DEFAULT_SKILL_LIBRARY_REPO",
    "__version__",
]
