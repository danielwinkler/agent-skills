#!/usr/bin/env python3
"""Compute the deterministic normalized MirrorGate comprehension score.

Input JSON: {"questions": [{"category": "intent", "score": 3.5}, ...],
             "planned_questions": 7}.
Invalid/unanswerable questions must be omitted, not scored zero.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

WEIGHTS = {"intent": 0.30, "implementation": 0.40, "code": 0.30}


def calculate(data: dict) -> dict:
    questions = data.get("questions", [])
    if not isinstance(questions, list):
        raise ValueError("questions must be an array")
    categories = defaultdict(list)
    for i, q in enumerate(questions, start=1):
        category = q.get("category")
        score = q.get("score")
        if category not in WEIGHTS:
            raise ValueError(f"Question {i}: category must be intent/implementation/code")
        if isinstance(score, bool) or not isinstance(score, (int, float)) or not 0 <= score <= 4:
            raise ValueError(f"Question {i}: score must be a number in [0,4]")
        categories[category].append(float(score))
    planned = data.get("planned_questions", len(questions))
    if not isinstance(planned, int) or planned < len(questions):
        raise ValueError("planned_questions must be an integer >= number of scored questions")
    if not questions:
        return {"score": None, "status": "not_graded", "answered_questions": 0,
                "planned_questions": planned, "categories": {}}
    weight_total = sum(WEIGHTS[c] for c in categories)
    ratios = {c: sum(scores) / (4 * len(scores)) for c, scores in categories.items()}
    overall = 100 * sum(ratios[c] * WEIGHTS[c] for c in categories) / weight_total
    category_summary = {c: {"score": round(100 * ratios[c], 1), "questions": len(categories[c]),
                            "normalized_weight": round(WEIGHTS[c] / weight_total, 4)}
                        for c in WEIGHTS if c in categories}
    status = "partial" if planned > len(questions) else ("narrow" if len(questions) < 3 else "graded")
    return {"score": round(overall, 1), "status": status,
            "answered_questions": len(questions), "planned_questions": planned,
            "categories": category_summary}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("path", type=Path, help="JSON file with category + score per question")
    args = ap.parse_args()
    print(json.dumps(calculate(json.loads(args.path.read_text(encoding="utf-8"))), indent=2))


if __name__ == "__main__":
    main()
