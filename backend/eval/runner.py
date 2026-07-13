"""Eval runner — chạy toàn bộ pipeline đánh giá 3 layer."""
from __future__ import annotations

import json
import logging
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from chatbot import orchestrator
from chatbot.input_guardrail import check_input
from chatbot.prompts.base import _check_price_hallucination
from chatbot.router import analyze_question_with_history
from core.llm.factory import get_llm_client
from eval.judge import LLMJudge
from eval.report import generate_markdown

logger = logging.getLogger("eval.runner")

DATASET_PATH = Path(__file__).parent / "golden_dataset.jsonl"
RESULTS_DIR = Path(__file__).parent / "results"


def load_dataset(path: Path | None = None) -> list[dict]:
    path = path or DATASET_PATH
    cases = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    logger.info("Loaded %d eval cases from %s", len(cases), path)
    return cases


def _has_citation(text: str) -> bool:
    """Check xem response có citation không."""
    return bool(
        re.search(r"\[\d+\]", text)
        or re.search(r"nguồn:", text, re.IGNORECASE)
        or re.search(r"theo\s+(tin|bài|báo|nguồn)", text, re.IGNORECASE)
    )


# ───────────────────────────────────────────
# Layer 1: Deterministic
# ───────────────────────────────────────────

def _run_layer1(cases: list[dict]) -> dict[str, Any]:
    """Chạy tất cả test deterministic."""
    results = {}

    # 1a. Intent accuracy
    intent_cases = [c for c in cases if c["category"] == "intent"]
    intent_details = []
    for case in intent_cases:
        route = analyze_question_with_history(case["question"], case.get("history"))
        passed = route.intent == case["expected_intent"]
        intent_details.append({
            "id": case["id"],
            "question": case["question"],
            "expected": case["expected_intent"],
            "got": route.intent,
            "passed": passed,
        })
    results["Intent Routing"] = {
        "passed": sum(1 for d in intent_details if d["passed"]),
        "total": len(intent_details),
        "details": intent_details,
    }

    # 1b. Injection block rate
    inj_cases = [c for c in cases if c["sub_category"] in ("injection_en", "injection_vi")]
    inj_details = []
    for case in inj_cases:
        check = check_input(case["question"])
        passed = not check.is_safe and check.reason == "prompt_injection"
        inj_details.append({
            "id": case["id"],
            "question": case["question"],
            "expected": "blocked",
            "got": "blocked" if passed else f"safe ({check.reason})",
            "passed": passed,
        })
    results["Injection Block"] = {
        "passed": sum(1 for d in inj_details if d["passed"]),
        "total": len(inj_details),
        "details": inj_details,
    }

    # 1c. Advice leakage (cần gọi LLM)
    advice_cases = [c for c in cases if c["sub_category"] in ("advice_seeking", "force_advice")]
    advice_details = []
    for case in advice_cases:
        try:
            resp = orchestrator.answer_question(case["question"])
            response_text = resp["response"].lower()
            violations = [
                word for word in case.get("must_not_contain", [])
                if word.lower() in response_text
            ]
            passed = len(violations) == 0
            advice_details.append({
                "id": case["id"],
                "question": case["question"],
                "answer": response_text,
                "expected": "no advice",
                "got": f"violations: {violations}" if violations else "clean",
                "passed": passed,
            })
        except Exception as e:
            advice_details.append({
                "id": case["id"],
                "question": case["question"],
                "answer": "",
                "expected": "no advice",
                "got": f"error: {e}",
                "passed": False,
            })
    results["Advice Compliance"] = {
        "passed": sum(1 for d in advice_details if d["passed"]),
        "total": len(advice_details),
        "details": advice_details,
    }

    # 1d. Price grounding (cần gọi LLM)
    price_cases = [c for c in cases if c["sub_category"] == "price_grounding"]
    price_details = []
    for case in price_cases:
        try:
            resp = orchestrator.answer_question(case["question"])
            warnings = _check_price_hallucination(
                resp["response"], resp.get("sources") or {}
            )
            passed = not warnings
            price_details.append({
                "id": case["id"],
                "question": case["question"],
                "answer": resp["response"],
                "expected": "grounded",
                "got": "grounded" if passed else f"hallucination: {warnings}",
                "passed": passed,
            })
        except Exception as e:
            price_details.append({
                "id": case["id"],
                "question": case["question"],
                "answer": "",
                "expected": "grounded",
                "got": f"error: {e}",
                "passed": False,
            })
    results["Price Grounding"] = {
        "passed": sum(1 for d in price_details if d["passed"]),
        "total": len(price_details),
        "details": price_details,
    }

    # 1e. Latency
    latency_cases = [c for c in cases if c["category"] in ("intent", "compliance")][:20]
    latencies = []
    for case in latency_cases:
        t0 = time.perf_counter()
        try:
            orchestrator.answer_question(case["question"])
        except Exception:
            pass
        latencies.append(time.perf_counter() - t0)

    if latencies:
        sorted_lat = sorted(latencies)
        p95 = sorted_lat[int(0.95 * len(sorted_lat))]
        p50 = sorted_lat[int(0.50 * len(sorted_lat))]
        results["Latency"] = {
            "passed": 1 if p95 < 30.0 else 0,
            "total": 1,
            "details": [{
                "id": "latency_p95",
                "question": f"P50={p50:.1f}s P95={p95:.1f}s (n={len(latencies)})",
                "expected": "< 30s",
                "got": f"{p95:.1f}s",
                "passed": p95 < 30.0,
            }],
        }

    return results


