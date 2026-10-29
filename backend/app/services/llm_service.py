import sys
import requests
from backend.app.core.encoding import safe_print
print = safe_print

from backend.app.core.config import settings


class LLMService:

    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL.rstrip("/")
        self.model = settings.OLLAMA_MODEL

    # ============================================================
    # VERIFY OLLAMA
    # ============================================================

    def verify_ollama_and_model(self) -> bool:
        """
        Verify that Ollama is running and that the configured
        model is installed.
        """

        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=5
            )

            response.raise_for_status()

        except requests.exceptions.RequestException as e:

            raise ConnectionError(
                f"Ollama is not running at {self.base_url}. "
                f"Please start Ollama before querying."
            ) from e

        try:
            data = response.json()

        except ValueError as e:

            raise RuntimeError(
                "Ollama returned an invalid JSON response."
            ) from e

        models = [
            model.get("name", "")
            for model in data.get("models", [])
        ]

        model_exists = (
            self.model in models
            or f"{self.model}:latest" in models
            or any(
                self.model in model_name
                for model_name in models
            )
        )

        if not model_exists:

            raise ValueError(
                f"Model '{self.model}' is not installed in Ollama. "
                f"Please run: ollama pull {self.model}"
            )

        return True

    # ============================================================
    # GENERATE RESPONSE
    # ============================================================

    def generate(
        self,
        prompt: str,
        system_prompt: str = None
    ) -> str:

        # --------------------------------------------------------
        # Verify Ollama
        # --------------------------------------------------------

        self.verify_ollama_and_model()

        url = f"{self.base_url}/api/generate"

        # --------------------------------------------------------
        # Ollama payload
        # --------------------------------------------------------
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,

            "options": {
                # Keep responses deterministic
                "temperature": 0.1,

                # Large response token limit to allow Qwen3 reasoning to finish
                "num_predict": 1024,

                # Reduce excessive thinking/generation
                "top_p": 0.8
            }
        }

        if system_prompt:
            payload["system"] = system_prompt

        # --------------------------------------------------------
        # Debug
        # --------------------------------------------------------

        print("\n========================================")
        print("OLLAMA REQUEST")
        print("========================================")
        print("Model:", self.model)
        print("URL:", url)
        print("Prompt characters:", len(prompt))

        if system_prompt:
            print(
                "System prompt characters:",
                len(system_prompt)
            )

        print("========================================")

        # --------------------------------------------------------
        # Send request
        # --------------------------------------------------------

        try:

            response = requests.post(
                url,
                json=payload,
                timeout=180
            )

            response.raise_for_status()

        except requests.exceptions.Timeout as e:

            raise RuntimeError(
                "Ollama generation timed out. "
                "The model is taking too long to respond."
            ) from e

        except requests.exceptions.ConnectionError as e:

            raise RuntimeError(
                "Could not connect to Ollama. "
                "Please make sure Ollama is running."
            ) from e

        except requests.exceptions.RequestException as e:

            raise RuntimeError(
                f"Failed to communicate with Ollama API: {str(e)}"
            ) from e

        # --------------------------------------------------------
        # Parse response
        # --------------------------------------------------------

        try:

            data = response.json()

        except ValueError as e:

            raise RuntimeError(
                "Ollama returned an invalid JSON response."
            ) from e

        response_text = data.get(
            "response",
            ""
        ).strip()

        # --------------------------------------------------------
        # Empty response protection
        # --------------------------------------------------------

        if not response_text:

            print("\n========================================")
            print("OLLAMA EMPTY RESPONSE")
            print("========================================")
            print("Raw Ollama response:")
            print(data)
            print("========================================")

            raise ValueError(
                "Ollama returned an empty response."
            )

        # --------------------------------------------------------
        # Debug response (Task 8 details)
        # --------------------------------------------------------

        print("\n========================================")
        print("OLLAMA RESPONSE DETAILS")
        print("========================================")
        print("Ollama URL:", url)
        print("Model:", self.model)
        print("HTTP status:", response.status_code)
        print("Response keys:", list(data.keys()))
        print("Response length:", len(response_text))
        print("========================================")

        return response_text