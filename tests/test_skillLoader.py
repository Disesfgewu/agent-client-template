import unittest
import asyncio
import json
import sys
import os
import tempfile
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from disesfgewuAgent.skillLoader import skillLoader
from disesfgewuAgent.defaultSkills import bootstrap_default_skills
from tests.live_api import live_api_available, SKIP_REASON

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestDefaultSkills(unittest.TestCase):
    """Offline: every bundled skill is well-formed and registered."""

    def test_all_skill_files_have_frontmatter(self):
        loader = object.__new__(skillLoader)
        skills_dir = os.path.join(ROOT, "skills")
        md_files = [f for f in os.listdir(skills_dir) if f.endswith(".md")]
        self.assertGreater(len(md_files), 0)
        for fname in md_files:
            with open(os.path.join(skills_dir, fname), encoding="utf-8") as f:
                frontmatter, body = loader._parse_frontmatter(f.read())
            self.assertIn("name", frontmatter, f"{fname} missing name")
            self.assertIn("description", frontmatter, f"{fname} missing description")
            self.assertGreater(
                len(frontmatter["description"]), 20, f"{fname} weak description"
            )
            self.assertGreater(len(body.strip()), 50, f"{fname} weak body")

    def test_registry_points_to_real_files(self):
        with open(
            os.path.join(ROOT, "config", "skills.example.json"), encoding="utf-8"
        ) as f:
            registry = json.load(f)
        for name, info in registry.items():
            path = os.path.join(ROOT, "skills", info["relativePath"])
            self.assertTrue(os.path.exists(path), f"{name} -> {info['relativePath']}")

    def test_default_skills_registered(self):
        with open(
            os.path.join(ROOT, "config", "skills.example.json"), encoding="utf-8"
        ) as f:
            registry = json.load(f)
        for name in (
            "sql",
            "computation",
            "general-tasks",
            "code-editing",
            "web-frontend-design",
            "web-frontend-code-review",
            "flutter-frontend-design",
            "flutter-frontend-code-review",
            "mobile-code-review",
            "backend-design",
            "database-review",
            "web-research",
            "data-analysis",
            "document-ingestion",
            "file-io",
            "skills-optimize",
            "skill-creator",
            "prompt-injection-guard",
            "agent-skill-security-audit",
            "agent-action-safety-control",
        ):
            self.assertIn(name, registry)



