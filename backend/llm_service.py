import json
import os
import re
import time
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

from .config import settings


class LLMService:
    """
    LLM service supporting OpenRouter and Gemini.

    OpenRouter is selected when LLM_PROVIDER=openrouter.
    Gemini remains available as a fallback provider.
    """

    def __init__(self):
        pass

    @property
    def provider(self) -> str:
        """
        Determine the configured provider.

        LLM_PROVIDER takes priority so that having a Gemini key
        in .env does not accidentally force Gemini usage.
        """
        return os.getenv(
            "LLM_PROVIDER",
            settings.LLM_PROVIDER,
        ).strip().lower()

    @property
    def api_key(self) -> str:
        """
        Return the API key for the selected provider.
        """
        if self.provider == "openrouter":
            return (
                os.getenv("OPENROUTER_API_KEY")
                or os.getenv("LLM_API_KEY")
                or ""
            ).strip()

        if self.provider == "gemini":
            return (
                os.getenv("GEMINI_API_KEY")
                or os.getenv("LLM_API_KEY")
                or ""
            ).strip()

        return (
            os.getenv("LLM_API_KEY")
            or os.getenv("OPENAI_API_KEY")
            or ""
        ).strip()

    @property
    def model(self) -> str:
        """
        Return the model configured for the active provider.
        """
        if self.provider == "openrouter":
            return os.getenv(
                "OPENROUTER_MODEL",
                "openrouter/free",
            ).strip()

        if self.provider == "gemini":
            return os.getenv(
                "LLM_MODEL",
                "gemini-3.6-flash",
            ).strip()

        return os.getenv(
            "LLM_MODEL",
            "gpt-4o-mini",
        ).strip()

    @property
    def base_url(self) -> str:
        """
        Return the API base URL.
        """
        if self.provider == "openrouter":
            return os.getenv(
                "OPENROUTER_BASE_URL",
                "https://openrouter.ai/api/v1",
            ).rstrip("/")

        return os.getenv(
            "LLM_BASE_URL",
            settings.LLM_BASE_URL,
        ).rstrip("/")

    def is_configured(self) -> bool:
        """
        Check whether an API key is available.
        """
        return bool(self.api_key)

    def _extract_json(self, raw_text: str) -> Dict[str, Any]:
        """
        Extract a JSON object from plain text or markdown fences.
        """
        text = raw_text.strip()

        # Remove markdown JSON fences:
        # ```json
        # {...}
        # ```
        fence_match = re.search(
            r"```(?:json)?\s*(\{.*?\})\s*```",
            text,
            re.DOTALL,
        )

        if fence_match:
            text = fence_match.group(1)

        elif text.startswith("```") and text.endswith("```"):
            lines = text.splitlines()

            if len(lines) >= 2:
                text = "\n".join(lines[1:-1])

        # First try the entire response.
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            pass

        # If extra text surrounds the JSON, extract the first object.
        object_match = re.search(
            r"\{.*\}",
            text,
            re.DOTALL,
        )

        if object_match:
            return json.loads(
                object_match.group(0)
            )

        raise ValueError(
            "The LLM response did not contain valid JSON."
        )

    def generate_plan(
        self,
        requirement: str,
    ) -> Dict[str, Any]:
        """
        Generate a structured software development plan.
        """
        if not requirement.strip():
            return {
                "success": False,
                "error": "Requirement cannot be empty.",
                "plan": None,
            }

        if not self.is_configured():
            return {
                "success": False,
                "error": (
                    "LLM API key is missing. "
                    "Set OPENROUTER_API_KEY or GEMINI_API_KEY "
                    "in the .env file."
                ),
                "plan": None,
            }

        system_prompt = (
            "You are an expert Autonomous AI Software Architect. "
            "Given a software requirement, create a structured "
            "JSON development plan. "
            "Return ONLY valid JSON with exactly these keys: "
            "'goal' (string), "
            "'architecture' (list of components), "
            "'execution_steps' "
            "(list of objects containing "
            "'step', 'role', 'action', 'file_target'), "
            "'risk_analysis' (list of risks), and "
            "'verification_plan' (list of verification steps)."
        )

        user_prompt = (
            f"Software Requirement:\n{requirement}"
        )

        try:
            return self._call_llm(
                system_prompt,
                user_prompt,
            )

        except urllib.error.HTTPError as error:
            return self._http_error_result(
                error
            )

        except Exception as error:
            return {
                "success": False,
                "error": (
                    f"LLM API Call failed: {error}"
                ),
                "plan": None,
            }

    def generate_code(
        self,
        goal: str,
        step_action: str,
        file_target: str,
        context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate complete source code for a target file.
        """
        if not self.is_configured():
            return {
                "success": False,
                "error": (
                    "LLM API key is missing."
                ),
                "file_target": file_target,
                "content": None,
            }

        system_prompt = (
            "You are an expert Autonomous AI Senior "
            "Software Engineer. "
            "Generate complete, robust code for the target file. "
            "Return ONLY valid JSON with exactly these keys: "
            "'file_target' (string), "
            "'content' (complete source code as a string), "
            "'explanation' (brief explanation). "
            "Do not put markdown fences around the JSON."
        )

        user_prompt = (
            f"Project Goal: {goal}\n"
            f"Step Action: {step_action}\n"
            f"Target File: {file_target}\n"
        )

        if context:
            user_prompt += (
                f"Context & Dependencies:\n{context}\n"
            )

        user_prompt += (
            "\nProvide the complete file content."
        )

        try:
            result = self._call_llm(
                system_prompt,
                user_prompt,
            )

            if not result["success"]:
                return {
                    "success": False,
                    "error": result.get(
                        "error",
                        "Code generation failed.",
                    ),
                    "file_target": file_target,
                    "content": None,
                }

            response_data = result.get(
                "plan"
            )

            if (
                isinstance(response_data, dict)
                and "content" in response_data
            ):
                content = response_data["content"]
                explanation = response_data.get(
                    "explanation",
                    f"Implemented {file_target}",
                )

            elif isinstance(
                response_data,
                str,
            ):
                content = response_data
                explanation = (
                    f"Implemented {file_target}"
                )

            else:
                content = str(response_data)
                explanation = (
                    f"Generated code for {file_target}"
                )

            return {
                "success": True,
                "provider": self.provider,
                "model": self.model,
                "file_target": file_target,
                "content": content,
                "explanation": explanation,
            }

        except urllib.error.HTTPError as error:
            return self._code_http_error_result(
                error,
                file_target,
            )

        except Exception as error:
            return {
                "success": False,
                "error": (
                    f"Code generation failed: {error}"
                ),
                "file_target": file_target,
                "content": None,
            }

    def _call_llm(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> Dict[str, Any]:
        """
        Dispatch the request to the configured provider.
        """
        if self.provider == "openrouter":
            return self._call_openrouter(
                system_prompt,
                user_prompt,
            )

        if self.provider == "gemini":
            return self._call_gemini(
                system_prompt,
                user_prompt,
            )

        return self._call_openai(
            system_prompt,
            user_prompt,
        )

    def _call_openrouter(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> Dict[str, Any]:
        """
        Call OpenRouter's OpenAI-compatible
        chat completions API.
        """
        url = (
            f"{self.base_url}/chat/completions"
        )

        headers = {
            "Content-Type": "application/json",
            "Authorization": (
                f"Bearer {self.api_key}"
            ),
            "HTTP-Referer": (
                "http://localhost:5173"
            ),
            "X-Title": (
                "Autonomous AI Software Engineer"
            ),
        }

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            "response_format": {
                "type": "json_object"
            },
            "temperature": 0.2,
        }

        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode(
                "utf-8"
            ),
            headers=headers,
            method="POST",
        )

        max_retries = 3

        for attempt in range(max_retries):
            try:
                with urllib.request.urlopen(
                    request,
                    timeout=90,
                ) as response:
                    response_body = json.loads(
                        response.read().decode(
                            "utf-8"
                        )
                    )

                choices = response_body.get(
                    "choices",
                    [],
                )

                if not choices:
                    raise ValueError(
                        "OpenRouter returned no choices."
                    )

                message = choices[0].get(
                    "message",
                    {},
                )

                content = message.get(
                    "content"
                )

                if not content:
                    raise ValueError(
                        "OpenRouter returned empty content."
                    )

                plan_data = (
                    self._extract_json(content)
                )

                return {
                    "success": True,
                    "provider": "openrouter",
                    "model": self.model,
                    "plan": plan_data,
                }

            except urllib.error.HTTPError as error:
                # Retry rate limits and temporary server errors.
                if (
                    error.code in (429, 500, 502, 503, 504)
                    and attempt < max_retries - 1
                ):
                    time.sleep(
                        2 * (attempt + 1)
                    )
                    continue

                raise

    def _call_gemini(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> Dict[str, Any]:
        """
        Call the Gemini generateContent API.
        """
        url = (
            "https://generativelanguage.googleapis.com/"
            f"v1beta/models/{self.model}"
            f":generateContent?key={self.api_key}"
        )

        headers = {
            "Content-Type": "application/json"
        }

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": (
                                f"{system_prompt}\n\n"
                                f"{user_prompt}"
                            )
                        }
                    ],
                }
            ],
            "generationConfig": {
                "response_mime_type": (
                    "application/json"
                ),
                "temperature": 0.2,
            },
        }

        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode(
                "utf-8"
            ),
            headers=headers,
            method="POST",
        )

        max_retries = 3

        for attempt in range(max_retries):
            try:
                with urllib.request.urlopen(
                    request,
                    timeout=90,
                ) as response:
                    response_body = json.loads(
                        response.read().decode(
                            "utf-8"
                        )
                    )

                text_content = (
                    response_body["candidates"][0]
                    ["content"]["parts"][0]["text"]
                )

                try:
                    plan_data = (
                        self._extract_json(
                            text_content
                        )
                    )
                except Exception:
                    plan_data = text_content

                return {
                    "success": True,
                    "provider": "gemini",
                    "model": self.model,
                    "plan": plan_data,
                }

            except (
                TimeoutError,
                urllib.error.URLError,
            ):
                if attempt < max_retries - 1:
                    time.sleep(
                        3 * (attempt + 1)
                    )
                    continue

                raise

    def _call_openai(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> Dict[str, Any]:
        """
        Generic OpenAI-compatible provider support.
        """
        url = (
            f"{self.base_url}/chat/completions"
        )

        headers = {
            "Content-Type": "application/json",
            "Authorization": (
                f"Bearer {self.api_key}"
            ),
        }

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            "response_format": {
                "type": "json_object"
            },
            "temperature": 0.2,
        }

        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode(
                "utf-8"
            ),
            headers=headers,
            method="POST",
        )

        with urllib.request.urlopen(
            request,
            timeout=90,
        ) as response:
            response_body = json.loads(
                response.read().decode(
                    "utf-8"
                )
            )

        content = (
            response_body["choices"][0]
            ["message"]["content"]
        )

        plan_data = self._extract_json(
            content
        )

        return {
            "success": True,
            "provider": "openai",
            "model": self.model,
            "plan": plan_data,
        }

    def _http_error_result(
        self,
        error: urllib.error.HTTPError,
    ) -> Dict[str, Any]:
        """
        Convert an HTTP error into a readable
        generate_plan response.
        """
        message = str(error)

        try:
            body = json.loads(
                error.read().decode("utf-8")
            )

            if (
                isinstance(body, dict)
                and isinstance(
                    body.get("error"),
                    dict,
                )
                and body["error"].get(
                    "message"
                )
            ):
                message = (
                    f"{error.code} - "
                    f"{body['error']['message']}"
                )
        except Exception:
            pass

        return {
            "success": False,
            "error": (
                "LLM API Call failed: "
                f"HTTP Error {message}"
            ),
            "plan": None,
        }

    def _code_http_error_result(
        self,
        error: urllib.error.HTTPError,
        file_target: str,
    ) -> Dict[str, Any]:
        """
        Convert an HTTP error into a readable
        generate_code response.
        """
        message = str(error)

        try:
            body = json.loads(
                error.read().decode("utf-8")
            )

            if (
                isinstance(body, dict)
                and isinstance(
                    body.get("error"),
                    dict,
                )
                and body["error"].get(
                    "message"
                )
            ):
                message = (
                    f"{error.code} - "
                    f"{body['error']['message']}"
                )
        except Exception:
            pass

        return {
            "success": False,
            "error": (
                "LLM API Call failed: "
                f"HTTP Error {message}"
            ),
            "file_target": file_target,
            "content": None,
        }


llm_service = LLMService()