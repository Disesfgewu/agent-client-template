import asyncio
import json
import os
import re
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
import faiss
import numpy as np
import yaml


class skillLoader:
    def __init__(self, skillConfig: str, skillFolderPath: str):
        load_dotenv()

        self._skillConfig = skillConfig
        self._skillPath = skillFolderPath
        self._skills = []
        self._skill_map = {}
        self._global_skills = []
        self._index = None
        self._loaded = False

        self._embedding_url = os.getenv(
            "EMBEDDING_URL", "https://integrate.api.nvidia.com/v1"
        )
        self._embedding_api = os.getenv("EMBEDDING_API")
        self._embedding_model = os.getenv("EMBEDDING_MODEL", "nvidia/nv-embed-v1")
        self._client: Optional[OpenAI] = None

    def _getClient(self) -> OpenAI:
        if self._client is None:
            if not self._embedding_api:
                raise ValueError("EMBEDDING_API not found in environment")
            self._client = OpenAI(
                api_key=self._embedding_api, base_url=self._embedding_url
            )
        return self._client

    def _parse_frontmatter(self, content: str) -> tuple:
        pattern = r"^---\s*\n(.*?)\n---\s*\n(.*)$"
        match = re.match(pattern, content, re.DOTALL)

        if not match:
            return {}, content

        frontmatter_str = match.group(1)
        body = match.group(2)

        try:
            frontmatter = yaml.safe_load(frontmatter_str)
        except yaml.YAMLError:
            frontmatter = {}

        return frontmatter or {}, body

    def _embed(self, text: str) -> list:
        client = self._getClient()
        response = client.embeddings.create(
            input=[text],
            model=self._embedding_model,
            encoding_format="float",
            extra_body={"input_type": "query", "truncate": "END"},
        )
        return response.data[0].embedding

    def load(self, force: bool = False) -> list:
        # Building the FAISS index and (re)embedding is expensive; skip it once
        # loaded. Callers that change skills on disk can pass force=True.
        if self._loaded and not force:
            return self._skills

        with open(self._skillConfig, "r", encoding="utf-8") as f:
            config = json.load(f)

        self._skills = []
        self._skill_map = {}
        self._global_skills = []
        embeddings = []
        updated_config = {}
        has_new_embeddings = False

        for skill_name, skill_info in config.items():
            skill_path = os.path.join(self._skillPath, skill_info["relativePath"])

            with open(skill_path, "r", encoding="utf-8") as f:
                full_content = f.read()

            frontmatter, body = self._parse_frontmatter(full_content)

            description = frontmatter.get("description", "")
            is_global = bool(
                frontmatter.get("global", False)
                or "shared" in Path(skill_info["relativePath"]).parts
                or skill_info.get("global", False)
            )

            if "embedding" in skill_info and skill_info["embedding"]:
                embedding = skill_info["embedding"]
            else:
                embedding = self._embed(description) if description else [0.0] * 1024
                has_new_embeddings = True

            updated_entry = dict(skill_info)
            updated_entry["embedding"] = embedding
            updated_config[skill_name] = updated_entry

            canonical_name = frontmatter.get("name", skill_name)

            skill_dict = {
                "skill_embedding": embedding,
                "skill_name": canonical_name,
                "skill_description": description,
                "skill_file_name": skill_info["relativePath"],
                "skill_context": body,
                "skill_frontmatter": frontmatter,
                "domain": frontmatter.get("domain", ""),
                "category": frontmatter.get("category", ""),
                "requires": frontmatter.get("requires", []),
                "optional": frontmatter.get("optional", []),
                "is_global": is_global,
            }

            idx = len(self._skills)
            skill_dict["idx"] = idx

            self._skills.append(skill_dict)
            self._skill_map[canonical_name] = skill_dict
            self._skill_map[skill_name] = skill_dict

            if is_global:
                self._global_skills.append(skill_dict)

            embeddings.append(embedding)

        if has_new_embeddings:
            with open(self._skillConfig, "w", encoding="utf-8") as f:
                json.dump(updated_config, f, indent=2, ensure_ascii=False)

        if embeddings:
            embeddings_array = np.array(embeddings, dtype=np.float32)
            dimension = embeddings_array.shape[1]
            self._index = faiss.IndexFlatIP(dimension)
            faiss.normalize_L2(embeddings_array)
            self._index.add(embeddings_array)

        self._loaded = True
        return self._skills

    def resolve_dependencies(self, matched_skills: list) -> list:
        """Expand matched skills with their prerequisites specified in 'requires'.

        Guards against circular dependencies and missing prerequisites.
        """
        resolved = []
        visited = set()

        def _traverse(skill_name: str, parent_score: float = 1.0):
            if skill_name in visited:
                return
            visited.add(skill_name)

            skill = self._skill_map.get(skill_name)
            if not skill:
                return

            requires = skill.get("requires", [])
            if isinstance(requires, list):
                for req_name in requires:
                    if isinstance(req_name, str):
                        _traverse(req_name, parent_score)

            skill_copy = skill.copy()
            if "score" not in skill_copy:
                skill_copy["score"] = parent_score
            if skill_copy not in resolved:
                resolved.append(skill_copy)

        for s in matched_skills:
            name = s.get("skill_name")
            score = s.get("score", 1.0)
            if name:
                _traverse(name, score)

        return resolved

    def getEmbedding(self, idx: int) -> list:
        if idx < 0 or idx >= len(self._skills):
            raise IndexError(f"Skill index {idx} out of range")
        return self._skills[idx]["skill_embedding"]

    def getSkill(self, idx: int) -> dict:
        if idx < 0 or idx >= len(self._skills):
            raise IndexError(f"Skill index {idx} out of range")
        return self._skills[idx]

    def search(self, query: str, top_k: int = 3, min_score: float = 0.3) -> list:
        if not self._loaded:
            raise ValueError("Skills not loaded. Call load() first.")

        if not self._index or not self._skills:
            return []

        try:
            query_embedding = self._embed(query)
        except Exception:
            return []
        query_array = np.array([query_embedding], dtype=np.float32)
        faiss.normalize_L2(query_array)

        k = min(top_k, len(self._skills))
        distances, indices = self._index.search(query_array, k)

        results = []
        for i, idx in enumerate(indices[0]):
            if idx >= 0:
                score = float(distances[0][i])
                if score < min_score:
                    continue
                skill = self._skills[idx].copy()
                skill["score"] = score
                skill["idx"] = int(idx)
                results.append(skill)

        return results

    def composeSkills(self, idxs: list, include_global: bool = True) -> str:
        composed = []
        added_names = set()

        if include_global and self._global_skills:
            global_blocks = []
            for g_skill in self._global_skills:
                if g_skill["skill_name"] not in added_names:
                    global_blocks.append(
                        f"=== System Guideline: {g_skill['skill_name']} ===\n{g_skill['skill_context']}"
                    )
                    added_names.add(g_skill["skill_name"])
            if global_blocks:
                composed.append("\n\n".join(global_blocks))

        topic_blocks = []
        for idx in idxs:
            skill = self.getSkill(idx)
            if skill["skill_name"] not in added_names:
                topic_blocks.append(
                    f"=== {skill['skill_name']} ===\n{skill['skill_context']}"
                )
                added_names.add(skill["skill_name"])

        if topic_blocks:
            composed.append("\n\n".join(topic_blocks))

        return "\n\n".join(composed)

    def searchAndCompose(
        self, query: str, top_k: int = 3, min_score: float = 0.3
    ) -> tuple:
        results = self.search(query, top_k=top_k, min_score=min_score)
        
        # Expand matched skills with their prerequisites via DAG resolution
        expanded_skills = self.resolve_dependencies(results) if results else []

        # Gather indices of all expanded skills
        idxs = [s["idx"] for s in expanded_skills if "idx" in s]

        composed = self.composeSkills(idxs, include_global=True)
        return composed, expanded_skills if expanded_skills else results

    async def loadAsync(self) -> list:
        return await asyncio.to_thread(self.load)

    async def searchAsync(
        self, query: str, top_k: int = 3, min_score: float = 0.3
    ) -> list:
        return await asyncio.to_thread(self.search, query, top_k, min_score)

    async def searchAndComposeAsync(
        self, query: str, top_k: int = 3, min_score: float = 0.3
    ) -> tuple:
        return await asyncio.to_thread(
            self.searchAndCompose, query, top_k, min_score
        )
