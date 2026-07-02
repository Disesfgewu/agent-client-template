import asyncio
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
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
    "review",
    "redesign",
    "audit",
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
    "審查",
    "檢視",
    "重設計",
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
        maxTurnsInContext: int = 6,
        enableCodeExecution: bool = False,
        enableShell: bool = False,
        codeExecutionTimeout: int = 30,
        onEvent=None,
        onApprove=None,
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

        # Rolling multi-turn conversation (see chat()). Persists across ask()
        # calls; only cleared by resetConversation().
        self._maxTurnsInContext = maxTurnsInContext
        self._conversation = []

        # Opt-in execution. The system provides the environment (run Python /
        # run shell commands); skills teach WHICH commands to use (grep, find,
        # ...). Both off by default: only enable for trusted, local use.
        self._enableCodeExecution = enableCodeExecution
        self._enableShell = enableShell
        self._codeExecutionTimeout = codeExecutionTimeout

        # Optional observer of the agent loop, so a UI can surface each step
        # (planning, running code, observing output). Makes the agentic loop
        # visible instead of hiding it behind a single final answer.
        self._onEvent = onEvent

        # Optional approval gate: called with the action about to run; return a
        # falsy value to block it. The embedding app owns the policy (interactive
        # prompt, allow-list, auto-approve) — this is what makes execution safe
        # to embed. None = auto-approve (suitable for trusted / non-interactive).
        self._onApprove = onApprove

        self._resetState()

    def _emit(self, event: dict) -> None:
        if self._onEvent is None:
            return
        try:
            self._onEvent(event)
        except Exception:
            self._logger.debug("onEvent handler raised", exc_info=True)

    def _approve(self, action: dict) -> bool:
        if self._onApprove is None:
            return True
        try:
            return bool(self._onApprove(action))
        except Exception:
            self._logger.debug("onApprove handler raised; denying", exc_info=True)
            return False

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
        # Large attached material (reviewing/redesigning a big file or project)
        # is a strong signal — route it to a stronger model, not the cheapest.
        if self._inputFilesToken > 8000:
            score += 2
        elif self._inputFilesToken > 2000:
            score += 1
        if len(self._inputFiles) >= 3:
            score += 1
        if self._matchedSkillCount >= 3:
            score += 1

        return score >= self._complexityScoreThreshold

    async def _connect(self, inputFull: str, jsonMode: bool = False) -> str:
        inputToken = self._countTokens(inputFull)
        return await self._router.connect(
            inputFull,
            inputToken=inputToken,
            isComplex=self._taskIsComplex,
            jsonMode=jsonMode,
        )

    def _buildPrompt(self, informations: str = "") -> str:
        sections = []

        instructions = (
            "You are an autonomous task-solving agent (not a chat bot). Think "
            "step by step and work toward completing the task.\n"
            "Respond with valid JSON only, one action per response:\n"
            '{"status": "continue", "answer": "progress so far", '
            '"reasoning": "your step-by-step thinking", "next_action": "next step"}\n'
            '{"status": "done", "answer": "final answer", "reasoning": "..."}\n'
            "For a COMPLEX task, decompose it: take several 'continue' steps, "
            "reasoning explicitly at each step, and only use 'done' once the whole "
            "task is finished. For a simple task, answer with 'done' directly."
        )
        if self._enableCodeExecution or self._enableShell:
            langs = []
            if self._enableCodeExecution:
                langs.append('"python" (run a script)')
            if self._enableShell:
                langs.append(
                    '"shell" (run a shell command: grep, find, ls, cat, sed, ...)'
                )
            instructions += (
                '\nTo actually run code or commands, use:\n'
                '{"status": "execute", "language": "<lang>", "code": "...", '
                '"reasoning": "..."}\n'
                "Available languages: " + "; ".join(langs) + ". "
                "Use this whenever the task needs real computation, searching or "
                "navigating the codebase, file inspection, or verification. Prefer "
                "POSIX/bash syntax for shell. The stdout/stderr is returned to "
                "you, then you continue reasoning or finish with 'done'."
            )
        sections.append(instructions)

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
        self._emit({"type": "assessed", "complex": self._taskIsComplex})

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
            return await self._connect(prompt, jsonMode=True)

        chunks = self._splitTaskInputAlgorithm(task_input, chunk_budget)
        if len(chunks) <= 1:
            return await self._connect(prompt, jsonMode=True)

        self._logger.info(f"Splitting into {len(chunks)} chunks")

        tasks = [
            self._connect(
                f"{fixed_section}[TASK - Part {i+1}/{len(chunks)}]\n{chunk}",
                jsonMode=True,
            )
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
        return await self._connect(merge_prompt, jsonMode=True)

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
            return await self._connect(prompt, jsonMode=True)

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
            self._emit(
                {"type": "iteration", "iteration": iteration, "max": self._maxIterations}
            )

            response = await self._action(informations)
            self._history.append({"iteration": iteration, "response": response})

            signal = self._parseSignal(response)
            status = signal.get("status", "done")

            if status == "execute" and (self._enableCodeExecution or self._enableShell):
                code = signal.get("code", "")
                language = signal.get("language", "python")
                self._logger.info(f"Executing {language} code ({len(code)} chars)")
                self._emit(
                    {
                        "type": "execute",
                        "language": language,
                        "code": code,
                        "reasoning": signal.get("reasoning", ""),
                    }
                )
                if not self._approve(
                    {"type": "execute", "language": language, "code": code}
                ):
                    self._logger.info("Execution denied by approval hook")
                    denied = "Execution denied by the user."
                    self._emit(
                        {
                            "type": "execution_result",
                            "stdout": "",
                            "stderr": denied,
                            "exit_code": -1,
                        }
                    )
                    self._history.append(
                        {"iteration": iteration, "execution_result": denied}
                    )
                    informations = (
                        denied
                        + ' The user declined to run that. Try another approach, '
                        'ask for what you need, or finish with "done".'
                    )
                    continue
                stdout, stderr, rc = await self._executeCode(code, language)
                self._logger.info(f"Execution finished with exit code {rc}")
                self._emit(
                    {
                        "type": "execution_result",
                        "stdout": stdout,
                        "stderr": stderr,
                        "exit_code": rc,
                    }
                )
                result_block = (
                    f"You executed this {language} code:\n{code}\n\n"
                    f"Result (exit code {rc}):\n"
                    f"STDOUT:\n{stdout or '(empty)'}\n"
                    f"STDERR:\n{stderr or '(empty)'}"
                )
                self._history.append(
                    {"iteration": iteration, "execution_result": result_block}
                )
                self._inputStrCache += (
                    f"\n\n[Iteration {iteration} execution]\n{result_block}"
                )
                self._contextWindowsToken = self._countTokens(self._inputStrCache)
                informations = (
                    result_block
                    + '\n\nNow respond with status "done": show the output and '
                    'explain it, or "execute" again if more steps are needed.'
                )
                continue

            if status == "done":
                self._logger.info("Task completed")
                await self._backupHistory()
                return signal.get("answer", response)

            self._logger.info(f"Continuing: {signal.get('reasoning', '')}")
            self._emit(
                {
                    "type": "step",
                    "reasoning": signal.get("reasoning", ""),
                    "answer": signal.get("answer", ""),
                    "next_action": signal.get("next_action", ""),
                }
            )
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

    def _runPythonSubprocess(self, code: str) -> tuple:
        fd, path = tempfile.mkstemp(suffix=".py")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(code)
            proc = subprocess.run(
                [sys.executable, path],
                capture_output=True,
                text=True,
                timeout=self._codeExecutionTimeout,
            )
            return proc.stdout, proc.stderr, proc.returncode
        except subprocess.TimeoutExpired:
            return "", f"Timed out after {self._codeExecutionTimeout}s", -1
        finally:
            try:
                os.remove(path)
            except OSError:
                pass

    def _runShell(self, command: str, lang: str = "shell") -> tuple:
        # Prefer bash for POSIX commands (grep/find/sed/...) so the same syntax
        # works cross-platform (Git Bash on Windows). Fall back to PowerShell or
        # the native shell.
        try:
            bash = shutil.which("bash")
            if lang in ("shell", "bash", "sh") and bash:
                proc = subprocess.run(
                    [bash, "-c", command],
                    capture_output=True,
                    text=True,
                    timeout=self._codeExecutionTimeout,
                )
            elif lang in ("powershell", "pwsh"):
                proc = subprocess.run(
                    ["powershell", "-NoProfile", "-Command", command],
                    capture_output=True,
                    text=True,
                    timeout=self._codeExecutionTimeout,
                )
            else:
                proc = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=self._codeExecutionTimeout,
                )
            return proc.stdout, proc.stderr, proc.returncode
        except subprocess.TimeoutExpired:
            return "", f"Timed out after {self._codeExecutionTimeout}s", -1
        except Exception as e:
            return "", f"Shell error: {e}", -1

    async def _executeCode(self, code: str, language: str = "python") -> tuple:
        # Returns (stdout, stderr, exit_code). Runs in a worker thread so the
        # event loop is not blocked. The system provides the environment; the
        # agent generates the actual Python / shell commands (taught by skills).
        lang = language.lower()
        if lang in ("python", "py"):
            if not self._enableCodeExecution:
                return "", "Python execution is disabled", -1
            return await asyncio.to_thread(self._runPythonSubprocess, code)
        if lang in ("shell", "bash", "sh", "powershell", "pwsh", "cmd"):
            if not self._enableShell:
                return "", "Shell execution is disabled", -1
            return await asyncio.to_thread(self._runShell, code, lang)
        return "", f"Unsupported language: {language}", -1

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
        # One-shot: reset per-conversation state so the client can be reused
        # across independent tasks. The router is left open; lifecycle is owned
        # by the caller via aclose() or the async context manager.
        self._resetState()
        await self._getInputs(inputStr, inputFiles)
        return await self._actionLoop()

    def _buildConversationInput(self, message: str) -> str:
        if not self._conversation:
            return message
        turns = self._conversation[-self._maxTurnsInContext * 2:]
        transcript = "\n".join(f"{role}: {text}" for role, text in turns)
        return f"Conversation so far:\n{transcript}\n\nUser: {message}"

    async def chat(self, message: str, inputFiles: Optional[list] = None) -> str:
        # Multi-turn: remembers prior turns so the caller only feeds the latest
        # message. Built on ask(), so difficulty routing / skills / files all
        # apply per turn.
        answer = await self.ask(self._buildConversationInput(message), inputFiles)
        self._conversation.append(("User", message))
        self._conversation.append(("Assistant", answer))
        return answer

    def resetConversation(self) -> None:
        self._conversation = []

    async def aclose(self) -> None:
        await self._router.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.aclose()
