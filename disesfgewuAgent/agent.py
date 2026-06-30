import asyncio
import json
import logging
import os
import re
from datetime import datetime
from typing import Optional

import tiktoken

from disesfgewuAgent.inputFileManager import inputFileManager
from disesfgewuAgent.llmRouter import llmRouter
from disesfgewuAgent.skillLoader import skillLoader

# Reasoning-heavy words (English + Chinese) that hint at a harder task. Matched
# as case-insensitive substrings against the RAW task only.
COMPLEX_KEYWORDS = (
    "analyze",
    "analyse",
    "prove",
    "design",
    "architect",
    "refactor",
    "debug",
    "optimize",
    "optimise",
    "derive",
    "evaluate",
    "compare",
    "implement",
    "algorithm",
    "step by step",
    "trade-off",
    "tradeoff",
    "分析",
    "證明",
    "推導",
    "設計",
    "架構",
    "重構",
    "除錯",
    "優化",
    "最佳化",
    "推理",
    "逐步",
    "比較",
    "評估",
    "演算法",
    "實作",
    "為什麼",
)


class AgentClient:
    def __init__(
        self,
        skillConfigPath: str,
        skillFolderPath: str,
        apiConfig,
        contextWindowSize: int = 32000,
        historyDir: Optional[str] = None,
        routingStrategy: str = "taskComplex",
        complexityScoreThreshold: int = 3,
    ):
        # apiConfig: list of model dicts or path to a JSON file (injected, so the
        # package never reaches into its own install dir for user config).
        # historyDir: where to persist session logs; None disables disk writes.
        # routingStrategy: how the router picks a model — "taskComplex" tiers by
        # difficulty (default), "maxTokens" prefers the biggest window, "" keeps
        # the config order.
        self._router = llmRouter(apiConfig, routingStrategy)
        self._skillLoader = skillLoader(skillConfigPath, skillFolderPath)

        self._contextWindowSize = contextWindowSize
        self._historyDir = historyDir
        # Budget against the largest available window so we only split when no
        # model can fit the prompt. Per-call routing then skips models that are
        # too small for the actual input size (see llmRouter.connect).
        self._maxInputToken = self._router.getMaxInputToken()
        self._outputReserveToken = 2048

        self._maxIterations = 10
        self._encoder = tiktoken.get_encoding("cl100k_base")
        self._logger = logging.getLogger(__name__)

        # Score (from _assessComplexity) at/above which a task counts as
        # complex. Higher = stay on cheap models for more tasks.
        self._complexityScoreThreshold = complexityScoreThreshold

        self._resetState()

    def _resetState(self) -> None:
        # Per-conversation accumulators; cleared at the start of every ask() so
        # the same client can be reused for independent, unrelated tasks.
        self._contextWindowsToken = 0
        self._inputStrCache = ""
        self._inputFiles = []
        self._inputFilesCache = ""
        self._inputFilesToken = 0
        self._skillCache = ""
        self._skillCacheToken = 0
        self._inputStr = ""
        self._history = []
        self._matchedSkillCount = 0
        self._taskIsComplex = False

    def _countTokens(self, text: str) -> int:
        return len(self._encoder.encode(text))

    def _getInputTokenSize(self) -> int:
        return (
            self._contextWindowsToken
            + self._skillCacheToken
            + self._inputFilesToken
            + self._countTokens(self._inputStr)
        )

    async def _getSkills(self):
        composed, results = await self._skillLoader.searchAndComposeAsync(
            self._inputStr
        )
        self._matchedSkillCount = len(results)
        if composed:
            self._skillCache = f"[SKILLS]\n{composed}"
        else:
            self._skillCache = ""
        self._skillCacheToken = self._countTokens(self._skillCache)

    def _assessComplexity(self) -> bool:
        # Composite, zero-cost difficulty heuristic. Scored on the RAW task
        # (self._inputStr) plus structural signals, NOT the assembled prompt —
        # the injected skill text is full of reasoning words and would skew
        # keyword matching toward "complex" for every task.
        #
        # Deliberately conservative: even the cheapest models are capable, so we
        # stay on them by default and escalate only on strong evidence. Reasoning
        # keywords are the primary signal; length / file count / skill count are
        # weak nudges that do not escalate on their own.
        task = self._inputStr
        score = 0

        lowered = task.lower()
        keyword_hits = sum(1 for kw in COMPLEX_KEYWORDS if kw in lowered)
        score += min(keyword_hits, 3)

        if self._countTokens(task) > 5000:
            score += 1
        if len(self._inputFiles) >= 3:
            score += 1
        if self._matchedSkillCount >= 3:
            score += 1

        return score >= self._complexityScoreThreshold

    async def _connect(self, inputFull: str) -> str:
        inputToken = self._countTokens(inputFull)
        return await self._router.connect(
            inputFull, inputToken=inputToken, isComplex=self._taskIsComplex
        )

    def _buildPrompt(self, informations: str = "") -> str:
        sections = []

        sections.append(
            "You are a task-oriented agent. You MUST respond with valid JSON only.\n"
            "Response format:\n"
            '{"status": "done", "answer": "final answer", "reasoning": "..."}\n'
            '{"status": "continue", "answer": "current progress", '
            '"reasoning": "...", "next_action": "..."}'
        )

        if self._skillCache:
            sections.append(self._skillCache)

        if self._inputStrCache:
            sections.append(f"[CONTEXT MEMORY]\n{self._inputStrCache}")

        if informations:
            sections.append(f"[INFORMATIONS FROM LAST]\n{informations}")

        if self._inputFilesCache:
            sections.append(self._inputFilesCache)

        sections.append(f"[TASK]\n{self._inputStr}")

        return "\n\n".join(sections)

    async def _getInputs(self, inputStr: str, inputFiles: Optional[list] = None):
        inputFiles = inputFiles or []
        self._inputStr = inputStr
        self._inputFiles = inputFiles

        await self._skillLoader.loadAsync()

        if inputFiles:
            self._inputFilesCache, self._inputFilesToken = (
                await inputFileManager.decompose(inputFiles, self._countTokens)
            )

        await self._getSkills()

        self._taskIsComplex = self._assessComplexity()
        self._logger.info(
            f"Task assessed as {'complex' if self._taskIsComplex else 'simple'}"
        )

    def _splitTaskInputAlgorithm(self, text: str, chunk_token_budget: int) -> list:
        tokens = self._encoder.encode(text)
        if len(tokens) <= chunk_token_budget:
            return [text]

        overlap = int(chunk_token_budget * 0.1)
        chunks = []
        start = 0
        while start < len(tokens):
            end = min(start + chunk_token_budget, len(tokens))
            chunks.append(self._encoder.decode(tokens[start:end]))
            if end >= len(tokens):
                break
            start = end - overlap

        return chunks

    async def _splitAndProcess(self, prompt: str, available: int) -> str:
        # The task section is always appended last by _buildPrompt, so split on
        # the final marker. Splitting on the first one would mis-fire if any
        # skill/file/context body happens to contain "[TASK]\n".
        parts = prompt.rsplit("[TASK]\n", 1)
        fixed_section = parts[0]
        task_input = parts[1] if len(parts) > 1 else ""

        fixed_tokens = self._countTokens(fixed_section)
        chunk_budget = available - fixed_tokens
        if chunk_budget <= 0:
            return await self._connect(prompt)

        chunks = self._splitTaskInputAlgorithm(task_input, chunk_budget)
        if len(chunks) <= 1:
            return await self._connect(prompt)

        self._logger.info(f"Splitting into {len(chunks)} chunks")

        tasks = [
            self._connect(f"{fixed_section}[TASK - Part {i+1}/{len(chunks)}]\n{chunk}")
            for i, chunk in enumerate(chunks)
        ]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        valid = []
        errors = []
        for i, r in enumerate(responses):
            if isinstance(r, str):
                valid.append((i, r))
            else:
                errors.append(f"Part {i+1}: {r}")

        if errors:
            self._logger.warning(
                f"{len(errors)}/{len(responses)} chunks failed: " + "; ".join(errors)
            )

        if not valid:
            raise Exception(
                "All chunks failed during split processing:\n" + "\n".join(errors)
            )

        merged = "\n\n---\n\n".join(f"[Part {i+1} Response]\n{r}" for i, r in valid)

        merge_prompt = (
            f"{fixed_section}\n"
            f"[PARTIAL RESPONSES]\n{merged}\n\n"
            f"[TASK]\nMerge the above partial responses into a complete answer. "
            f"Respond in JSON format."
        )
        return await self._connect(merge_prompt)

    async def _action(self, informations: str = "") -> str:
        prompt = self._buildPrompt(informations)
        prompt_tokens = self._countTokens(prompt)
        available = self._maxInputToken - self._outputReserveToken

        self._logger.debug(f"Prompt tokens: {prompt_tokens}, available: {available}")

        if self._contextWindowsToken > self._contextWindowSize:
            self._logger.info("Context memory exceeds window size, compressing")
            await self._compress()
            prompt = self._buildPrompt(informations)
            prompt_tokens = self._countTokens(prompt)

        if prompt_tokens <= available:
            return await self._connect(prompt)

        self._logger.info(
            f"Prompt too large ({prompt_tokens} > {available}), splitting"
        )
        return await self._splitAndProcess(prompt, available)

    def _parseSignal(self, response: str) -> dict:
        candidates = [response]

        fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response, re.DOTALL)
        if fenced:
            candidates.append(fenced.group(1))

        brace = re.search(r"\{.*\}", response, re.DOTALL)
        if brace:
            candidates.append(brace.group(0))

        for candidate in candidates:
            try:
                signal = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            if isinstance(signal, dict):
                return signal

        self._logger.warning("Response is not valid JSON, treating as done")
        return {"status": "done", "answer": response}

    async def _actionLoop(self) -> str:
        informations = ""

        for iteration in range(1, self._maxIterations + 1):
            self._logger.info(f"Iteration {iteration}/{self._maxIterations}")

            response = await self._action(informations)
            self._history.append({"iteration": iteration, "response": response})

            signal = self._parseSignal(response)
            status = signal.get("status", "done")

            if status == "done":
                self._logger.info("Task completed")
                await self._backupHistory()
                return signal.get("answer", response)

            self._logger.info(f"Continuing: {signal.get('reasoning', '')}")
            # Store the parsed answer, not the raw response, so context memory
            # does not fill up with JSON envelopes / reasoning scaffolding.
            # Default to "" (not the raw response) when no answer is present.
            answer = signal.get("answer", "")
            self._inputStrCache += f"\n\n[Iteration {iteration}]\n{answer}"
            self._contextWindowsToken = self._countTokens(self._inputStrCache)

            informations = (
                f"LAST: {signal.get('answer', '')}\n"
                f"REASONING: {signal.get('reasoning', '')}\n"
                f"NEXT: {signal.get('next_action', '')}"
            )

        self._logger.warning("Max iterations reached")
        await self._backupHistory()
        return "Max iterations reached."

    async def _compress(self):
        if not self._inputStrCache:
            return

        self._logger.info("Compressing context memory")
        original_tokens = self._countTokens(self._inputStrCache)
        summary = await self._summarize(self._inputStrCache)
        summary_tokens = self._countTokens(summary)

        if summary_tokens >= original_tokens:
            self._logger.info(
                f"Compression did not reduce size "
                f"({summary_tokens} >= {original_tokens}), keeping original"
            )
            return

        self._inputStrCache = summary
        self._contextWindowsToken = summary_tokens
        self._logger.info(f"Compressed to {summary_tokens} tokens")

    async def _summarize(self, text: str, depth: int = 0) -> str:
        prefix = (
            "Summarize the following context concisely, "
            "keeping only essential information:\n\n"
        )
        available = self._maxInputToken - self._outputReserveToken

        if self._countTokens(prefix + text) <= available:
            return await self._connect(prefix + text)

        if depth >= 3:
            self._logger.warning("Context too large to summarize, truncating")
            budget = max(1, available - self._countTokens(prefix))
            return self._truncateToTokens(text, budget)

        # Summarize oversized context chunk-by-chunk, then recurse on the
        # joined summaries until the whole thing fits a single request.
        chunk_budget = max(1, available - self._countTokens(prefix))
        chunks = self._splitTaskInputAlgorithm(text, chunk_budget)
        self._logger.info(f"Summarizing oversized context in {len(chunks)} chunks")
        summaries = [await self._connect(prefix + chunk) for chunk in chunks]
        return await self._summarize("\n\n".join(summaries), depth + 1)

    def _truncateToTokens(self, text: str, max_tokens: int) -> str:
        tokens = self._encoder.encode(text)
        if len(tokens) <= max_tokens:
            return text
        return self._encoder.decode(tokens[:max_tokens])

    async def _backupHistory(self):
        if not self._historyDir:
            return
        os.makedirs(self._historyDir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(self._historyDir, f"session_{timestamp}.json")

        def _write():
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(self._history, f, indent=2, ensure_ascii=False)

        await asyncio.to_thread(_write)
        self._logger.info(f"History saved to {filepath}")

    async def ask(self, inputStr: str, inputFiles: Optional[list] = None) -> str:
        # Reset per-conversation state so the client can be reused across
        # independent tasks. The router is left open; lifecycle is owned by the
        # caller via aclose() or the async context manager.
        self._resetState()
        await self._getInputs(inputStr, inputFiles)
        return await self._actionLoop()

    async def aclose(self) -> None:
        await self._router.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.aclose()
