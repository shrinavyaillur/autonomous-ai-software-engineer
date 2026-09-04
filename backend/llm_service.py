import time
import os
import json
import urllib.request
import urllib.error
import re
from typing import Dict, Any, Optional
from .config import settings

class LLMService:
    def __init__(self):
        pass

    @property
    def api_key(self) -> str:
        return os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("GEMINI_API_KEY") or settings.LLM_API_KEY

    @property
    def provider(self) -> str:
        if os.getenv("GEMINI_API_KEY") or settings.LLM_API_KEY.startswith("AQ.") or settings.LLM_API_KEY.startswith("AIza"):
            return "gemini"
        return os.getenv("LLM_PROVIDER", settings.LLM_PROVIDER).lower()

    @property
    def model(self) -> str:
        if self.provider == "gemini":
            return os.getenv("LLM_MODEL", "gemini-3.6-flash")
        return os.getenv("LLM_MODEL", settings.LLM_MODEL)

    def is_configured(self) -> bool:
        return bool(self.api_key.strip())

    def _extract_json(self, raw_text: str) -> Dict[str, Any]:
        text = raw_text.strip()
        # Remove markdown code fences if wrapped in ```json ... ```
        fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if fence_match:
            text = fence_match.group(1)
        elif text.startswith("```") and text.endswith("```"):
            lines = text.splitlines()
            if len(lines) >= 2:
                text = "\n".join(lines[1:-1])
        return json.loads(text.strip())

    def generate_plan(self, requirement: str) -> Dict[str, Any]:
        """
        Receives a software requirement prompt and uses the connected LLM to generate a structured development plan.
        """
        if not self.is_configured():
            return {
                "success": False,
                "error": "LLM API Key is missing. Please set 'OPENAI_API_KEY', 'GEMINI_API_KEY', or 'LLM_API_KEY' in your environment or .env file.",
                "plan": None
            }

        system_prompt = (
            "You are an expert Autonomous AI Software Architect. "
            "Given a software requirement or feature goal, construct a structured JSON development plan with keys: "
            "'goal' (string), 'architecture' (list of components), "
            "'execution_steps' (list of objects with 'step', 'role', 'action', 'file_target'), "
            "'risk_analysis' (list of risks), and 'verification_plan' (list of verification steps). "
            "Output ONLY valid raw JSON."
        )

        user_prompt = f"Software Requirement:\n{requirement}"

        try:
            if self.provider == "gemini":
                return self._call_gemini(system_prompt, user_prompt)
            else:
                return self._call_openai(system_prompt, user_prompt)
        except urllib.error.HTTPError as he:
            err_msg = str(he)
            try:
                body = json.loads(he.read().decode("utf-8"))
                if "error" in body and "message" in body["error"]:
                    err_msg = f"{he.code} - {body['error']['message']}"
            except Exception:
                pass
            return {
                "success": False,
                "error": f"LLM API Call failed: HTTP Error {err_msg}",
                "plan": None
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"LLM API Call failed: {str(e)}",
                "plan": None
            }

    def generate_code(self, goal: str, step_action: str, file_target: str, context: Optional[str] = None) -> Dict[str, Any]:
        """
        Generates production-quality source code for a specific file target based on the development plan.
        """
        if not self.is_configured():
            return {
                "success": False,
                "error": "LLM API Key is missing. Please configure GEMINI_API_KEY or LLM_API_KEY.",
                "file_target": file_target,
                "content": None
            }

        system_prompt = (
            "You are an expert Autonomous AI Senior Software Engineer. "
            "Generate complete, robust, production-ready code for the target file to satisfy the given development step. "
            "Return valid JSON ONLY with three keys: "
            "'file_target' (string matching the target path), "
            "'content' (the complete source code as a single string, including imports, comments, and logic), and "
            "'explanation' (a concise 1-2 sentence description of what was implemented). "
            "Do NOT include markdown fences outside the JSON string."
        )

        user_prompt = (
            f"Project Goal: {goal}\n"
            f"Step Action: {step_action}\n"
            f"Target File: {file_target}\n"
        )
        if context:
            user_prompt += f"Context & Dependencies:\n{context}\n"
        user_prompt += "\nProvide the complete file content."

        try:
            if self.provider == "gemini":
                raw_res = self._call_gemini(system_prompt, user_prompt)
            else:
                raw_res = self._call_openai(system_prompt, user_prompt)

            if not raw_res["success"]:
                return {
                    "success": False,
                    "error": raw_res.get("error", "Code generation failed"),
                    "file_target": file_target,
                    "content": None
                }

            plan_or_code = raw_res["plan"]
            if isinstance(plan_or_code, dict) and "content" in plan_or_code:
                content = plan_or_code["content"]
                explanation = plan_or_code.get("explanation", f"Implemented {file_target}")
            elif isinstance(plan_or_code, str):
                content = plan_or_code
                explanation = f"Implemented {file_target}"
            else:
                # If plan_or_code has other keys, convert or serialize cleanly
                content = str(plan_or_code)
                explanation = f"Generated code for {file_target}"

            return {
                "success": True,
                "provider": self.provider,
                "model": self.model,
                "file_target": file_target,
                "content": content,
                "explanation": explanation
            }
        except urllib.error.HTTPError as he:
            err_msg = str(he)
            try:
                body = json.loads(he.read().decode("utf-8"))
                if "error" in body and "message" in body["error"]:
                    err_msg = f"{he.code} - {body['error']['message']}"
            except Exception:
                pass
            return {
                "success": False,
                "error": f"LLM API Call failed: HTTP Error {err_msg}",
                "file_target": file_target,
                "content": None
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Code generation failed: {str(e)}",
                "file_target": file_target,
                "content": None
            }

    def _call_openai(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        url = f"{settings.LLM_BASE_URL.rstrip('/')}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2
        }

        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=90) as response:
            res_body = json.loads(response.read().decode("utf-8"))
            content = res_body["choices"][0]["message"]["content"]
            plan_data = self._extract_json(content)
            return {
                "success": True,
                "provider": "openai",
                "model": self.model,
                "plan": plan_data
            }

    def _call_gemini(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": f"{system_prompt}\n\n{user_prompt}"}]
                }
            ],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.2
            }
        }

        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        max_retries = 3
        for attempt in range(max_retries):
            try:
                with urllib.request.urlopen(req, timeout=90) as response:
                    res_body = json.loads(response.read().decode("utf-8"))
                    text_content = res_body["candidates"][0]["content"]["parts"][0]["text"]
                    try:
                        plan_data = self._extract_json(text_content)
                    except Exception:
                        plan_data = text_content
                    return {
                        "success": True,
                        "provider": "gemini",
                        "model": self.model,
                        "plan": plan_data
                    }
            except (TimeoutError, urllib.error.URLError) as err:
                if attempt < max_retries - 1:
                    time.sleep(3 * (attempt + 1))
                    continue
                raise

llm_service = LLMService()
