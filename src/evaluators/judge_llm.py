"""Calls an LLM to score output quality (accuracy, relevance)."""

import json
from typing import Any

import httpx

from src.config import settings


class JudgeLLM:
    """LLM-as-judge evaluator that calls a configured LLM endpoint."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
    ):
        self.base_url = base_url or getattr(settings, "llm_base_url", None)
        self.api_key = api_key or getattr(settings, "llm_api_key", None)
        self.model = model or getattr(settings, "llm_model", "gpt-4")

    async def score(self, output: str, reference: str | None = None) -> dict[str, Any]:
        """Score an LLM output for accuracy and relevance via an LLM judge."""
        if not self.base_url or not self.api_key:
            return {
                "accuracy": 0.0,
                "relevance": 0.0,
                "rationale": "LLM judge not configured (missing base_url or api_key)",
            }

        prompt = self._build_prompt(output, reference)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0,
            "response_format": {"type": "json_object"},
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{self.base_url.rstrip('/')}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:  # noqa: BLE001
            return {
                "accuracy": 0.0,
                "relevance": 0.0,
                "rationale": f"LLM judge call failed: {exc}",
            }

        content = data.get("choices", [{}])[0].get("message", {}).get("content", "{}")
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            parsed = {}

        return {
            "accuracy": float(parsed.get("accuracy", 0.0)),
            "relevance": float(parsed.get("relevance", 0.0)),
            "rationale": parsed.get("rationale", ""),
        }

    @staticmethod
    def _build_prompt(output: str, reference: str | None) -> str:
        ref_section = f"\nReference answer:\n{reference}" if reference else ""
        return (
            "You are a quality judge. Score the following model output on accuracy and "
            "relevance (0.0 to 1.0 each). Return ONLY a JSON object with keys: "
            "accuracy, relevance, rationale.\n\n"
            f"Model output:\n{output}{ref_section}"
        )
