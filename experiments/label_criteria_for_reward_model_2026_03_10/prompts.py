from __future__ import annotations

CRITERIA_RUBRIC = """You are an expert rater labeling a single MIRROR text against six Stage-1 reward-model criteria.

Return ONLY valid JSON (no markdown, no prose) with exactly these keys:
- political_us
- opinion_not_news
- complete
- self_contained
- target_topic
- clear_political_stance

Each value must be an integer 0 or 1.

Criteria definitions (binary):
1. political_us: the mirror expresses a political viewpoint and specifically concerns US politics rather than international politics.
2. opinion_not_news: the mirror is an opinion or stance, not a news headline, factual report, ad, or product promotion.
3. complete: the mirror is a complete, coherent response and not obviously truncated.
4. self_contained: the mirror can be understood without extra missing context.
5. target_topic: the mirror addresses at least one target topic: abortion, climate change, immigration, or gun control.
6. clear_political_stance: the mirror has a clear left or right lean, not neutral or unclear.
"""


def build_stage1_criteria_prompt(*, original_text: str, mirror_text: str) -> str:
    original = (original_text or "").strip()
    mirror = (mirror_text or "").strip()
    return (
        CRITERIA_RUBRIC
        + "\nORIGINAL POST:\n"
        + original
        + "\n\nMIRROR:\n"
        + mirror
    )

