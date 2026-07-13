"""LLM-as-Judge — chấm chất lượng câu trả lời chatbot."""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from core.llm.base import BaseLLMClient

logger = logging.getLogger("eval.judge")


@dataclass
class JudgeScore:
    metric: str
    score: float
    reason: str


@dataclass
class JudgeResult:
    case_id: str
    scores: list[JudgeScore] = field(default_factory=list)

    @property
    def avg_score(self) -> float:
        if not self.scores:
            return 0.0
        return sum(s.score for s in self.scores) / len(self.scores)

    def to_dict(self) -> dict:
        return {
            "case_id": self.case_id,
            "avg_score": round(self.avg_score, 3),
            "scores": [
                {"metric": s.metric, "score": s.score, "reason": s.reason}
                for s in self.scores
            ],
        }


FAITHFULNESS_PROMPT = """Bạn là expert đánh giá chất lượng chatbot tài chính vàng.

QUESTION: {question}

CONTEXT (dữ liệu thật từ hệ thống):
{context}

ANSWER (câu trả lời của chatbot):
{answer}

Chấm điểm Faithfulness từ 0.0 đến 1.0:
- 1.0: Mọi claim trong ANSWER đều có căn cứ từ CONTEXT. Số liệu khớp.
- 0.7: Phần lớn đúng, có vài chỗ diễn giải hơi rộng nhưng không sai.
- 0.5: Một số claim không có căn cứ nhưng không mâu thuẫn.
- 0.0: ANSWER bịa số liệu hoặc mâu thuẫn rõ ràng với CONTEXT.

Trả về ĐÚNG JSON (không giải thích thêm):
{{"score": <float 0.0-1.0>, "reason": "<giải thích ngắn gọn>"}}"""

RELEVANCY_PROMPT = """Bạn là expert đánh giá chất lượng chatbot tài chính vàng.

QUESTION: {question}

ANSWER (câu trả lời của chatbot):
{answer}

Chấm điểm Answer Relevancy từ 0.0 đến 1.0:
- 1.0: ANSWER trả lời đúng trọng tâm câu hỏi, đầy đủ thông tin cần thiết.
- 0.7: Trả lời đúng hướng nhưng thiếu một số thông tin quan trọng.
- 0.5: Trả lời liên quan nhưng lạc trọng tâm hoặc quá chung chung.
- 0.0: ANSWER hoàn toàn không liên quan đến câu hỏi.

Trả về ĐÚNG JSON (không giải thích thêm):
{{"score": <float 0.0-1.0>, "reason": "<giải thích ngắn gọn>"}}"""

TONE_PROMPT = """Bạn là expert đánh giá chất lượng chatbot tài chính vàng.

ANSWER (câu trả lời của chatbot):
{answer}

Chấm điểm Tone Compliance từ 0.0 đến 1.0:
- 1.0: Giọng phân tích khách quan, chuyên nghiệp. Không khuyên mua/bán. Có disclaimer nếu cần.
- 0.7: Phần lớn khách quan nhưng có vài câu hơi thiên lệch (bullish/bearish quá mức).
- 0.5: Có lời khuyên gián tiếp hoặc giọng điệu không phù hợp.
- 0.0: Khuyên mua/bán trực tiếp hoặc giọng điệu thiếu chuyên nghiệp.

Trả về ĐÚNG JSON (không giải thích thêm):
{{"score": <float 0.0-1.0>, "reason": "<giải thích ngắn gọn>"}}"""


def _parse_judge_response(raw: str) -> dict:
    """Parse JSON từ LLM judge response, xử lý cả trường hợp model trả thêm text."""
    # Thử parse trực tiếp
    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError:
        pass

    # Tìm JSON trong text
    match = re.search(r'\{[^{}]*"score"\s*:\s*[\d.]+[^{}]*\}', raw)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    logger.warning("Could not parse judge response: %s", raw[:200])
    return {"score": 0.0, "reason": f"Parse error: {raw[:100]}"}


class LLMJudge:
    """Dùng LLM hiện tại để chấm chất lượng câu trả lời."""

    def __init__(self, llm_client: BaseLLMClient):
        self.llm = llm_client

    def _call_judge(self, prompt: str) -> dict:
        try:
            raw = self.llm.generate([{"role": "user", "content": prompt}])
            return _parse_judge_response(raw)
        except Exception as e:
            logger.error("Judge LLM call failed: %s", e)
            return {"score": 0.0, "reason": f"LLM error: {e}"}

    def score_faithfulness(self, question: str, answer: str, context: str) -> JudgeScore:
        prompt = FAITHFULNESS_PROMPT.format(
            question=question, context=context[:3000], answer=answer[:2000]
        )
        result = self._call_judge(prompt)
        return JudgeScore(
            metric="faithfulness",
            score=min(1.0, max(0.0, float(result.get("score", 0)))),
            reason=result.get("reason", ""),
        )

    def score_relevancy(self, question: str, answer: str) -> JudgeScore:
        prompt = RELEVANCY_PROMPT.format(question=question, answer=answer[:2000])
        result = self._call_judge(prompt)
        return JudgeScore(
            metric="relevancy",
            score=min(1.0, max(0.0, float(result.get("score", 0)))),
            reason=result.get("reason", ""),
        )

    def score_tone_compliance(self, answer: str) -> JudgeScore:
        prompt = TONE_PROMPT.format(answer=answer[:2000])
        result = self._call_judge(prompt)
        return JudgeScore(
            metric="tone_compliance",
            score=min(1.0, max(0.0, float(result.get("score", 0)))),
            reason=result.get("reason", ""),
        )

    def judge_case(
        self,
        case_id: str,
        question: str,
        answer: str,
        context_str: str = "",
        run_metrics: list[str] | None = None,
    ) -> JudgeResult:
        """Chạy tất cả metric cho 1 case."""
        metrics = run_metrics or ["faithfulness", "relevancy", "tone_compliance"]
        result = JudgeResult(case_id=case_id)

        if "faithfulness" in metrics and context_str:
            result.scores.append(
                self.score_faithfulness(question, answer, context_str)
            )
        if "relevancy" in metrics:
            result.scores.append(self.score_relevancy(question, answer))
        if "tone_compliance" in metrics:
            result.scores.append(self.score_tone_compliance(answer))

        logger.info(
            "[JUDGE] %s: avg=%.2f scores=%s",
            case_id,
            result.avg_score,
            [(s.metric, s.score) for s in result.scores],
        )
        return result
