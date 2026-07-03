"""End-to-end integration tests against the REAL LLM / embedding endpoints.

These tests are intentionally NOT mocked. They exercise the whole pipeline
(skill retrieval -> prompt build -> token-aware routing -> iteration loop ->
answer extraction) using ``config/api.local.json`` and the ``EMBEDDING_API``
from ``.env``.

They are skipped automatically when the project is not configured, so a fresh
clone of the template still produces a green run. To run only this suite:

    python -m unittest tests.test_integration -v

Note: these consume real API quota and depend on the configured endpoints being
reachable and within rate limits.
"""

import os
import sys
import shutil
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.live_api import live_api_available, SKIP_REASON, ROOT
from disesfgewuAgent.agent import AgentClient
from disesfgewuAgent.llmRouter import llmRouter

API_CONFIG = os.path.join(ROOT, "config", "api.local.json")
SKILLS_CONFIG = os.path.join(ROOT, "config", "skills.json")
SKILLS_DIR = os.path.join(ROOT, "skills")


def _model_with_protocol(router: llmRouter, protocol: str):
    for name, api in router._api["models"].items():
        if api.get("protocol") == protocol:
            return name
    return None


@unittest.skipUnless(live_api_available(), SKIP_REASON)
class TestAgentEndToEnd(unittest.IsolatedAsyncioTestCase):
    """Drives the full AgentClient against live models."""

    def _agent(self, context_window: int = 32000) -> AgentClient:
        return AgentClient(
            SKILLS_CONFIG,
            SKILLS_DIR,
            API_CONFIG,
            contextWindowSize=context_window,
            historyDir=os.path.join(ROOT, "history"),
        )

    async def test_simple_answer_is_correct(self):
        async with self._agent() as agent:
            result = await agent.ask(
                "What is the capital of Japan? Reply with one word."
            )
        self.assertEqual(result["status"], "done")
        self.assertIn("tokyo", result["answer"].lower())
        print(f"\n[e2e simple] {result['answer'][:120]}")

    async def test_arithmetic_answer(self):
        async with self._agent() as agent:
            result = await agent.ask("What is 21 + 21? Reply with just the number.")
        self.assertIn("42", result["answer"])
        print(f"\n[e2e arithmetic] {result['answer'][:120]}")

    async def test_reuse_same_client_for_independent_tasks(self):
        async with self._agent() as agent:
            first = await agent.ask("Reply with exactly the word: alpha")
            history_after_first = list(agent._history)

            second = await agent.ask("What is 10 minus 4? Reply with just the number.")

        self.assertGreater(len(first["answer"]), 0)
        self.assertIn("6", second["answer"])
        # State was reset before the second task: history reflects the second
        # run only, not the accumulation of both.
        self.assertGreater(len(history_after_first), 0)
        self.assertLessEqual(len(agent._history), agent._maxIterations)
        print(f"\n[e2e reuse] first={first['answer'][:40]!r} "
              f"second={second['answer'][:40]!r}")

    async def test_answer_uses_file_content(self):
        work_dir = tempfile.mkdtemp()
        try:
            file_path = os.path.join(work_dir, "secret.txt")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("The launch code is BLUE-42. Keep it confidential.")

            async with self._agent() as agent:
                result = await agent.ask(
                    "What is the launch code mentioned in the file?",
                    inputFiles=[file_path],
                )
            self.assertIn("42", result["answer"])
            print(f"\n[e2e file] {result['answer'][:120]}")
        finally:
            shutil.rmtree(work_dir)

    async def test_skill_retrieval_populates_cache(self):
        async with self._agent() as agent:
            await agent._getInputs("How should I conduct a thorough code review?")
            self.assertTrue(agent._skillCache.startswith("[SKILLS]"))
            self.assertGreater(agent._skillCacheToken, 0)
            print(f"\n[e2e skills] {agent._skillCacheToken} skill tokens injected")

    async def test_writes_runs_and_explains_code(self):
        agent = AgentClient(
            SKILLS_CONFIG,
            SKILLS_DIR,
            API_CONFIG,
            historyDir=os.path.join(ROOT, "history"),
            enableCodeExecution=True,
        )
        async with agent:
            result = await agent.ask(
                'Write and RUN Python to compute the sum of integers from 1 to '
                '100. Use status "execute" to actually run it, then report the '
                "numeric result."
            )
        self.assertIn("5050", result["answer"])
        self.assertGreater(len(result["commands"]), 0)  # it actually ran code
        print(f"\n[e2e code-exec] {result['answer'][:160]}")

    async def test_agent_uses_shell(self):
        agent = AgentClient(
            SKILLS_CONFIG,
            SKILLS_DIR,
            API_CONFIG,
            historyDir=os.path.join(ROOT, "history"),
            enableShell=True,
        )
        async with agent:
            result = await agent.ask(
                'Use the shell (execute with language "shell") to run exactly: '
                "echo ROUTER_MARKER_42 -- then report what it printed."
            )
        self.assertIn("ROUTER_MARKER_42", result["answer"])
        print(f"\n[e2e shell] {result['answer'][:120]}")

    async def test_agent_edits_a_file(self):
        work_dir = tempfile.mkdtemp()
        try:
            path = os.path.join(work_dir, "mod.py")
            with open(path, "w", encoding="utf-8") as f:
                f.write("def add(a, b):\n    return a + b\n")

            agent = AgentClient(
                SKILLS_CONFIG,
                SKILLS_DIR,
                API_CONFIG,
                historyDir=os.path.join(ROOT, "history"),
                enableCodeExecution=True,
            )
            async with agent:
                result = await agent.ask(
                    f"Edit the file at {path}: add a function subtract(a, b) that "
                    "returns a - b, keeping the existing add(). Actually apply the "
                    "change to the file on disk, then confirm."
                )

            with open(path, encoding="utf-8") as f:
                content = f.read()
            self.assertIn("subtract", content)
            self.assertIn("a - b", content)
            self.assertIn("def add", content)  # existing code preserved
            print(f"\n[e2e edit] {result['answer'][:120]}")
        finally:
            shutil.rmtree(work_dir)

    async def test_edit_file_action_returns_diff(self):
        work_dir = tempfile.mkdtemp()
        try:
            path = os.path.join(work_dir, "conf.py").replace("\\", "/")
            with open(path, "w", encoding="utf-8") as f:
                f.write("VERSION = 1\n")

            agent = AgentClient(
                SKILLS_CONFIG,
                SKILLS_DIR,
                API_CONFIG,
                historyDir=os.path.join(ROOT, "history"),
                mode="coding",
                enableFileEdit=True,
            )
            async with agent:
                result = await agent.ask(
                    f'Edit the file "{path}". Emit exactly one edit_file action '
                    f'that replaces the snippet "VERSION = 1" with "VERSION = 2", '
                    f"then finish with done."
                )

            with open(path, encoding="utf-8") as f:
                content = f.read()
            self.assertIn("VERSION = 2", content)
            # the fixed-schema result carries the change + a diff
            self.assertTrue(result["diffs"])
            self.assertIn("VERSION = 2", result["diffs"][0]["diff"])
            print(f"\n[e2e edit_file diff]\n{result['diffs'][0]['diff']}")
        finally:
            shutil.rmtree(work_dir)

    async def test_context_manager_closes_router(self):
        agent = self._agent()
        async with agent:
            await agent.ask("Reply with exactly: ok")
        client = agent._router._asyncClient
        self.assertTrue(client is None or client.is_closed)