class TestDefaultSkillBootstrap(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_bootstrap_creates_private_registry_and_skills(self):
        config_path, skills_dir = bootstrap_default_skills(base_dir=self.temp_dir)

        self.assertTrue(os.path.exists(config_path))
        self.assertTrue(os.path.isdir(skills_dir))
        self.assertIn(os.path.join(self.temp_dir, ".agent"), config_path)
        self.assertTrue(os.path.exists(os.path.join(skills_dir, "skill-creator.md")))

        with open(config_path, encoding="utf-8") as f:
            registry = json.load(f)
        self.assertIn("skill-creator", registry)
        self.assertIn("prompt-injection-guard", registry)
        self.assertNotIn("embedding", registry["skill-creator"])

class TestSkillLoaderLogic(unittest.TestCase):
    def test_parse_frontmatter_valid(self):
        loader = object.__new__(skillLoader)
        content = """---
name: test-skill
description: A test skill
version: 1.0.0
tags:
  - test
---

# Test Skill

This is the content."""

        frontmatter, body = loader._parse_frontmatter(content)

        self.assertEqual(frontmatter["name"], "test-skill")
        self.assertEqual(frontmatter["description"], "A test skill")
        self.assertEqual(frontmatter["version"], "1.0.0")
        self.assertIn("test", frontmatter["tags"])
        self.assertIn("# Test Skill", body)
        self.assertIn("This is the content.", body)

    def test_parse_frontmatter_no_frontmatter(self):
        loader = object.__new__(skillLoader)
        content = "# Just a heading\n\nSome content without frontmatter."

        frontmatter, body = loader._parse_frontmatter(content)

        self.assertEqual(frontmatter, {})
        self.assertEqual(body, content)

    def test_parse_frontmatter_empty(self):
        loader = object.__new__(skillLoader)
        content = ""

        frontmatter, body = loader._parse_frontmatter(content)

        self.assertEqual(frontmatter, {})
        self.assertEqual(body, content)

    def test_parse_frontmatter_invalid_yaml(self):
        loader = object.__new__(skillLoader)
        content = """---
invalid: yaml: content: [
---

Body content."""

        frontmatter, body = loader._parse_frontmatter(content)

        self.assertEqual(frontmatter, {})
        self.assertIn("Body content.", body)

    def test_parse_frontmatter_empty_frontmatter(self):
        loader = object.__new__(skillLoader)
        content = """---
---

Body after empty frontmatter."""

        frontmatter, body = loader._parse_frontmatter(content)

        self.assertEqual(frontmatter, {})
        self.assertIn("Body after empty frontmatter.", body)


@unittest.skipUnless(live_api_available(), SKIP_REASON)
class TestSkillLoaderReal(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "config",
            "skills.json",
        )
        cls.skills_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "skills",
        )
        cls.loader = skillLoader(cls.config_path, cls.skills_dir)
        cls.skills = cls.loader.load()

    def test_load_returns_skills(self):
        self.assertGreater(len(self.skills), 0)
        for skill in self.skills:
            self.assertIn("skill_embedding", skill)
            self.assertIn("skill_name", skill)
            self.assertIn("skill_context", skill)
            self.assertIn("skill_description", skill)
            self.assertIn("skill_frontmatter", skill)
            self.assertIsInstance(skill["skill_embedding"], list)
            self.assertGreater(len(skill["skill_embedding"]), 0)

    def test_embedding_dimension(self):
        embedding = self.loader.getEmbedding(0)
        self.assertIsInstance(embedding, list)
        self.assertGreater(len(embedding), 100)
        print(f"\n[Embedding dimension] {len(embedding)}")

    def test_getSkill_returns_correct_skill(self):
        skill = self.loader.getSkill(0)
        self.assertIn("skill_name", skill)
        self.assertIn("skill_context", skill)
        self.assertIsInstance(skill["skill_name"], str)
        self.assertGreater(len(skill["skill_name"]), 0)

    def test_getSkill_raises_on_invalid_index(self):
        with self.assertRaises(IndexError):
            self.loader.getSkill(999)

    def test_getEmbedding_raises_on_invalid_index(self):
        with self.assertRaises(IndexError):
            self.loader.getEmbedding(-1)

    def test_search_returns_results_with_idx(self):
        results = self.loader.search("code review best practices", top_k=2)

        self.assertGreater(len(results), 0)
        for result in results:
            self.assertIn("idx", result)
            self.assertIn("score", result)
            self.assertIn("skill_name", result)
            self.assertIsInstance(result["idx"], int)
            self.assertIsInstance(result["score"], float)
            self.assertGreaterEqual(result["score"], 0.3)

        print(f"\n[Search with idx]")
        for r in results:
            print(f"  idx={r['idx']}, {r['skill_name']}: score={r['score']:.4f}")

    def test_search_min_score_filters_low_scores(self):
        results_high = self.loader.search("code review", top_k=3, min_score=0.5)
        results_low = self.loader.search("code review", top_k=3, min_score=0.0)

        for r in results_high:
            self.assertGreaterEqual(r["score"], 0.5)

        self.assertGreaterEqual(len(results_low), len(results_high))

    def test_search_raises_when_not_loaded(self):
        loader = object.__new__(skillLoader)
        loader._index = None
        loader._skills = []

        with self.assertRaises(ValueError) as context:
            loader.search("test query")

        self.assertIn("Skills not loaded", str(context.exception))

    def test_composeSkills_combines_multiple(self):
        composed = self.loader.composeSkills([0, 1])

        self.assertIsInstance(composed, str)
        self.assertGreater(len(composed), 100)
        self.assertIn("===", composed)

        skill0 = self.loader.getSkill(0)
        skill1 = self.loader.getSkill(1)
        self.assertIn(skill0["skill_name"], composed)
        self.assertIn(skill1["skill_name"], composed)

        print(f"\n[Composed skills] Length: {len(composed)} chars")

    def test_searchAndCompose_returns_tuple(self):
        composed, results = self.loader.searchAndCompose(
            "how to debug code", top_k=2
        )

        self.assertIsInstance(composed, str)
        self.assertIsInstance(results, list)

        if results:
            self.assertGreater(len(composed), 0)
            self.assertIn("===", composed)
            for r in results:
                self.assertIn("idx", r)
                self.assertIn("score", r)

            print(f"\n[searchAndCompose] {len(results)} skills, {len(composed)} chars")
        else:
            self.assertEqual(composed, "")

    def test_searchAndCompose_empty_when_no_match(self):
        composed, results = self.loader.searchAndCompose(
            "xyzzy completely unrelated nonsense", top_k=1, min_score=0.99
        )

        self.assertEqual(composed, "")
        self.assertEqual(results, [])

    def test_searchAndCompose_uses_search_results_idx(self):
        composed, results = self.loader.searchAndCompose("testing", top_k=2)

        if results:
            idxs = [r["idx"] for r in results]
            expected = self.loader.composeSkills(idxs)
            self.assertEqual(composed, expected)


@unittest.skipUnless(live_api_available(), SKIP_REASON)
class TestSkillLoaderAsync(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "config",
            "skills.json",
        )
        cls.skills_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "skills",
        )
        cls.loader = skillLoader(cls.config_path, cls.skills_dir)
        cls.loader.load()

    async def test_loadAsync(self):
        loader = skillLoader(self.config_path, self.skills_dir)
        skills = await loader.loadAsync()

        self.assertGreater(len(skills), 0)
        for skill in skills:
            self.assertIn("skill_embedding", skill)
            self.assertIn("skill_name", skill)

    async def test_searchAsync(self):
        results = await self.loader.searchAsync("code review", top_k=2)

        self.assertGreater(len(results), 0)
        for r in results:
            self.assertIn("idx", r)
            self.assertIn("score", r)

        print(f"\n[searchAsync] {len(results)} results")

    async def test_searchAndComposeAsync(self):
        composed, results = await self.loader.searchAndComposeAsync(
            "debugging techniques", top_k=2
        )

        self.assertIsInstance(composed, str)
        self.assertIsInstance(results, list)

        if results:
            self.assertGreater(len(composed), 0)
            self.assertIn("===", composed)

        print(f"\n[searchAndComposeAsync] {len(results)} skills")

    async def test_searchAndComposeAsync_empty(self):
        composed, results = await self.loader.searchAndComposeAsync(
            "xyzzy nonsense", top_k=1, min_score=0.99
        )

        self.assertEqual(composed, "")
        self.assertEqual(results, [])


if __name__ == "__main__":
    unittest.main()
