import unittest
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from disesfgewuAgent.llmRouter import llmRouter
from tests.live_api import live_api_available, SKIP_REASON

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API_CONFIG_PATH = os.path.join(ROOT, "config", "api.local.json")


class TestLLMRouterLogic(unittest.TestCase):
    def setUp(self):
        self.sample_config = [
            {
                "provider": "openai",
                "endpointUrl": "https://api.openai.com",
                "modelName": "gpt-4",
                "maxInputToken": 8192,
                "maxOutputToken": 4096,
                "apiKey": "test-key-1",
            },
            {
                "provider": "openai",
                "endpointUrl": "https://api.openai.com",
                "modelName": "gpt-3.5-turbo",
                "maxInputToken": 16385,
                "maxOutputToken": 4096,
                "apiKey": "test-key-2",
            },
        ]

    def test_decompose_creates_models_dict(self):
        router = object.__new__(llmRouter)
        result = router.decompose(self.sample_config)

        self.assertIn("models", result)
        self.assertEqual(len(result["models"]), 2)
        self.assertIn("gpt-4", result["models"])
        self.assertIn("gpt-3.5-turbo", result["models"])

    def test_decompose_stores_protocol(self):
        router = object.__new__(llmRouter)
        config = [
            {
                "provider": "google",
                "protocol": "google",
                "endpointUrl": "https://generativelanguage.googleapis.com",
                "modelName": "gemini-2.5-pro",
                "maxInputToken": 1048576,
                "maxOutputToken": 65536,
                "apiKey": "test-key",
            }
        ]
        result = router.decompose(config)

        self.assertEqual(result["models"]["gemini-2.5-pro"]["protocol"], "google")

    def test_decompose_defaults_protocol_to_openai(self):
        router = object.__new__(llmRouter)
        config = [
            {
                "provider": "custom",
                "endpointUrl": "https://custom.api.com",
                "modelName": "custom-model",
                "maxInputToken": 4096,
                "maxOutputToken": 2048,
                "apiKey": "test-key",
            }
        ]
        result = router.decompose(config)

        self.assertEqual(result["models"]["custom-model"]["protocol"], "openai")

    def test_getApi_returns_correct_model(self):
        router = object.__new__(llmRouter)
        router._api = router.decompose(self.sample_config)

        api = router.getApi("gpt-4")
        self.assertIsNotNone(api)
        self.assertEqual(api["modelName"], "gpt-4")
        self.assertEqual(api["maxInputToken"], 8192)

    def test_getApi_returns_none_for_missing_model(self):
        router = object.__new__(llmRouter)
        router._api = router.decompose(self.sample_config)

        api = router.getApi("nonexistent-model")
        self.assertIsNone(api)

    def test_priorityAlgorithm_returns_default_order(self):
        router = object.__new__(llmRouter)
        models = {"gpt-4": {}, "gpt-3.5-turbo": {}}

        result = router.priorityAlgorithm(models)
        self.assertEqual(result, ["gpt-4", "gpt-3.5-turbo"])

    def test_priorityAlgorithmByMaxTokens_sorts_correctly(self):
        router = object.__new__(llmRouter)
        models = {
            "gpt-4": {"maxInputToken": 8192, "maxOutputToken": 4096},
            "gpt-3.5-turbo": {"maxInputToken": 16385, "maxOutputToken": 4096},
        }

        result = router.priorityAlgorithmByMaxTokens(models)
        self.assertEqual(result[0], "gpt-3.5-turbo")
        self.assertEqual(result[1], "gpt-4")

    def test_decompose_defaults_tier_to_2(self):
        router = object.__new__(llmRouter)
        result = router.decompose(
            [
                {
                    "provider": "x",
                    "endpointUrl": "http://x",
                    "modelName": "m",
                    "maxInputToken": 4096,
                    "maxOutputToken": 2048,
                }
            ]
        )
        self.assertEqual(result["models"]["m"]["tier"], 2)

    def test_decompose_stores_explicit_tier(self):
        router = object.__new__(llmRouter)
        result = router.decompose(
            [
                {
                    "provider": "x",
                    "endpointUrl": "http://x",
                    "modelName": "m",
                    "maxInputToken": 4096,
                    "maxOutputToken": 2048,
                    "tier": 5,
                }
            ]
        )
        self.assertEqual(result["models"]["m"]["tier"], 5)

    def test_taskComplex_simple_prefers_low_tier(self):
        router = object.__new__(llmRouter)
        router._complexity_threshold = 100
        models = {
            "cheap": {"maxInputToken": 8000, "tier": 1},
            "strong": {"maxInputToken": 200000, "tier": 3},
        }
        result = router.priorityAlgorithmByTaskComplex(models, "hi")
        self.assertEqual(result[0], "cheap")
        self.assertEqual(result[1], "strong")

    def test_taskComplex_complex_prefers_high_tier(self):
        router = object.__new__(llmRouter)
        router._complexity_threshold = 100
        models = {
            "cheap": {"maxInputToken": 8000, "tier": 1},
            "strong": {"maxInputToken": 200000, "tier": 3},
        }
        result = router.priorityAlgorithmByTaskComplex(models, "x" * 500)
        self.assertEqual(result[0], "strong")
        self.assertEqual(result[1], "cheap")

    def test_taskComplex_breaks_ties_by_window_size(self):
        router = object.__new__(llmRouter)
        router._complexity_threshold = 100
        models = {
            "small": {"maxInputToken": 8192},   # tier defaults to 2
            "big": {"maxInputToken": 200000},   # tier defaults to 2
        }
        # easy task -> smaller window first within the same tier
        self.assertEqual(
            router.priorityAlgorithmByTaskComplex(models, "hi")[0], "small"
        )
        # hard task -> bigger window first
        self.assertEqual(
            router.priorityAlgorithmByTaskComplex(models, "x" * 500)[0], "big"
        )

    def test_taskComplex_explicit_isComplex_overrides_length(self):
        router = object.__new__(llmRouter)
        router._complexity_threshold = 100
        models = {
            "cheap": {"maxInputToken": 8000, "tier": 1},
            "strong": {"maxInputToken": 200000, "tier": 3},
        }
        # short text but explicitly complex -> strong first
        self.assertEqual(
            router.priorityAlgorithmByTaskComplex(models, "hi", isComplex=True)[0],
            "strong",
        )
        # long text but explicitly simple -> cheap first
        self.assertEqual(
            router.priorityAlgorithmByTaskComplex(
                models, "x" * 500, isComplex=False
            )[0],
            "cheap",
        )

    def test_getMinInputToken(self):
        router = object.__new__(llmRouter)
        router._api = router.decompose(self.sample_config)

        result = router.getMinInputToken()
        self.assertEqual(result, 8192)

    def test_getMaxInputToken(self):
        router = object.__new__(llmRouter)
        router._api = router.decompose(self.sample_config)

        result = router.getMaxInputToken()
        self.assertEqual(result, 16385)


