import json
import os
from typing import Optional
import httpx


class llmRouter:
    def __init__(
        self, config, priority: str = "", complexityThreshold: int = 4000
    ) -> None:
        # Explicit config injection (no package-relative file lookups), so the
        # router works the same whether run from a checkout or pip-installed.
        # `config` is either a list of model dicts or a path to a JSON file.
        # complexityThreshold: prompt length (chars) above which the
        # "taskComplex" strategy treats a task as hard (see
        # priorityAlgorithmByTaskComplex).
        if config is None:
            raise ValueError(
                "llmRouter requires a model config: pass a list of model dicts "
                "or a path to a JSON file describing them."
            )
        if isinstance(config, (str, os.PathLike)):
            with open(config, "r", encoding="utf-8") as f:
                config = json.load(f)
        self._complexity_threshold = complexityThreshold
        self._api = self.decompose(config, priority)
        self._asyncClient: Optional[httpx.AsyncClient] = None

    async def _getClient(self) -> httpx.AsyncClient:
        if self._asyncClient is None or self._asyncClient.is_closed:
            self._asyncClient = httpx.AsyncClient(timeout=60.0)
        return self._asyncClient

    async def close(self) -> None:
        if self._asyncClient and not self._asyncClient.is_closed:
            await self._asyncClient.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()

    def getApi(self, modelName: str) -> Optional[dict]:
        if modelName in self._api["models"]:
            return self._api["models"][modelName]
        return None

    def getMinInputToken(self) -> int:
        return min(api["maxInputToken"] for api in self._api["models"].values())

    def getMaxInputToken(self) -> int:
        return max(api["maxInputToken"] for api in self._api["models"].values())

    async def connect(
        self,
        inputStr: str,
        modelName: str = None,
        priority: str = "",
        inputToken=0,
        isComplex=None,
    ):
        if modelName:
            if not self.getApi(modelName):
                raise ValueError(f"Model '{modelName}' not found in config")
            priority_list = [modelName]
        else:
            priority_list = self._getPriorityList(inputStr, priority, isComplex)

        errors = []
        for model_name in priority_list:
            api = self.getApi(model_name)
            if not api:
                continue
            try:
                if inputToken > int(api["maxInputToken"]):
                    errors.append(
                        f"{model_name}: skipped, input {inputToken} tokens "
                        f"exceeds maxInputToken {api['maxInputToken']}"
                    )
                    continue
                answer = await self._callLLM(api, inputStr)
                return answer
            except Exception as e:
                errors.append(f"{model_name}: {str(e)}")
                continue

        error_msg = "All LLM endpoints failed:\n" + "\n".join(errors)
        raise Exception(error_msg)

    def _getPriorityList(
        self, inputStr: str, priority: str = "", isComplex=None
    ) -> list:
        strategy = priority or self._priority_strategy
        models = self._api["models"]
        if strategy == "maxTokens":
            return self.priorityAlgorithmByMaxTokens(models)
        elif strategy == "taskComplex":
            return self.priorityAlgorithmByTaskComplex(models, inputStr, isComplex)
        return self.priorityAlgorithm(models)

    async def _callLLM(self, api: dict, inputStr: str) -> str:
        protocol = api.get("protocol", "openai")
        if protocol == "anthropic":
            return await self._callAnthropic(api, inputStr)
        elif protocol == "google":
            return await self._callGoogle(api, inputStr)
        elif protocol == "ollama":
            return await self._callOllama(api, inputStr)
        return await self._callOpenAI(api, inputStr)

    async def _callOpenAI(self, api: dict, inputStr: str) -> str:
        client = await self._getClient()
        url = api["endpointUrl"].rstrip("/")
        headers = {
            "Authorization": f"Bearer {api['apiKey']}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": api["modelName"],
            "messages": [{"role": "user", "content": inputStr}],
            "max_tokens": api["maxOutputToken"],
        }

        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    async def _callAnthropic(self, api: dict, inputStr: str) -> str:
        client = await self._getClient()
        url = api["endpointUrl"].rstrip("/")
        headers = {
            "x-api-key": api["apiKey"],
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        payload = {
            "model": api["modelName"],
            "max_tokens": api["maxOutputToken"],
            "messages": [{"role": "user", "content": inputStr}],
        }

        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        for item in data["content"]:
            if item.get("type") == "text":
                return item["text"]
        raise Exception("No text content in response")

    async def _callGoogle(self, api: dict, inputStr: str) -> str:
        client = await self._getClient()
        base_url = api["endpointUrl"].rstrip("/")
        url = f"{base_url}/v1beta/models/{api['modelName']}:generateContent"
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": api["apiKey"],
        }
        payload = {
            "contents": [{"parts": [{"text": inputStr}]}],
            "generationConfig": {"maxOutputTokens": api["maxOutputToken"]},
        }

        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]

    async def _callOllama(self, api: dict, inputStr: str) -> str:
        client = await self._getClient()
        url = api["endpointUrl"].rstrip("/")
        headers = {"Content-Type": "application/json"}
        payload = {
            "model": api["modelName"],
            "messages": [{"role": "user", "content": inputStr}],
            "stream": False,
            "options": {"num_predict": api["maxOutputToken"]},
        }

        response = await client.post(url, json=payload, headers=headers, timeout=120.0)
        response.raise_for_status()
        data = response.json()
        return data["message"]["content"]

    def decompose(self, api: list, priority: str = "") -> dict:
        models = {}
        for item in api:
            model_name = item["modelName"]
            models[model_name] = {
                "provider": item["provider"],
                "protocol": item.get("protocol", "openai"),
                "endpointUrl": item["endpointUrl"],
                "modelName": item["modelName"],
                "maxInputToken": item["maxInputToken"],
                "maxOutputToken": item["maxOutputToken"],
                "apiKey": item.get("apiKey", ""),
                # Capability tier (higher = more capable). Drives difficulty
                # tiering in priorityAlgorithmByTaskComplex. Defaults to 2.
                "tier": item.get("tier", 2),
            }

        self._priority_strategy = priority

        return {"models": models}

    def priorityAlgorithm(self, models: dict) -> list:
        return list(models.keys())

    def priorityAlgorithmByMaxTokens(self, models: dict) -> list:
        sorted_models = sorted(
            models.items(),
            key=lambda x: x[1]["maxInputToken"] + x[1]["maxOutputToken"],
            reverse=True,
        )
        return [name for name, _ in sorted_models]

    def priorityAlgorithmByTaskComplex(
        self, models: dict, inputStr: str, isComplex=None
    ) -> list:
        # Hard tasks prefer higher-tier (more capable) models; easy tasks prefer
        # the lowest-tier model first to save cost. Within a tier, ties break by
        # window size (bigger first for hard tasks). The token-fit guard in
        # connect() still drops any model whose window cannot hold the input.
        #
        # isComplex is decided by the caller from richer signals (see
        # AgentClient._assessComplexity). When not provided we fall back to a
        # crude prompt-length check so the router still works standalone.
        if isComplex is None:
            isComplex = len(inputStr) > getattr(self, "_complexity_threshold", 4000)
        sorted_models = sorted(
            models.items(),
            key=lambda x: (x[1].get("tier", 2), x[1]["maxInputToken"]),
            reverse=isComplex,
        )
        return [name for name, _ in sorted_models]