@unittest.skipUnless(live_api_available(), SKIP_REASON)
class TestRouterEndToEnd(unittest.IsolatedAsyncioTestCase):
    """Drives the multi-protocol router directly against live models."""

    async def asyncSetUp(self):
        self.router = llmRouter(API_CONFIG)

    async def asyncTearDown(self):
        await self.router.close()

    async def test_openai_protocol_model(self):
        name = _model_with_protocol(self.router, "openai")
        if not name:
            self.skipTest("no openai-protocol model configured")
        result = await self.router.connect("Reply with exactly: ok", modelName=name)
        self.assertIsInstance(result, str)
        self.assertGreater(len(result.strip()), 0)
        print(f"\n[e2e openai:{name}] {result[:80]}")

    async def test_anthropic_protocol_model(self):
        name = _model_with_protocol(self.router, "anthropic")
        if not name:
            self.skipTest("no anthropic-protocol model configured")
        result = await self.router.connect("Reply with exactly: ok", modelName=name)
        self.assertIsInstance(result, str)
        self.assertGreater(len(result.strip()), 0)
        print(f"\n[e2e anthropic:{name}] {result[:80]}")

    async def test_default_priority_failover(self):
        # No modelName -> walks the priority list; succeeds on the first model
        # that is reachable and within rate limits.
        result = await self.router.connect("Reply with exactly: ok")
        self.assertIsInstance(result, str)
        self.assertGreater(len(result.strip()), 0)

    async def test_parallel_calls_share_one_client(self):
        import asyncio

        names = list(self.router._api["models"].keys())[:2]
        if len(names) < 2:
            self.skipTest("need at least two models for the parallel test")
        results = await asyncio.gather(
            self.router.connect("Reply 'one'.", modelName=names[0]),
            self.router.connect("Reply 'two'.", modelName=names[1]),
        )
        self.assertEqual(len(results), 2)
        for r in results:
            self.assertIsInstance(r, str)
            self.assertGreater(len(r.strip()), 0)


if __name__ == "__main__":
    unittest.main()