class TestLLMRouterTokenGuard(unittest.IsolatedAsyncioTestCase):
    """Deterministic, network-free checks of token-aware routing (Fix 1 / Fix 5)."""

    def _router(self, models: list) -> llmRouter:
        router = object.__new__(llmRouter)
        router._asyncClient = None
        router._api = router.decompose(models)
        router._priority_strategy = ""
        return router

    async def test_all_models_too_small_raises_with_reason(self):
        router = self._router(
            [
                {
                    "provider": "x",
                    "endpointUrl": "http://x",
                    "modelName": "tiny",
                    "maxInputToken": 10,
                    "maxOutputToken": 10,
                    "apiKey": "",
                }
            ]
        )
        with self.assertRaises(Exception) as ctx:
            await router.connect("irrelevant", inputToken=999)
        msg = str(ctx.exception)
        self.assertIn("tiny", msg)
        self.assertIn("exceeds maxInputToken", msg)
        await router.close()

    async def test_skip_message_lists_every_model(self):
        router = self._router(
            [
                {
                    "provider": "x",
                    "endpointUrl": "http://x",
                    "modelName": "m1",
                    "maxInputToken": 100,
                    "maxOutputToken": 10,
                    "apiKey": "",
                },
                {
                    "provider": "x",
                    "endpointUrl": "http://x",
                    "modelName": "m2",
                    "maxInputToken": 200,
                    "maxOutputToken": 10,
                    "apiKey": "",
                },
            ]
        )
        with self.assertRaises(Exception) as ctx:
            await router.connect("irrelevant", inputToken=10_000)
        msg = str(ctx.exception)
        self.assertIn("m1", msg)
        self.assertIn("m2", msg)
        await router.close()

    async def test_skips_too_small_and_picks_fitting_model(self):
        router = self._router(
            [
                {
                    "provider": "x",
                    "endpointUrl": "http://x",
                    "modelName": "small",
                    "maxInputToken": 1000,
                    "maxOutputToken": 100,
                    "tier": 1,
                },
                {
                    "provider": "x",
                    "endpointUrl": "http://x",
                    "modelName": "big",
                    "maxInputToken": 500000,
                    "maxOutputToken": 100,
                    "tier": 1,
                },
            ]
        )
        called = []

        async def fake_call(api, inputStr, jsonMode=False):
            called.append(api["modelName"])
            return "ok"

        router._callLLM = fake_call
        # input exceeds the 'small' window but fits 'big'
        result = await router.connect("hello", inputToken=2000)
        self.assertEqual(result, "ok")
        self.assertEqual(called, ["big"])  # 'small' was filtered out by the fit guard
        await router.close()

    async def test_connect_forwards_jsonMode(self):
        router = self._router(
            [
                {
                    "provider": "x",
                    "endpointUrl": "http://x",
                    "modelName": "m",
                    "maxInputToken": 100000,
                    "maxOutputToken": 100,
                    "tier": 1,
                }
            ]
        )
        captured = {}

        async def fake_call(api, inputStr, jsonMode=False):
            captured["jsonMode"] = jsonMode
            return "ok"

        router._callLLM = fake_call
        await router.connect("hi", jsonMode=True)
        self.assertTrue(captured["jsonMode"])
        await router.close()


