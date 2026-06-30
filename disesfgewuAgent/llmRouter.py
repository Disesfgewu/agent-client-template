import json
import os
from typing import Optional
import httpx


class llmRouter:
    def __init__(self) -> None:
        config_path = os.path.join(
            os.path.dirname(__file__), "..", "config", "api.local.json"
        )
        with open(config_path, "r") as f:
            api = json.load(f)
        self._api = self.decompose(api)
        self._client = httpx.Client(timeout=60.0)

    def getApi(self, modelName: str) -> Optional[dict]:
        if modelName in self._api["models"]:
            return self._api["models"][modelName]
        return None

    def connect(
        self, inputStr: str, modelName: str = None, priority: str = "", inputToken=0
    ):
        if modelName:
            if not self.getApi(modelName):
                raise ValueError(f"Model '{modelName}' not found in config")
            priority_list = [modelName]
        else:
            priority_list = self._getPriorityList(inputStr, priority)

        errors = []
        for model_name in priority_list:
            api = self.getApi(model_name)
            if not api:
                continue
            try:
                if inputToken > int(api[model_name]["maxInputToken"]):
                    continue
                answer = self._callLLM(api, inputStr)
                return answer
            except Exception as e:
                errors.append(f"{model_name}: {str(e)}")
                continue

        error_msg = "All LLM endpoints failed:\n" + "\n".join(errors)
        raise Exception(error_msg)

    def _getPriorityList(self, inputStr: str, priority: str = "") -> list:
        strategy = priority or self._priority_strategy
        models = self._api["models"]
        if strategy == "maxTokens":
            return self.priorityAlgorithmByMaxTokens(models)
        elif strategy == "taskComplex":
            return self.priorityAlgorithmByTaskComplex(models, inputStr)
        return self.priorityAlgorithm(models)

    def _callLLM(self, api: dict, inputStr: str) -> str:
        protocol = api.get("protocol", "openai")
        if protocol == "anthropic":
            return self._callAnthropic(api, inputStr)
        elif protocol == "google":
            return self._callGoogle(api, inputStr)
        elif protocol == "ollama":
            return self._callOllama(api, inputStr)
        return self._callOpenAI(api, inputStr)

    def _callOpenAI(self, api: dict, inputStr: str) -> str:
        url = api["endpointUrl"].rstrip("/")
        headers = {
            "Authorization": f"Bearer {api['apiKey']}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": api["modelName"],
            "messages": [{"role": "user", "content": inputStr}],
        }

        response = self._client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    def _callAnthropic(self, api: dict, inputStr: str) -> str:
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

        response = self._client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        for item in data["content"]:
            if item.get("type") == "text":
                return item["text"]
        raise Exception("No text content in response")

    def _callGoogle(self, api: dict, inputStr: str) -> str:
        base_url = api["endpointUrl"].rstrip("/")
        url = f"{base_url}/v1beta/models/{api['modelName']}:generateContent"
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": api["apiKey"],
        }
        payload = {"contents": [{"parts": [{"text": inputStr}]}]}

        response = self._client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]

    def _callOllama(self, api: dict, inputStr: str) -> str:
        url = api["endpointUrl"].rstrip("/")
        headers = {"Content-Type": "application/json"}
        payload = {
            "model": api["modelName"],
            "messages": [{"role": "user", "content": inputStr}],
            "stream": False,
        }

        response = self._client.post(url, json=payload, headers=headers, timeout=120.0)
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

    def priorityAlgorithmByTaskComplex(self, models: dict, inputStr: str) -> list:
        complexity = len(inputStr)
        if complexity > 1000:
            sorted_models = sorted(
                models.items(), key=lambda x: x[1]["maxInputToken"], reverse=True
            )
        else:
            sorted_models = sorted(
                models.items(), key=lambda x: x[1]["maxInputToken"], reverse=False
            )
        return [name for name, _ in sorted_models]
