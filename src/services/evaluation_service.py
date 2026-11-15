"""Scores traces with rule-based checks and (if configured) an LLM judge."""

from typing import Any, Optional

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.sqlalchemy_models import Evaluation, Trace
from src.evaluators.judge_llm import JudgeLLM
from src.evaluators.rule_based_checks import RuleBasedChecks


class EvaluationRequest(BaseModel):
    """Optional overrides; by default values are read from the trace's root-span metadata."""

    output: Optional[str] = None
    reference: Optional[str] = None
    output_schema: Optional[dict[str, Any]] = Field(default=None, alias="schema")
    min_len: Optional[int] = Field(default=None, ge=0)
    max_len: Optional[int] = Field(default=None, ge=0)
    keyword: Optional[str] = None

    model_config = {"populate_by_name": True}


class EvaluationService:
    def __init__(self, session: AsyncSession, judge: JudgeLLM | None = None):
        self.session = session
        self.judge = judge or JudgeLLM()

    async def evaluate_trace(
        self,
        trace_id: str,
        request: EvaluationRequest | None = None,
        project_id: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        """Score a trace and persist the evaluation. Returns None if the trace doesn't exist."""
        stmt = select(Trace).where(Trace.trace_id == trace_id)
        if project_id:
            stmt = stmt.where(Trace.project_id == project_id)
        trace = (await self.session.execute(stmt)).scalar_one_or_none()
        if trace is None:
            return None

        req = request or EvaluationRequest()
        meta = trace.trace_metadata or {}
        output = req.output if req.output is not None else str(meta.get("output", ""))
        reference = req.reference if req.reference is not None else meta.get("reference")

        rule_result = RuleBasedChecks().check_all(
            output,
            schema=req.output_schema if req.output_schema is not None else meta.get("schema"),
            min_len=req.min_len if req.min_len is not None else meta.get("min_len", 0),
            max_len=req.max_len if req.max_len is not None else meta.get("max_len"),
            keyword=req.keyword if req.keyword is not None else meta.get("keyword"),
        )

        if self.judge.configured:
            judge_result = await self.judge.score(output, reference)
            quality = (judge_result["accuracy"] + judge_result["relevance"]) / 2
            score = 0.5 * float(rule_result["passed"]) + 0.5 * quality
            judge_name = "rule_based+llm_judge"
        else:
            judge_result = None
            score = float(rule_result["passed"])
            judge_name = "rule_based"

        failed = [k for k in ("schema", "length", "keyword") if not rule_result[k]]
        parts = [f"failed rule checks: {', '.join(failed)}"] if failed else []
        if judge_result and judge_result.get("rationale"):
            parts.append(judge_result["rationale"])
        rationale = "; ".join(parts) or "passed all checks"

        evaluation = Evaluation(
            trace_id=trace.id,
            judge=judge_name,
            score=round(score, 4),
            rationale=rationale,
            details={"rule_checks": rule_result, "judge": judge_result},
        )
        self.session.add(evaluation)
        await self.session.commit()

        return {
            "id": evaluation.id,
            "trace_id": trace_id,
            "judge": judge_name,
            "score": evaluation.score,
            "rationale": rationale,
            "rule_checks": rule_result,
            "llm_judge": judge_result,
        }
