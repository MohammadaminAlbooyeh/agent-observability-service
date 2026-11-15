"""Deterministic checks (schema validity, length, keyword presence)."""

import json
from typing import Any


class RuleBasedChecks:
    """Deterministic validation checks for trace outputs."""

    def check_schema(self, output: Any, schema: dict) -> bool:
        """Validate output against a simple JSON Schema subset (type + required)."""
        try:
            parsed = json.loads(output) if isinstance(output, str) else output
        except (json.JSONDecodeError, TypeError):
            return False

        if not isinstance(parsed, dict):
            return False

        # Check required fields
        required = schema.get("required", [])
        for field in required:
            if field not in parsed:
                return False

        # Check types for properties
        properties = schema.get("properties", {})
        for field, field_schema in properties.items():
            if field in parsed:
                expected_type = field_schema.get("type")
                if expected_type and not self._type_matches(parsed[field], expected_type):
                    return False
        return True

    @staticmethod
    def _type_matches(value: Any, expected_type: str) -> bool:
        type_map = {
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
            "array": list,
            "object": dict,
            "null": type(None),
        }
        python_type = type_map.get(expected_type)
        if python_type is None:
            return True
        if isinstance(value, bool) and expected_type in ("integer", "number"):
            return False
        return isinstance(value, python_type)

    def check_length(
        self, text: str, min_len: int = 0, max_len: int | None = None
    ) -> bool:
        """Check text length bounds."""
        if len(text) < min_len:
            return False
        if max_len is not None and len(text) > max_len:
            return False
        return True

    def check_keyword(self, text: str, keyword: str) -> bool:
        """Check keyword presence in text (case-insensitive)."""
        return keyword.lower() in text.lower()

    def check_all(
        self,
        output: Any,
        schema: dict | None = None,
        min_len: int = 0,
        max_len: int | None = None,
        keyword: str | None = None,
    ) -> dict[str, Any]:
        """Run a bundle of deterministic checks and return per-check results."""
        results: dict[str, Any] = {
            "schema": True,
            "length": True,
            "keyword": True,
            "passed": True,
        }

        if schema is not None:
            results["schema"] = self.check_schema(output, schema)

        if isinstance(output, str):
            results["length"] = self.check_length(output, min_len, max_len)
        else:
            results["length"] = True

        if keyword is not None and isinstance(output, str):
            results["keyword"] = self.check_keyword(output, keyword)

        results["passed"] = all(
            results[k] for k in ("schema", "length", "keyword")
        )
        return results
