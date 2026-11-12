"""Token-to-cost conversion per model."""

from typing import Any


class CostCalculator:
    """Converts token usage to cost per model using a built-in price table."""

    # Prices in USD per 1,000 tokens (input, output).
    MODEL_COSTS: dict[str, dict[str, float]] = {
        "gpt-4": {"input_per_1k": 0.03, "output_per_1k": 0.06},
        "gpt-4-turbo": {"input_per_1k": 0.01, "output_per_1k": 0.03},
        "gpt-3.5-turbo": {"input_per_1k": 0.0015, "output_per_1k": 0.002},
        "gpt-3.5-turbo-16k": {"input_per_1k": 0.003, "output_per_1k": 0.004},
        "claude-3-opus": {"input_per_1k": 0.015, "output_per_1k": 0.075},
        "claude-3-sonnet": {"input_per_1k": 0.003, "output_per_1k": 0.015},
        "claude-3-haiku": {"input_per_1k": 0.00025, "output_per_1k": 0.00125},
    }

    def __init__(self, custom_costs: dict[str, dict[str, float]] | None = None):
        self.model_costs = dict(self.MODEL_COSTS)
        if custom_costs:
            for model, costs in custom_costs.items():
                self.model_costs[model] = costs

    def calculate(self, model: str, input_tokens: int, output_tokens: int) -> dict[str, Any]:
        """Calculate cost for a model given token counts."""
        costs = self.model_costs.get(
            model, {"input_per_1k": 0.0, "output_per_1k": 0.0}
        )
        input_cost = (input_tokens / 1000.0) * costs["input_per_1k"]
        output_cost = (output_tokens / 1000.0) * costs["output_per_1k"]
        total = input_cost + output_cost
        return {
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "input_cost_usd": round(input_cost, 6),
            "output_cost_usd": round(output_cost, 6),
            "total_cost_usd": round(total, 6),
        }

    def add_model(self, model: str, input_per_1k: float, output_per_1k: float) -> None:
        """Register a custom model price."""
        self.model_costs[model] = {
            "input_per_1k": input_per_1k,
            "output_per_1k": output_per_1k,
        }