@unittest.skipUnless(live_api_available(), SKIP_REASON)
class TestLLMRouterAsyncLifecycle(unittest.IsolatedAsyncioTestCase):
    def _makeRouter(self) -> llmRouter:
        router = object.__new__(llmRouter)
        router._asyncClient = None
        shared = llmRouter(API_CONFIG_PATH)
        router._api = shared._api
        router._priority_strategy = shared._priority_strategy
        return router

    async def test_getClient_lazy_creates(self):
        router = self._makeRouter()

        client = await router._getClient()
        self.assertIsNotNone(client)
        self.assertFalse(client.is_closed)

        client2 = await router._getClient()
        self.assertIs(client, client2)

        await router.close()

    async def test_getClient_reuses_client(self):
        router = self._makeRouter()

        client1 = await router._getClient()
        client2 = await router._getClient()
        self.assertIs(client1, client2)

        await router.close()

    async def test_getClient_recreates_after_close(self):
        router = self._makeRouter()

        client1 = await router._getClient()
        await router.close()
        self.assertTrue(client1.is_closed)

        client2 = await router._getClient()
        self.assertIsNot(client1, client2)
        self.assertFalse(client2.is_closed)

        await router.close()

    async def test_close_closes_client(self):
        router = self._makeRouter()

        await router._getClient()
        self.assertFalse(router._asyncClient.is_closed)

        await router.close()
        self.assertTrue(router._asyncClient.is_closed)

    async def test_close_noop_when_no_client(self):
        router = self._makeRouter()
        await router.close()

    async def test_async_context_manager(self):
        router = self._makeRouter()

        async with router as r:
            self.assertIs(r, router)
            await r._getClient()
            self.assertFalse(r._asyncClient.is_closed)

        self.assertTrue(router._asyncClient.is_closed)


