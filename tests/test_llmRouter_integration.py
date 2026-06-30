import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from disesfgewuAgent.llmRouter import llmRouter


class TestLLMRouterIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.router = llmRouter()

    def test_openai_protocol_deepseek_v4_flash(self):
        api = self.router.getApi("deepseek-v4-flash")
        self.assertIsNotNone(api, "deepseek-v4-flash not found in config")
        self.assertEqual(api["protocol"], "openai")

        result = self.router._callOpenAI(api, "Say 'hello' in one word.")
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)
        print(f"\n[OpenAI protocol - deepseek-v4-flash] Response: {result[:100]}")

    def test_openai_protocol_via_connect(self):
        result = self.router.connect("What is 2+2? Reply with just the number.", modelName="deepseek-v4-flash")
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)
        print(f"\n[connect() - deepseek-v4-flash] Response: {result[:100]}")

    def test_anthropic_protocol_qwen37_plus(self):
        api = self.router.getApi("qwen3.7-plus")
        self.assertIsNotNone(api, "qwen3.7-plus not found in config")
        self.assertEqual(api["protocol"], "anthropic")

        result = self.router._callAnthropic(api, "Say 'hello' in one word.")
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)
        print(f"\n[Anthropic protocol - qwen3.7-plus] Response: {result[:100]}")

    def test_anthropic_protocol_via_connect(self):
        result = self.router.connect("What is 3+3? Reply with just the number.", modelName="qwen3.7-plus")
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)
        print(f"\n[connect() - qwen3.7-plus] Response: {result[:100]}")

    def test_fallback_between_models(self):
        result = self.router.connect("Say 'test passed' in exactly those two words.")
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)
        print(f"\n[Fallback] Response: {result[:100]}")


if __name__ == '__main__':
    unittest.main()
