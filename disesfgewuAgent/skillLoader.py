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
        self._index = None

        embedding_url = os.getenv(
            "EMBEDDING_URL", "https://integrate.api.nvidia.com/v1"
        )
        embedding_api = os.getenv("EMBEDDING_API")
        self._embedding_model = os.getenv("EMBEDDING_MODEL", "nvidia/nv-embed-v1")

        if not embedding_api:
            raise ValueError("EMBEDDING_API not found in environment")

        self._client = OpenAI(api_key=embedding_api, base_url=embedding_url)

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
        response = self._client.embeddings.create(
            input=[text],
            model=self._embedding_model,
            encoding_format="float",
            extra_body={"input_type": "query", "truncate": "NONE"},
        )
        return response.data[0].embedding

    def load(self) -> list:
        with open(self._skillConfig, "r", encoding="utf-8") as f:
            config = json.load(f)

        self._skills = []
        embeddings = []
        updated_config = {}

        for skill_name, skill_info in config.items():
            skill_path = os.path.join(self._skillPath, skill_info["relativePath"])

            with open(skill_path, "r", encoding="utf-8") as f:
                full_content = f.read()

            frontmatter, body = self._parse_frontmatter(full_content)

            description = frontmatter.get("description", "")

            if "embedding" in skill_info and skill_info["embedding"]:
                embedding = skill_info["embedding"]
            else:
                embedding = self._embed(description)

            updated_config[skill_name] = {
                "relativePath": skill_info["relativePath"],
                "embedding": embedding,
            }

            skill_dict = {
                "skill_embedding": embedding,
                "skill_name": frontmatter.get("name", skill_name),
                "skill_description": description,
                "skill_file_name": skill_info["relativePath"],
                "skill_context": body,
                "skill_frontmatter": frontmatter,
            }

            self._skills.append(skill_dict)
            embeddings.append(embedding)

        with open(self._skillConfig, "w", encoding="utf-8") as f:
            json.dump(updated_config, f, indent=2)

        if embeddings:
            embeddings_array = np.array(embeddings, dtype=np.float32)
            dimension = embeddings_array.shape[1]
            self._index = faiss.IndexFlatIP(dimension)
            faiss.normalize_L2(embeddings_array)
            self._index.add(embeddings_array)

        return self._skills

    def getEmbedding(self, idx: int) -> list:
        if idx < 0 or idx >= len(self._skills):
            raise IndexError(f"Skill index {idx} out of range")
        return self._skills[idx]["skill_embedding"]

    def getSkill(self, idx: int) -> dict:
        if idx < 0 or idx >= len(self._skills):
            raise IndexError(f"Skill index {idx} out of range")
        return self._skills[idx]

    def search(self, query: str, top_k: int = 3) -> list:
        if not self._index or not self._skills:
            raise ValueError("Skills not loaded. Call load() first.")

        query_embedding = self._embed(query)
        query_array = np.array([query_embedding], dtype=np.float32)
        faiss.normalize_L2(query_array)

        k = min(top_k, len(self._skills))
        distances, indices = self._index.search(query_array, k)

        results = []
        for i, idx in enumerate(indices[0]):
            if idx >= 0:
                skill = self._skills[idx].copy()
                skill["score"] = float(distances[0][i])
                results.append(skill)

        return results

    def composeSkills(self, idxs: list) -> str:
        composed = []
        for idx in idxs:
            skill = self.getSkill(idx)
            composed.append(f"=== {skill['skill_name']} ===\n{skill['skill_context']}")

        return "\n\n".join(composed)
