import unittest
from unittest.mock import patch, Mock
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from disesfgewuAgent.llmRouter import llmRouter


class TestLLMRouter(unittest.TestCase):
    def setUp(self):
        self.sample_config = [
            {
                "provider": "openai",
                "endpointUrl": "https://api.openai.com",
                "modelName": "gpt-4",
                "maxInputToken": 8192,
                "maxOutputToken": 4096,
                "apiKey": "test-key-1"
            },
            {
                "provider": "openai",
                "endpointUrl": "https://api.openai.com",
                "modelName": "gpt-3.5-turbo",
                "maxInputToken": 16385,
                "maxOutputToken": 4096,
                "apiKey": "test-key-2"
            }
        ]

    @patch('builtins.open')
    @patch('json.load')
    def test_init_loads_config(self, mock_json_load, mock_open):
        mock_json_load.return_value = self.sample_config
        router = llmRouter()
        self.assertIn("models", router._api)
        self.assertEqual(router._priority_strategy, "")

    def test_decompose_creates_models_dict(self):
        router = object.__new__(llmRouter)
        result = router.decompose(self.sample_config)
        
        self.assertIn("models", result)
        self.assertEqual(len(result["models"]), 2)
        self.assertIn("gpt-4", result["models"])
        self.assertIn("gpt-3.5-turbo", result["models"])

    def test_decompose_with_max_tokens_priority(self):
        router = object.__new__(llmRouter)
        router._api = router.decompose(self.sample_config, priority="maxTokens")
        
        priority_list = router._getPriorityList("")
        self.assertEqual(priority_list[0], "gpt-3.5-turbo")
        self.assertEqual(priority_list[1], "gpt-4")

    def test_decompose_with_task_complex_priority(self):
        router = object.__new__(llmRouter)
        router._api = router.decompose(self.sample_config, priority="taskComplex")
        
        priority_list = router._getPriorityList("short")
        self.assertEqual(len(priority_list), 2)

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
            "gpt-3.5-turbo": {"maxInputToken": 16385, "maxOutputToken": 4096}
        }
        
        result = router.priorityAlgorithmByMaxTokens(models)
        self.assertEqual(result[0], "gpt-3.5-turbo")
        self.assertEqual(result[1], "gpt-4")

    def test_priorityAlgorithmByTaskComplex_short_input(self):
        router = object.__new__(llmRouter)
        models = {
            "gpt-4": {"maxInputToken": 8192},
            "gpt-3.5-turbo": {"maxInputToken": 16385}
        }
        
        result = router.priorityAlgorithmByTaskComplex(models, "short input")
        self.assertEqual(result[0], "gpt-4")
        self.assertEqual(result[1], "gpt-3.5-turbo")

    def test_priorityAlgorithmByTaskComplex_long_input(self):
        router = object.__new__(llmRouter)
        models = {
            "gpt-4": {"maxInputToken": 8192},
            "gpt-3.5-turbo": {"maxInputToken": 16385}
        }
        
        long_input = "x" * 1500
        result = router.priorityAlgorithmByTaskComplex(models, long_input)
        self.assertEqual(result[0], "gpt-3.5-turbo")
        self.assertEqual(result[1], "gpt-4")

    @patch('httpx.Client')
    def test_callLLM_makes_correct_request(self, mock_client_class):
        mock_client = Mock()
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Hello!"}}]
        }
        mock_response.raise_for_status = Mock()
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_class.return_value = mock_client

        router = object.__new__(llmRouter)
        router._client = mock_client
        api = {
            "endpointUrl": "https://api.openai.com",
            "modelName": "gpt-4",
            "apiKey": "test-key"
        }

        result = router._callLLM(api, "Hello")

        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        self.assertIn("gpt-4", str(call_args))
        self.assertIn("Hello", str(call_args))
        self.assertEqual(result, "Hello!")

    @patch('httpx.Client')
    def test_connect_uses_priority_list(self, mock_client_class):
        mock_client = Mock()
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Response"}}]
        }
        mock_response.raise_for_status = Mock()
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_class.return_value = mock_client

        router = object.__new__(llmRouter)
        router._client = mock_client
        router._api = router.decompose(self.sample_config)

        result = router.connect("Test input")

        self.assertEqual(result, "Response")
        mock_client.post.assert_called_once()

    @patch('httpx.Client')
    def test_connect_with_model_override(self, mock_client_class):
        mock_client = Mock()
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Response"}}]
        }
        mock_response.raise_for_status = Mock()
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_class.return_value = mock_client

        router = object.__new__(llmRouter)
        router._client = mock_client
        router._api = router.decompose(self.sample_config)

        result = router.connect("Test", modelName="gpt-3.5-turbo")

        self.assertEqual(result, "Response")
        call_args = mock_client.post.call_args
        self.assertIn("gpt-3.5-turbo", str(call_args))

    @patch('httpx.Client')
    def test_connect_fallback_on_failure(self, mock_client_class):
        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        
        call_count = [0]
        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("First model failed")
            mock_response = Mock()
            mock_response.json.return_value = {
                "choices": [{"message": {"content": "Fallback response"}}]
            }
            mock_response.raise_for_status = Mock()
            return mock_response
        
        mock_client.post.side_effect = side_effect
        mock_client_class.return_value = mock_client

        router = object.__new__(llmRouter)
        router._client = mock_client
        router._api = router.decompose(self.sample_config)

        result = router.connect("Test")

        self.assertEqual(result, "Fallback response")
        self.assertEqual(call_count[0], 2)

    def test_connect_raises_when_all_fail(self):
        router = object.__new__(llmRouter)
        router._api = router.decompose(self.sample_config)

        with patch('httpx.Client') as mock_client_class:
            mock_client = Mock()
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=None)
            mock_client.post.side_effect = Exception("API Error")
            mock_client_class.return_value = mock_client

            router._client = mock_client

            with self.assertRaises(Exception) as context:
                router.connect("Test")
            
            self.assertIn("All LLM endpoints failed", str(context.exception))
            self.assertIn("gpt-4", str(context.exception))
            self.assertIn("gpt-3.5-turbo", str(context.exception))

    def test_connect_raises_on_invalid_model_name(self):
        router = object.__new__(llmRouter)
        router._api = router.decompose(self.sample_config)
        router._client = Mock()

        with self.assertRaises(ValueError) as context:
            router.connect("Test", modelName="nonexistent-model")
        
        self.assertIn("nonexistent-model", str(context.exception))

    @patch('httpx.Client')
    def test_connect_with_priority_override(self, mock_client_class):
        mock_client = Mock()
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Response"}}]
        }
        mock_response.raise_for_status = Mock()
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_class.return_value = mock_client

        router = object.__new__(llmRouter)
        router._client = mock_client
        router._api = router.decompose(self.sample_config, priority="")

        result = router.connect("Test", priority="maxTokens")

        self.assertEqual(result, "Response")
        call_args = mock_client.post.call_args
        self.assertIn("gpt-3.5-turbo", str(call_args))

    @patch('httpx.Client')
    def test_connect_with_task_complex_priority(self, mock_client_class):
        mock_client = Mock()
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Response"}}]
        }
        mock_response.raise_for_status = Mock()
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_class.return_value = mock_client

        router = object.__new__(llmRouter)
        router._client = mock_client
        router._api = router.decompose(self.sample_config, priority="taskComplex")

        long_input = "x" * 1500
        result = router.connect(long_input)

        self.assertEqual(result, "Response")
        call_args = mock_client.post.call_args
        self.assertIn("gpt-3.5-turbo", str(call_args))

    @patch('httpx.Client')
    def test_callGoogle_makes_correct_request(self, mock_client_class):
        mock_client = Mock()
        mock_response = Mock()
        mock_response.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": "Google response!"}]}}]
        }
        mock_response.raise_for_status = Mock()
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_class.return_value = mock_client

        router = object.__new__(llmRouter)
        router._client = mock_client
        api = {
            "protocol": "google",
            "endpointUrl": "https://generativelanguage.googleapis.com",
            "modelName": "gemini-2.5-pro",
            "apiKey": "test-key"
        }

        result = router._callLLM(api, "Hello Google")

        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        self.assertIn("gemini-2.5-pro", str(call_args))
        self.assertIn("Hello Google", str(call_args))
        self.assertEqual(result, "Google response!")

    @patch('httpx.Client')
    def test_callOllama_makes_correct_request(self, mock_client_class):
        mock_client = Mock()
        mock_response = Mock()
        mock_response.json.return_value = {
            "message": {"content": "Ollama response!"}
        }
        mock_response.raise_for_status = Mock()
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_class.return_value = mock_client

        router = object.__new__(llmRouter)
        router._client = mock_client
        api = {
            "protocol": "ollama",
            "endpointUrl": "http://localhost:11434/api/chat",
            "modelName": "llama3.3",
            "apiKey": ""
        }

        result = router._callLLM(api, "Hello Ollama")

        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        self.assertIn("llama3.3", str(call_args))
        self.assertIn("Hello Ollama", str(call_args))
        self.assertEqual(result, "Ollama response!")

    @patch('httpx.Client')
    def test_callAnthropic_makes_correct_request(self, mock_client_class):
        mock_client = Mock()
        mock_response = Mock()
        mock_response.json.return_value = {
            "content": [{"type": "text", "text": "Anthropic response!"}]
        }
        mock_response.raise_for_status = Mock()
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_class.return_value = mock_client

        router = object.__new__(llmRouter)
        router._client = mock_client
        api = {
            "protocol": "anthropic",
            "endpointUrl": "https://api.anthropic.com",
            "modelName": "claude-3-opus",
            "maxOutputToken": 4096,
            "apiKey": "test-key"
        }

        result = router._callLLM(api, "Hello Anthropic")

        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        self.assertIn("claude-3-opus", str(call_args))
        self.assertIn("Hello Anthropic", str(call_args))
        self.assertEqual(result, "Anthropic response!")

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
                "apiKey": "test-key"
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
                "apiKey": "test-key"
            }
        ]
        result = router.decompose(config)
        
        self.assertEqual(result["models"]["custom-model"]["protocol"], "openai")


if __name__ == '__main__':
    unittest.main()
