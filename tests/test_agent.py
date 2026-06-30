import unittest
import asyncio
import tempfile
import shutil
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from disesfgewuAgent.agent import AgentClient
from tests.live_api import live_api_available, SKIP_REASON

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API_CONFIG_PATH = os.path.join(ROOT, "config", "api.local.json")
HISTORY_DIR = os.path.join(ROOT, "history")

# Inline config keeps the offline logic tests self-contained: they construct an
# AgentClient but never hit the network, so a fake single-model config is enough.
SAMPLE_API_CONFIG = [
    {
        "provider": "test",
        "protocol": "openai",
        "endpointUrl": "http://localhost/v1/chat/completions",
        "modelName": "test-model",
        "maxInputToken": 128000,
        "maxOutputToken": 4096,
        "apiKey": "",
    }
]


class TestAgentLogic(unittest.TestCase):
    def setUp(self):
        self.config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "config",
            "skills.json",
        )
        self.skills_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "skills",
        )
        self.agent = AgentClient(
            self.config_path, self.skills_dir, SAMPLE_API_CONFIG, 32000
        )

    def test_countTokens(self):
        text = "Hello, world!"
        tokens = self.agent._countTokens(text)
        self.assertIsInstance(tokens, int)
        self.assertGreater(tokens, 0)
        print(f"\n[_countTokens] '{text}' = {tokens} tokens")

    def test_countTokens_empty(self):
        tokens = self.agent._countTokens("")
        self.assertEqual(tokens, 0)

    def test_countTokens_unicode(self):
        text = "你好世界"
        tokens = self.agent._countTokens(text)
        self.assertGreater(tokens, 0)

    def test_getInputTokenSize(self):
        self.agent._inputStr = "Test input"
        self.agent._skillCache = "[SKILLS]\nSome skill content"
        self.agent._skillCacheToken = self.agent._countTokens(self.agent._skillCache)
        self.agent._inputFilesCache = "[FILES]\nSome file content"
        self.agent._inputFilesToken = self.agent._countTokens(
            self.agent._inputFilesCache
        )
        self.agent._contextWindowsToken = 100

        total = self.agent._getInputTokenSize()
        self.assertIsInstance(total, int)
        self.assertGreater(total, 100)

    def test_splitTaskInputAlgorithm_short_text(self):
        text = "Short text"
        chunks = self.agent._splitTaskInputAlgorithm(text, 1000)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0], text)

    def test_splitTaskInputAlgorithm_exact_fit(self):
        text = "A" * 100
        tokens = self.agent._countTokens(text)
        chunks = self.agent._splitTaskInputAlgorithm(text, tokens)
        self.assertEqual(len(chunks), 1)

    def test_splitTaskInputAlgorithm_long_text(self):
        text = "Word " * 5000
        chunks = self.agent._splitTaskInputAlgorithm(text, 500)
        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            chunk_tokens = self.agent._countTokens(chunk)
            self.assertLessEqual(chunk_tokens, 550)

    def test_buildPrompt_minimal(self):
        self.agent._inputStr = "Test task"
        prompt = self.agent._buildPrompt()

        self.assertIn("You are a task-oriented agent", prompt)
        self.assertIn("[TASK]", prompt)
        self.assertIn("Test task", prompt)

    def test_buildPrompt_with_skills(self):
        self.agent._inputStr = "Test task"
        self.agent._skillCache = "[SKILLS]\nSkill content here"
        prompt = self.agent._buildPrompt()

        self.assertIn("[SKILLS]", prompt)
        self.assertIn("Skill content here", prompt)

    def test_buildPrompt_with_files(self):
        self.agent._inputStr = "Test task"
        self.agent._inputFilesCache = "[FILES]\n[file.txt]\nFile content"
        prompt = self.agent._buildPrompt()

        self.assertIn("[FILES]", prompt)
        self.assertIn("File content", prompt)

    def test_buildPrompt_with_informations(self):
        self.agent._inputStr = "Test task"
        informations = "LAST: Previous answer\nREASONING: Continue working"
        prompt = self.agent._buildPrompt(informations)

        self.assertIn("[INFORMATIONS FROM LAST]", prompt)
        self.assertIn("Previous answer", prompt)

    def test_buildPrompt_with_context_memory(self):
        self.agent._inputStr = "Test task"
        self.agent._inputStrCache = "Previous iteration context"
        prompt = self.agent._buildPrompt()

        self.assertIn("[CONTEXT MEMORY]", prompt)
        self.assertIn("Previous iteration context", prompt)

    def test_buildPrompt_all_sections(self):
        self.agent._inputStr = "Test task"
        self.agent._skillCache = "[SKILLS]\nSkill"
        self.agent._inputFilesCache = "[FILES]\nFile"
        self.agent._inputStrCache = "Memory"
        informations = "LAST: Info"

        prompt = self.agent._buildPrompt(informations)

        self.assertIn("You are a task-oriented agent", prompt)
        self.assertIn("[SKILLS]", prompt)
        self.assertIn("[CONTEXT MEMORY]", prompt)
        self.assertIn("[INFORMATIONS FROM LAST]", prompt)
        self.assertIn("[FILES]", prompt)
        self.assertIn("[TASK]", prompt)

    def test_parseSignal_raw_json(self):
        signal = self.agent._parseSignal('{"status": "done", "answer": "4"}')
        self.assertEqual(signal["status"], "done")
        self.assertEqual(signal["answer"], "4")

    def test_parseSignal_fenced_json(self):
        response = 'Sure!\n```json\n{"status": "continue", "answer": "x"}\n```'
        signal = self.agent._parseSignal(response)
        self.assertEqual(signal["status"], "continue")
        self.assertEqual(signal["answer"], "x")

    def test_parseSignal_embedded_json(self):
        response = 'Here is the result: {"status": "done", "answer": "ok"} thanks'
        signal = self.agent._parseSignal(response)
        self.assertEqual(signal["status"], "done")
        self.assertEqual(signal["answer"], "ok")

    def test_parseSignal_invalid_falls_back_to_done(self):
        response = "I could not produce JSON."
        signal = self.agent._parseSignal(response)
        self.assertEqual(signal["status"], "done")
        self.assertEqual(signal["answer"], response)

    def test_resetState_clears_accumulators(self):
        self.agent._inputStrCache = "leftover"
        self.agent._contextWindowsToken = 123
        self.agent._skillCacheToken = 5
        self.agent._inputFilesToken = 7
        self.agent._history = [{"iteration": 1, "response": "x"}]

        self.agent._resetState()

        self.assertEqual(self.agent._inputStrCache, "")
        self.assertEqual(self.agent._contextWindowsToken, 0)
        self.assertEqual(self.agent._skillCacheToken, 0)
        self.assertEqual(self.agent._inputFilesToken, 0)
        self.assertEqual(self.agent._history, [])

    def test_truncateToTokens_limits_length(self):
        text = "word " * 1000
        truncated = self.agent._truncateToTokens(text, 50)
        self.assertLessEqual(self.agent._countTokens(truncated), 50)

    def test_truncateToTokens_keeps_short_text(self):
        text = "short text"
        self.assertEqual(self.agent._truncateToTokens(text, 1000), text)


