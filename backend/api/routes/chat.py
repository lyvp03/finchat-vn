import json
import logging
from typing import Dict, List

from fastapi import APIRouter
from pydantic import BaseModel, Field

from chatbot.orchestrator import answer_question
from core.llm.factory import get_llm_client

logger = logging.getLogger("chat_api")

router = APIRouter(prefix="/api", tags=["chat"])


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    history: List[Dict[str, str]] = Field(default_factory=list)


class EvalRequest(BaseModel):
    question: str = Field(..., min_length=1)
    answer: str = Field(..., min_length=1)


EVAL_SYSTEM_PROMPT = """Bạn là hệ thống chấm điểm câu trả lời tài chính.

Đánh giá output theo 5 tiêu chí:
1. Correctness - Độ chính xác của thông tin
2. Insight - Mức độ phân tích sâu, có giá trị
3. Clarity - Rõ ràng, dễ hiểu
4. Naturalness - Tự nhiên, giống con người
5. Conciseness - Ngắn gọn, súc tích

Chấm điểm từ 0–5 cho từng tiêu chí.

Trả về ĐÚNG JSON (không markdown, không giải thích):
{
  "correctness": ...,
  "insight": ...,
  "clarity": ...,
  "naturalness": ...,
  "conciseness": ...,
  "final_score": ...
}

final_score = 0.3*correctness + 0.25*insight + 0.2*naturalness + 0.15*clarity + 0.1*conciseness

KHÔNG giải thích dài dòng. CHỈ trả về JSON."""


@router.post("/chat")
def chat(request: ChatRequest):
    return answer_question(request.message, history=request.history)


@router.post("/chat/evaluate")
def evaluate(request: EvalRequest):
    """Auto-eval câu trả lời chatbot bằng LLM judge."""
    messages = [
        {"role": "system", "content": EVAL_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Câu hỏi của người dùng:\n{request.question}\n\n"
                f"Câu trả lời của chatbot:\n{request.answer}"
            ),
        },
    ]

    try:
        raw = get_llm_client().generate(messages)
        # Strip markdown fences if present
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        scores = json.loads(cleaned)
        # Recalculate final_score to ensure correctness
        scores["final_score"] = round(
            0.3 * scores.get("correctness", 0)
            + 0.25 * scores.get("insight", 0)
            + 0.2 * scores.get("naturalness", 0)
            + 0.15 * scores.get("clarity", 0)
            + 0.1 * scores.get("conciseness", 0),
            2,
        )
        return {"ok": True, "scores": scores}
    except json.JSONDecodeError as e:
        logger.error("Eval JSON parse error: %s | raw: %s", e, raw[:200])
        return {"ok": False, "error": "LLM returned invalid JSON", "raw": raw[:300]}
    except Exception as e:
        logger.error("Eval failed: %s", e)
        return {"ok": False, "error": str(e)}
