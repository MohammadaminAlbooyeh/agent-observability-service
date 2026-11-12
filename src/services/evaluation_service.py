"""Runs LLM-as-judge scoring on completed traces."""

from typing import Any

from src.database.base import AsyncSessionLocal
from src.database.models.sqlalchemy_models import Evaluation, Trace
from src.evaluators.judge_llm import JudgeLLM
from src.evaluators.rule_based_checks import RuleBasedChecks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class EvaluationService:
    """Service for evaluating traces with an LLM judge and rule-based checks."""

    def __init__(self, session: AsyncSession | None = None):
        self._session = session

    async def _get_session(self) -> AsyncSession:
        if self._session is not None:
            return self._session
        return AsyncSessionLocal()

    async def evaluate_trace(self, trace_id: str) -> dict[str, Any]:
        """Score a completed trace using LLM judge and rule-based checks."""
        session = await self._get_session()
        result = await session.execute(
            select(Trace).where(Trace.trace_id == trace_id)
        )
        trace = result.scalar_one_or_none()
        if self._session is None:
            await session.close()
        if trace is None:
            return {"trace_id": trace_id, "score": 0.0, "rationale": "Trace not found"}

        checks = RuleBasedChecks()
        metadata = trace.trace_metadata or {}
        output = str(metadata.get("output", ""))
        reference = metadata.get("reference")

        rule_result = checks.check_all(
            output,
            schema=metadata.get("schema"),
            min_len=metadata.get("min_len", 0),
            keyword=metadata.get("keyword"),
        )

        judge = JudgeLLM()
        judge_result = await judge.score(output, reference)

        score = 0.0
        if rule_result["passed"]:
            score += 0.5
        score += 0.5 * judge_result.get("accuracy", 0.0)

        rationale_parts = []
        if not rule_result["passed"]:
            rationale_parts.append("rule-based checks failed")
        if judge_result.get("rationale"):
            rationale_parts.append(judge_result["rationale"])
        rationale = "; ".join(rationale_parts) if rationale_parts else "passed all checks"

        eval_record = Evaluation(
            trace_id=trace.id,
            judge="rule_based+llm_judge",
            score=round(score, 4),
            rationale=rationale,
        )
        session = await self._get_session()
        session.add(eval_record)
        await session.commit()
        if self._session is None:
            await session.close()

        return {
            "trace_id": trace_id,
            "score": round(score, 4),
            "rationale": rationale,
            "rule_checks": rule_result,
            "judge": judge_result,
        }