@unittest.skipUnless(live_api_available(), SKIP_REASON)
class TestLLMRouterAsyncAPI(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.router = llmRouter(API_CONFIG_PATH)

    async def asyncTearDown(self):
        await self.router.close()

    async def test_callOpenAI(self):
        api = self.router.getApi("deepseek-v4-flash")
        self.assertIsNotNone(api, "deepseek-v4-flash not found in config")
        self.assertEqual(api["protocol"], "openai")

        result = await self.router._callOpenAI(api, "Reply with just the word 'ok'.")
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)
        print(f"\n[_callOpenAI - deepseek-v4-flash] {result[:100]}")

    async def test_callAnthropic(self):
        api = self.router.getApi("qwen3.7-plus")
        self.assertIsNotNone(api, "qwen3.7-plus not found in config")
        self.assertEqual(api["protocol"], "anthropic")

        result = await self.router._callAnthropic(api, "Reply with just the word 'ok'.")
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)
        print(f"\n[_callAnthropic - qwen3.7-plus] {result[:100]}")

    async def test_callLLM_dispatch_openai(self):
        api = self.router.getApi("deepseek-v4-flash")
        result = await self.router._callLLM(api, "Reply with just the word 'ok'.")
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)

    async def test_callLLM_dispatch_anthropic(self):
        api = self.router.getApi("qwen3.7-plus")
        result = await self.router._callLLM(api, "Reply with just the word 'ok'.")
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)

    async def test_connect_openai_model(self):
        result = await self.router.connect(
            "What is 2+2? Reply with just the number.",
            modelName="deepseek-v4-flash",
        )
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)
        print(f"\n[connect - deepseek-v4-flash] {result[:100]}")

    async def test_connect_anthropic_model(self):
        result = await self.router.connect(
            "What is 3+3? Reply with just the number.",
            modelName="qwen3.7-plus",
        )
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)
        print(f"\n[connect - qwen3.7-plus] {result[:100]}")

    async def test_connect_default_priority(self):
        result = await self.router.connect("Reply with just the word 'ok'.")
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)
        print(f"\n[connect - default priority] {result[:100]}")

    async def test_connect_with_priority_maxTokens(self):
        result = await self.router.connect(
            "Reply with just the word 'ok'.",
            priority="maxTokens",
        )
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)

    async def test_connect_with_priority_taskComplex(self):
        result = await self.router.connect(
            "Reply with just the word 'ok'.",
            priority="taskComplex",
        )
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)

    async def test_connect_raises_on_invalid_model(self):
        with self.assertRaises(ValueError) as context:
            await self.router.connect("Test", modelName="nonexistent-model")
        self.assertIn("nonexistent-model", str(context.exception))

    async def test_connect_parallel_different_models(self):
        results = await asyncio.gather(
            self.router.connect("Reply 'one'.", modelName="deepseek-v4-flash"),
            self.router.connect("Reply 'two'.", modelName="qwen3.7-plus"),
            self.router.connect("Reply 'three'.", modelName="deepseek-v4-pro"),
        )

        self.assertEqual(len(results), 3)
        for i, result in enumerate(results):
            self.assertIsInstance(result, str)
            self.assertTrue(len(result) > 0)
            print(f"\n[parallel #{i+1}] {result[:100]}")

    async def test_connect_parallel_same_model(self):
        prompts = [
            "Reply 'alpha'.",
            "Reply 'beta'.",
            "Reply 'gamma'.",
        ]
        results = await asyncio.gather(
            *[self.router.connect(p, modelName="deepseek-v4-flash") for p in prompts]
        )

        self.assertEqual(len(results), 3)
        for i, result in enumerate(results):
            self.assertIsInstance(result, str)
            self.assertTrue(len(result) > 0)
            print(f"\n[parallel-same #{i+1}] {result[:100]}")


if __name__ == "__main__":
    unittest.main()