@unittest.skipUnless(live_api_available(), SKIP_REASON)
class TestAgentReal(unittest.IsolatedAsyncioTestCase):
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

    async def test_getSkills(self):
        agent = AgentClient(
            self.config_path, self.skills_dir, API_CONFIG_PATH, 32000,
            historyDir=HISTORY_DIR,
        )
        agent._inputStr = "code review best practices"
        await agent._skillLoader.loadAsync()
        await agent._getSkills()

        self.assertIsInstance(agent._skillCache, str)
        self.assertIsInstance(agent._skillCacheToken, int)

        if agent._skillCache:
            self.assertIn("[SKILLS]", agent._skillCache)
            self.assertGreater(agent._skillCacheToken, 0)
            print(f"\n[_getSkills] {agent._skillCacheToken} tokens")

        await agent._router.close()

    async def test_connect(self):
        agent = AgentClient(
            self.config_path, self.skills_dir, API_CONFIG_PATH, 32000,
            historyDir=HISTORY_DIR,
        )
        response = await agent._connect("Reply with just the word 'ok'.")

        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 0)
        print(f"\n[_connect] {response[:100]}")

        await agent._router.close()

    async def test_ask_simple(self):
        async with AgentClient(
            self.config_path, self.skills_dir, API_CONFIG_PATH, 32000,
            historyDir=HISTORY_DIR,
        ) as agent:
            result = await agent.ask("What is 2+2? Reply with just the number.")

        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)
        print(f"\n[ask simple] {result[:100]}")

    async def test_ask_with_files(self):
        test_dir = tempfile.mkdtemp()
        try:
            test_file = os.path.join(test_dir, "test.txt")
            with open(test_file, "w", encoding="utf-8") as f:
                f.write("The secret number is 42.")

            async with AgentClient(
                self.config_path, self.skills_dir, API_CONFIG_PATH, 32000,
                historyDir=HISTORY_DIR,
            ) as agent:
                result = await agent.ask(
                    "What is the secret number from the file?",
                    inputFiles=[test_file],
                )

            self.assertIsInstance(result, str)
            self.assertGreater(len(result), 0)
            print(f"\n[ask with files] {result[:100]}")
        finally:
            shutil.rmtree(test_dir)

    async def test_backupHistory(self):
        agent = AgentClient(
            self.config_path, self.skills_dir, API_CONFIG_PATH, 32000,
            historyDir=HISTORY_DIR,
        )
        agent._history = [
            {"iteration": 1, "response": "test response 1"},
            {"iteration": 2, "response": "test response 2"},
        ]

        await agent._backupHistory()

        history_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "history",
        )
        self.assertTrue(os.path.exists(history_dir))

        files = os.listdir(history_dir)
        self.assertGreater(len(files), 0)
        print(f"\n[_backupHistory] {len(files)} history files")

        await agent._router.close()


if __name__ == "__main__":
    unittest.main()
