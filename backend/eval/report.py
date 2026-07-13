"""Generate Markdown eval report."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger("eval.report")


def generate_markdown(results: dict[str, Any], output_path: str) -> str:
    """
    Nhận kết quả eval aggregated, xuất ra file Markdown.

    Args:
        results: Dict chứa layer1, layer2, layer3 results.
        output_path: Đường dẫn file .md để ghi.

    Returns:
        Nội dung Markdown.
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        f"# Eval Report — {now}",
        "",
    ]

    # ── Summary Table ──
    lines.append("## Summary")
    lines.append("")
    lines.append("| Metric | Score | Threshold | Status |")
    lines.append("|---|---|---|---|")

    summary = results.get("summary", {})
    for metric_name, info in summary.items():
        score = info.get("score", 0)
        threshold = info.get("threshold", 0)
        if isinstance(score, float):
            score_str = f"{score:.2f}"
        else:
            score_str = str(score)
        status = "✅ PASS" if info.get("passed", False) else "❌ FAIL"
        lines.append(f"| {metric_name} | {score_str} | ≥ {threshold} | {status} |")
    lines.append("")

    # ── Layer 1: Deterministic ──
    layer1 = results.get("layer1", {})
    if layer1:
        lines.append("---")
        lines.append("")
        lines.append("## Layer 1: Deterministic Tests")
        lines.append("")

        for test_name, test_result in layer1.items():
            passed_count = test_result.get("passed", 0)
            total_count = test_result.get("total", 0)
            lines.append(f"### {test_name} ({passed_count}/{total_count})")
            lines.append("")

            details = test_result.get("details", [])
            if details:
                lines.append("| # | Q&A | Expected | Got | Status |")
                lines.append("|---|---|---|---|---|")
                for d in details:
                    q = d.get("question", "")
                    ans = d.get("answer", None)
                    if ans is not None:
                        ans_escaped = str(ans).replace("\n", "<br>").replace("|", "\\|")
                        qa_md = f"**Q:** {q}<br>**A:** {ans_escaped}"
                    else:
                        qa_md = f"**Q:** {q}"
                    
                    exp = d.get("expected", "")
                    got = d.get("got", "")
                    st = "✅" if d.get("passed") else "❌"
                    lines.append(f"| {d.get('id', '')} | {qa_md} | {exp} | {got} | {st} |")
                lines.append("")

            failures = [d for d in details if not d.get("passed")]
            if failures:
                lines.append("**Failures:**")
                for f in failures:
                    lines.append(
                        f"- ❌ `{f.get('id', '')}`: Expected `{f.get('expected')}`, "
                        f"got `{f.get('got')}` — \"{f.get('question', '')[:80]}\""
                    )
                lines.append("")

    # ── Layer 2: LLM Judge ──
    layer2 = results.get("layer2", {})
    if layer2:
        lines.append("---")
        lines.append("")
        lines.append("## Layer 2: LLM-as-Judge")
        lines.append("")

        # Aggregate scores
        agg = layer2.get("aggregate", {})
        if agg:
            lines.append("### Aggregate Scores")
            lines.append("")
            lines.append("| Metric | Mean | Min | Threshold |")
            lines.append("|---|---|---|---|")
            for metric, stats in agg.items():
                mean = stats.get("mean", 0)
                mn = stats.get("min", 0)
                thr = stats.get("threshold", 0)
                lines.append(f"| {metric} | {mean:.2f} | {mn:.2f} | ≥ {thr} |")
            lines.append("")

        # Per-case details
        per_case = layer2.get("per_case", [])
        if per_case:
            lines.append("### Per-case Details")
            lines.append("")
            lines.append("| Case ID | Q&A | Faithfulness | Relevancy | Tone | Avg |")
            lines.append("|---|---|---|---|---|---|")
            for pc in per_case:
                q = pc.get("question", "")
                ans = pc.get("answer", "")
                ans_escaped = ans.replace("\n", "<br>").replace("|", "\\|")
                qa_md = f"**Q:** {q}<br>**A:** {ans_escaped}"
                
                scores = pc.get("scores", {})
                faith = scores.get("faithfulness", "—")
                rel = scores.get("relevancy", "—")
                tone = scores.get("tone_compliance", "—")
                avg = pc.get("avg_score", 0)
                if isinstance(faith, float):
                    faith = f"{faith:.2f}"
                if isinstance(rel, float):
                    rel = f"{rel:.2f}"
                if isinstance(tone, float):
                    tone = f"{tone:.2f}"
                lines.append(
                    f"| {pc.get('case_id', '')} | {qa_md} | {faith} | {rel} | {tone} | {avg:.2f} |"
                )
            lines.append("")

    # ── Layer 3: E2E Scenarios ──
    layer3 = results.get("layer3", {})
    if layer3:
        lines.append("---")
        lines.append("")
        lines.append("## Layer 3: End-to-End Scenarios")
        lines.append("")
        lines.append("| Case ID | Status | Question & Response |")
        lines.append("|---|---|---|")

        for scenario_id, scenario_result in layer3.items():
            status = "✅ PASS" if scenario_result.get("passed") else "❌ FAIL"
            question = scenario_result.get("question", "")
            
            violations_md = ""
            if scenario_result.get("violations"):
                violations_md = "**Violations:**<br>" + "<br>".join([f"- {v}" for v in scenario_result["violations"]]) + "<br><br>"
            
            full_resp = scenario_result.get("full_response", scenario_result.get("response_preview", ""))
            full_resp_escaped = full_resp.replace("\n", "<br>").replace("|", "\\|")
            
            qa_md = f"**Q:** {question}<br><br>{violations_md}**A:** {full_resp_escaped}"
            
            lines.append(f"| {scenario_id} | {status} | {qa_md} |")
        lines.append("")

    # ── Write to file ──
    content = "\n".join(lines)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    logger.info("[REPORT] Written to %s (%d lines)", output_path, len(lines))
    return content