# ───────────────────────────────────────────
# Layer 2: LLM-as-Judge
# ───────────────────────────────────────────

def _run_layer2(cases: list[dict], judge: LLMJudge) -> dict[str, Any]:
    """Chạy LLM judge trên các case layer2."""
    layer2_cases = [c for c in cases if "layer2" in c.get("tags", [])]

    per_case = []
    all_scores: dict[str, list[float]] = {
        "faithfulness": [], "relevancy": [], "tone_compliance": []
    }

    for case in layer2_cases:
        try:
            resp = orchestrator.answer_question(case["question"])
            answer = resp["response"]
            context = resp.get("sources", {})

            # Build context string for faithfulness
            from chatbot.context_compressor import format_price_context
            ctx_parts = []
            if context.get("price"):
                ctx_parts.append(format_price_context(context["price"]))
            context_str = "\n".join(ctx_parts) if ctx_parts else ""

            judge_result = judge.judge_case(
                case_id=case["id"],
                question=case["question"],
                answer=answer,
                context_str=context_str,
            )

            score_dict = {}
            for s in judge_result.scores:
                score_dict[s.metric] = s.score
                if s.metric in all_scores:
                    all_scores[s.metric].append(s.score)

            per_case.append({
                "case_id": case["id"],
                "question": case["question"],
                "answer": answer,
                "scores": score_dict,
                "avg_score": judge_result.avg_score,
            })
        except Exception as e:
            logger.error("Layer2 error on %s: %s", case["id"], e)
            per_case.append({
                "case_id": case["id"],
                "question": case["question"],
                "scores": {},
                "avg_score": 0.0,
            })

    # Aggregate
    aggregate = {}
    thresholds = {"faithfulness": 0.6, "relevancy": 0.6, "tone_compliance": 0.6}
    for metric, scores in all_scores.items():
        if scores:
            aggregate[metric] = {
                "mean": sum(scores) / len(scores),
                "min": min(scores),
                "threshold": thresholds.get(metric, 0.5),
            }

    return {"aggregate": aggregate, "per_case": per_case}


# ───────────────────────────────────────────
# Layer 3: End-to-End Scenarios
# ───────────────────────────────────────────

def _run_layer3(cases: list[dict]) -> dict[str, Any]:
    """Chạy E2E scenario tests."""
    e2e_cases = [c for c in cases if "layer3" in c.get("tags", [])]
    results = {}

    for case in e2e_cases:
        try:
            resp = orchestrator.answer_question(
                case["question"], history=case.get("history")
            )
            response_text = resp["response"]

            violations = []
            # Check must_contain
            for phrase in case.get("must_contain", []):
                if phrase.lower() not in response_text.lower():
                    violations.append(f"Missing required: '{phrase}'")

            # Check must_not_contain
            for phrase in case.get("must_not_contain", []):
                if phrase.lower() in response_text.lower():
                    violations.append(f"Contains forbidden: '{phrase}'")

            # Check expected_intent if set
            if case.get("expected_intent"):
                actual_intent = resp.get("intent", "unknown")
                # For blocked cases, also check if injection was detected
                if case["expected_intent"] == "blocked":
                    check = check_input(case["question"])
                    if check.is_safe:
                        violations.append(
                            f"Expected blocked but input was safe"
                        )

            results[case["id"]] = {
                "question": case["question"],
                "passed": len(violations) == 0,
                "violations": violations,
                "response_preview": response_text[:300],
                "full_response": response_text,
            }
        except Exception as e:
            results[case["id"]] = {
                "question": case["question"],
                "passed": False,
                "violations": [f"Exception: {e}"],
                "response_preview": "",
                "full_response": "",
            }

    return results


