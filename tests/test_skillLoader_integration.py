import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from disesfgewuAgent.skillLoader import skillLoader


class TestSkillLoaderIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "config",
            "skills.json"
        )
        cls.skills_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "skills"
        )
        cls.loader = skillLoader(cls.config_path, cls.skills_dir)
        cls.skills = cls.loader.load()

    def test_load_returns_skills(self):
        self.assertGreater(len(self.skills), 0)
        for skill in self.skills:
            self.assertIn("skill_embedding", skill)
            self.assertIn("skill_name", skill)
            self.assertIn("skill_context", skill)
            self.assertIsInstance(skill["skill_embedding"], list)
            self.assertGreater(len(skill["skill_embedding"]), 0)

    def test_embedding_dimension(self):
        embedding = self.loader.getEmbedding(0)
        self.assertIsInstance(embedding, list)
        self.assertGreater(len(embedding), 100)
        print(f"\n[Embedding dimension] {len(embedding)}")

    def test_search_returns_relevant_results(self):
        results = self.loader.search("how to write good tests", top_k=2)
        
        self.assertEqual(len(results), 2)
        for result in results:
            self.assertIn("skill_name", result)
            self.assertIn("score", result)
            self.assertIsInstance(result["score"], float)
        
        print(f"\n[Search results]")
        for r in results:
            print(f"  {r['skill_name']}: score={r['score']:.4f}")

    def test_search_code_review_query(self):
        results = self.loader.search("code review best practices", top_k=1)
        
        self.assertEqual(len(results), 1)
        self.assertIn("code-review", results[0]["skill_name"])
        print(f"\n[Code review search] Top result: {results[0]['skill_name']} (score={results[0]['score']:.4f})")

    def test_composeSkills_returns_combined_content(self):
        composed = self.loader.composeSkills([0, 1])
        
        self.assertIsInstance(composed, str)
        self.assertGreater(len(composed), 100)
        self.assertIn("===", composed)
        print(f"\n[Composed skills] Length: {len(composed)} chars")


if __name__ == '__main__':
    unittest.main()
