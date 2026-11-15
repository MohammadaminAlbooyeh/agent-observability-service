"""Unit tests for evaluators."""


from src.evaluators.cost_calculator import CostCalculator
from src.evaluators.rule_based_checks import RuleBasedChecks


class TestCostCalculator:
    def test_calculate_known_model(self):
        calc = CostCalculator()
        result = calc.calculate("gpt-4", 1000, 1000)
        assert result["model"] == "gpt-4"
        assert result["input_tokens"] == 1000
        assert result["output_tokens"] == 1000
        assert result["input_cost_usd"] == 0.03
        assert result["output_cost_usd"] == 0.06
        assert result["total_cost_usd"] == 0.09

    def test_calculate_unknown_model(self):
        calc = CostCalculator()
        result = calc.calculate("unknown-model", 1000, 1000)
        assert result["total_cost_usd"] == 0.0

    def test_add_custom_model(self):
        calc = CostCalculator()
        calc.add_model("custom-model", 0.01, 0.02)
        result = calc.calculate("custom-model", 2000, 3000)
        assert result["input_cost_usd"] == 0.02
        assert result["output_cost_usd"] == 0.06
        assert result["total_cost_usd"] == 0.08

    def test_rounding(self):
        calc = CostCalculator()
        result = calc.calculate("gpt-3.5-turbo", 1, 1)
        assert result["total_cost_usd"] == round(0.0015 / 1000 + 0.002 / 1000, 6)


class TestRuleBasedChecks:
    def test_check_schema_valid(self):
        checks = RuleBasedChecks()
        output = '{"name": "foo", "age": 30}'
        schema = {
            "type": "object",
            "required": ["name", "age"],
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
            },
        }
        assert checks.check_schema(output, schema) is True

    def test_check_schema_missing_required(self):
        checks = RuleBasedChecks()
        output = '{"name": "foo"}'
        schema = {"required": ["name", "age"]}
        assert checks.check_schema(output, schema) is False

    def test_check_schema_wrong_type(self):
        checks = RuleBasedChecks()
        output = '{"age": "thirty"}'
        schema = {"properties": {"age": {"type": "integer"}}}
        assert checks.check_schema(output, schema) is False

    def test_check_schema_bool_is_not_integer(self):
        checks = RuleBasedChecks()
        schema = {"properties": {"n": {"type": "integer"}}}
        assert checks.check_schema('{"n": true}', schema) is False

    def test_check_schema_invalid_json(self):
        checks = RuleBasedChecks()
        assert checks.check_schema("not json", {}) is False

    def test_check_length(self):
        checks = RuleBasedChecks()
        assert checks.check_length("hello", min_len=3, max_len=10) is True
        assert checks.check_length("hi", min_len=3) is False
        assert checks.check_length("way too long", max_len=5) is False

    def test_check_keyword(self):
        checks = RuleBasedChecks()
        assert checks.check_keyword("Hello World", "world") is True
        assert checks.check_keyword("Hello World", "python") is False

    def test_check_all_passed(self):
        checks = RuleBasedChecks()
        result = checks.check_all(
            '{"name": "foo"}',
            schema={"required": ["name"]},
            min_len=1,
            keyword="name",
        )
        assert result["passed"] is True
        assert result["schema"] is True
        assert result["length"] is True
        assert result["keyword"] is True

    def test_check_all_failed(self):
        checks = RuleBasedChecks()
        result = checks.check_all(
            '{"other": 1}',
            schema={"required": ["name"]},
            min_len=100,
            keyword="missing",
        )
        assert result["passed"] is False
        assert result["schema"] is False
        assert result["length"] is False
        assert result["keyword"] is False