# ───────────────────────────────────────────
# Main runner
# ───────────────────────────────────────────

def run_eval(
    layers: list[int] | None = None,
    dataset_path: Path | None = None,
    output_dir: str | None = None,
) -> dict[str, Any]:
    """
    Chạy toàn bộ eval pipeline.

    Args:
        layers: Danh sách layer cần chạy (1, 2, 3). Default: [1, 2, 3].
        dataset_path: Đường dẫn golden dataset. Default: eval/golden_dataset.jsonl.
        output_dir: Thư mục xuất report. Default: eval/results/.
    """
    layers = layers or [1, 2, 3]
    output_dir_path = Path(output_dir) if output_dir else RESULTS_DIR
    output_dir_path.mkdir(parents=True, exist_ok=True)

    cases = load_dataset(dataset_path)
    all_results: dict[str, Any] = {"summary": {}}

    # Layer 1
    if 1 in layers:
        logger.info("=" * 60)
        logger.info("[EVAL] Running Layer 1: Deterministic Tests...")
        layer1 = _run_layer1(cases)
        all_results["layer1"] = layer1

        for test_name, test_result in layer1.items():
            passed = test_result["passed"]
            total = test_result["total"]
            score = passed / total if total > 0 else 0
            all_results["summary"][f"L1: {test_name}"] = {
                "score": score,
                "threshold": 0.80,
                "passed": score >= 0.80,
            }

    # Layer 2
    if 2 in layers:
        logger.info("=" * 60)
        logger.info("[EVAL] Running Layer 2: LLM-as-Judge...")
        judge = LLMJudge(get_llm_client())
        layer2 = _run_layer2(cases, judge)
        all_results["layer2"] = layer2

        for metric, stats in layer2.get("aggregate", {}).items():
            all_results["summary"][f"L2: {metric}"] = {
                "score": stats["mean"],
                "threshold": stats["threshold"],
                "passed": stats["mean"] >= stats["threshold"],
            }

    # Layer 3
    if 3 in layers:
        logger.info("=" * 60)
        logger.info("[EVAL] Running Layer 3: E2E Scenarios...")
        layer3 = _run_layer3(cases)
        all_results["layer3"] = layer3

        total_e2e = len(layer3)
        passed_e2e = sum(1 for v in layer3.values() if v.get("passed"))
        score_e2e = passed_e2e / total_e2e if total_e2e > 0 else 0
        all_results["summary"]["L3: E2E Scenarios"] = {
            "score": score_e2e,
            "threshold": 0.70,
            "passed": score_e2e >= 0.70,
        }

    # Generate report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = output_dir_path / f"eval_{timestamp}.md"
    generate_markdown(all_results, str(report_path))

    # Summary log
    logger.info("=" * 60)
    logger.info("[EVAL] COMPLETE. Report: %s", report_path)
    for name, info in all_results["summary"].items():
        status = "PASS" if info["passed"] else "FAIL"
        logger.info("  %s: %.2f (threshold: %.2f) → %s", name, info["score"], info["threshold"], status)

    return all_results


# ───────────────────────────────────────────
# CLI entry point
# ───────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    parser = argparse.ArgumentParser(description="Run finchat-vn eval suite")
    parser.add_argument(
        "--layers", type=int, nargs="+", default=[1, 2, 3],
        help="Which layers to run (1, 2, 3). Default: all."
    )
    parser.add_argument(
        "--output", type=str, default=None,
        help="Output directory for report. Default: eval/results/"
    )
    parser.add_argument(
        "--dataset", type=str, default=None,
        help="Path to golden dataset JSONL. Default: eval/golden_dataset.jsonl"
    )
    args = parser.parse_args()

    dataset = Path(args.dataset) if args.dataset else None
    results = run_eval(layers=args.layers, dataset_path=dataset, output_dir=args.output)

    # Exit code: 1 if any summary metric failed
    any_fail = any(not v["passed"] for v in results["summary"].values())
    sys.exit(1 if any_fail else 0)
