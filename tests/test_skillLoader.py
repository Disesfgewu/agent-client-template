import unittest
from unittest.mock import patch, Mock, MagicMock
import sys
import os
import json
import tempfile
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from disesfgewuAgent.skillLoader import skillLoader


class TestSkillLoader(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.skills_dir = os.path.join(self.test_dir, "skills")
        os.makedirs(self.skills_dir)
        
        self.skill1_content = """---
name: skill-1
description: This is skill 1 description for testing
version: 1.0.0
tags:
  - test
---

# Skill 1

This is skill 1 content."""
        
        self.skill2_content = """---
name: skill-2
description: This is skill 2 description for testing
version: 1.0.0
tags:
  - test
---

# Skill 2

This is skill 2 content."""
        
        with open(os.path.join(self.skills_dir, "skill1.md"), "w") as f:
            f.write(self.skill1_content)
        with open(os.path.join(self.skills_dir, "skill2.md"), "w") as f:
            f.write(self.skill2_content)
        
        self.config = {
            "skill1": {
                "relativePath": "skill1.md"
            },
            "skill2": {
                "relativePath": "skill2.md"
            }
        }
        
        self.config_path = os.path.join(self.test_dir, "skills.json")
        with open(self.config_path, "w") as f:
            json.dump(self.config, f)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    @patch('disesfgewuAgent.skillLoader.load_dotenv')
    @patch('disesfgewuAgent.skillLoader.OpenAI')
    def test_init_loads_env_and_creates_client(self, mock_openai, mock_dotenv):
        os.environ["EMBEDDING_API"] = "test-api-key"
        
        loader = skillLoader(self.config_path, self.skills_dir)
        
        mock_dotenv.assert_called_once()
        mock_openai.assert_called_once()
        self.assertIsNotNone(loader._client)
        
        del os.environ["EMBEDDING_API"]

    @patch('disesfgewuAgent.skillLoader.load_dotenv')
    @patch('disesfgewuAgent.skillLoader.OpenAI')
    def test_init_raises_without_api_key(self, mock_openai, mock_dotenv):
        if "EMBEDDING_API" in os.environ:
            del os.environ["EMBEDDING_API"]
        
        with self.assertRaises(ValueError) as context:
            skillLoader(self.config_path, self.skills_dir)
        
        self.assertIn("EMBEDDING_API", str(context.exception))

    @patch('disesfgewuAgent.skillLoader.load_dotenv')
    @patch('disesfgewuAgent.skillLoader.OpenAI')
    def test_embed_calls_api_correctly(self, mock_openai, mock_dotenv):
        os.environ["EMBEDDING_API"] = "test-api-key"
        
        mock_client = Mock()
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1, 0.2, 0.3])]
        mock_client.embeddings.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        loader = skillLoader(self.config_path, self.skills_dir)
        result = loader._embed("test text")
        
        mock_client.embeddings.create.assert_called_once()
        call_kwargs = mock_client.embeddings.create.call_args.kwargs
        self.assertEqual(call_kwargs["input"], ["test text"])
        self.assertEqual(result, [0.1, 0.2, 0.3])
        
        del os.environ["EMBEDDING_API"]

    @patch('disesfgewuAgent.skillLoader.load_dotenv')
    @patch('disesfgewuAgent.skillLoader.OpenAI')
    def test_load_reads_skills_and_creates_index(self, mock_openai, mock_dotenv):
        os.environ["EMBEDDING_API"] = "test-api-key"
        
        mock_client = Mock()
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1] * 1024)]
        mock_client.embeddings.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        loader = skillLoader(self.config_path, self.skills_dir)
        skills = loader.load()
        
        self.assertEqual(len(skills), 2)
        self.assertIn("skill_embedding", skills[0])
        self.assertIn("skill_name", skills[0])
        self.assertIn("skill_context", skills[0])
        self.assertIn("skill_frontmatter", skills[0])
        self.assertIsNotNone(loader._index)
        
        del os.environ["EMBEDDING_API"]

    @patch('disesfgewuAgent.skillLoader.load_dotenv')
    @patch('disesfgewuAgent.skillLoader.OpenAI')
    def test_load_parses_frontmatter(self, mock_openai, mock_dotenv):
        os.environ["EMBEDDING_API"] = "test-api-key"
        
        mock_client = Mock()
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1] * 1024)]
        mock_client.embeddings.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        loader = skillLoader(self.config_path, self.skills_dir)
        skills = loader.load()
        
        skill = skills[0]
        self.assertEqual(skill["skill_name"], "skill-1")
        self.assertIn("skill 1 description", skill["skill_description"])
        self.assertIn("Skill 1", skill["skill_context"])
        self.assertEqual(skill["skill_frontmatter"]["version"], "1.0.0")
        
        del os.environ["EMBEDDING_API"]

    @patch('disesfgewuAgent.skillLoader.load_dotenv')
    @patch('disesfgewuAgent.skillLoader.OpenAI')
    def test_load_uses_cached_embeddings(self, mock_openai, mock_dotenv):
        os.environ["EMBEDDING_API"] = "test-api-key"
        
        cached_embedding = [0.5] * 1024
        config_with_cache = {
            "skill1": {
                "relativePath": "skill1.md",
                "embedding": cached_embedding
            },
            "skill2": {
                "relativePath": "skill2.md",
                "embedding": cached_embedding
            }
        }
        
        config_path = os.path.join(self.test_dir, "skills_cached.json")
        with open(config_path, "w") as f:
            json.dump(config_with_cache, f)
        
        mock_client = Mock()
        mock_openai.return_value = mock_client
        
        loader = skillLoader(config_path, self.skills_dir)
        skills = loader.load()
        
        mock_client.embeddings.create.assert_not_called()
        self.assertEqual(len(skills), 2)
        
        del os.environ["EMBEDDING_API"]

    @patch('disesfgewuAgent.skillLoader.load_dotenv')
    @patch('disesfgewuAgent.skillLoader.OpenAI')
    def test_getSkill_returns_correct_skill(self, mock_openai, mock_dotenv):
        os.environ["EMBEDDING_API"] = "test-api-key"
        
        mock_client = Mock()
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1] * 1024)]
        mock_client.embeddings.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        loader = skillLoader(self.config_path, self.skills_dir)
        loader.load()
        
        skill = loader.getSkill(0)
        self.assertEqual(skill["skill_name"], "skill-1")
        self.assertIn("Skill 1", skill["skill_context"])
        
        del os.environ["EMBEDDING_API"]

    @patch('disesfgewuAgent.skillLoader.load_dotenv')
    @patch('disesfgewuAgent.skillLoader.OpenAI')
    def test_getSkill_raises_on_invalid_index(self, mock_openai, mock_dotenv):
        os.environ["EMBEDDING_API"] = "test-api-key"
        
        mock_client = Mock()
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1] * 1024)]
        mock_client.embeddings.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        loader = skillLoader(self.config_path, self.skills_dir)
        loader.load()
        
        with self.assertRaises(IndexError):
            loader.getSkill(999)
        
        del os.environ["EMBEDDING_API"]

    @patch('disesfgewuAgent.skillLoader.load_dotenv')
    @patch('disesfgewuAgent.skillLoader.OpenAI')
    def test_getEmbedding_returns_vector(self, mock_openai, mock_dotenv):
        os.environ["EMBEDDING_API"] = "test-api-key"
        
        mock_client = Mock()
        mock_response = Mock()
        test_embedding = [0.1] * 1024
        mock_response.data = [Mock(embedding=test_embedding)]
        mock_client.embeddings.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        loader = skillLoader(self.config_path, self.skills_dir)
        loader.load()
        
        embedding = loader.getEmbedding(0)
        self.assertEqual(len(embedding), 1024)
        self.assertEqual(embedding, test_embedding)
        
        del os.environ["EMBEDDING_API"]

    @patch('disesfgewuAgent.skillLoader.load_dotenv')
    @patch('disesfgewuAgent.skillLoader.OpenAI')
    def test_search_returns_top_k_results(self, mock_openai, mock_dotenv):
        os.environ["EMBEDDING_API"] = "test-api-key"
        
        mock_client = Mock()
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1] * 1024)]
        mock_client.embeddings.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        loader = skillLoader(self.config_path, self.skills_dir)
        loader.load()
        
        results = loader.search("test query", top_k=2)
        
        self.assertEqual(len(results), 2)
        self.assertIn("score", results[0])
        self.assertIn("skill_name", results[0])
        
        del os.environ["EMBEDDING_API"]

    @patch('disesfgewuAgent.skillLoader.load_dotenv')
    @patch('disesfgewuAgent.skillLoader.OpenAI')
    def test_search_raises_when_not_loaded(self, mock_openai, mock_dotenv):
        os.environ["EMBEDDING_API"] = "test-api-key"
        
        mock_client = Mock()
        mock_openai.return_value = mock_client
        
        loader = skillLoader(self.config_path, self.skills_dir)
        
        with self.assertRaises(ValueError) as context:
            loader.search("test query")
        
        self.assertIn("Skills not loaded", str(context.exception))
        
        del os.environ["EMBEDDING_API"]

    @patch('disesfgewuAgent.skillLoader.load_dotenv')
    @patch('disesfgewuAgent.skillLoader.OpenAI')
    def test_composeSkills_combines_multiple_skills(self, mock_openai, mock_dotenv):
        os.environ["EMBEDDING_API"] = "test-api-key"
        
        mock_client = Mock()
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1] * 1024)]
        mock_client.embeddings.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        loader = skillLoader(self.config_path, self.skills_dir)
        loader.load()
        
        composed = loader.composeSkills([0, 1])
        
        self.assertIn("skill-1", composed)
        self.assertIn("skill-2", composed)
        self.assertIn("Skill 1", composed)
        self.assertIn("Skill 2", composed)
        self.assertIn("===", composed)
        
        del os.environ["EMBEDDING_API"]


if __name__ == '__main__':
    unittest.main()
