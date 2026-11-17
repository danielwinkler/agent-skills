# Blame Me assessment rubric

## Per-question quality scale (integers or halves, 0-4)

| Score | Anchored interpretation |
|---|---|
| 0 | Cannot explain, skips, or fundamentally wrong about behavior |
| 1 | Recognizes a surface detail but misses main mechanism/purpose |
| 2 | Understands the main idea but materially misses an important step, edge case, or effect |
| 3 | Correct and practical explanation of main behavior/mechanism; minor omission |
| 4 | Accurate causal explanation including relevant rationale, tradeoff, or non-obvious edge case |

Use the same anchored scale for all three categories; don't require exact identifier names. In a code trace question, being wrong about observable behavior is a material error. A sophisticated explanation based on imagined code is not correct. Only score claims supported by fetched code and context. If source truth is uncertain, discard the question rather than grade speculation.

## Category-normalized score

- Default weights: intent = 0.30, implementation = 0.40, code = 0.30.
- Let `mean_c = sum(question_scores_in_c) / (4 * count_c)` for a category with questions.
- Let `W` be the sum of default weights for categories with at least one valid answered/skipped question.
- **Final /100 = round(100 * sum(weight_c * mean_c for valid categories) / W, 1)**.
- Example: intent scores [4, 3], implementation [3, 2], code [1] => intent .875, implementation .625, code .25 -> **58.8/100** (26.25 + 25 + 7.5).
- If no code question was warranted, intent/implementation reweight to 3/7 and 4/7 (not a zero in code).
- A *skipped* evidence-backed question scores zero. A broken/unsupported question is removed entirely. An interrupted session is marked partial; indicate attempted and planned counts.
- Scores are comparable **within repeated runs of this same instrument only with caution**; difficulty and selected PRs vary. Never equate this with job performance or automatically infer authorship/AI reliance.

## Scope and calibration

Always state `X/Y merged PRs quizzed`, `Z merged PRs summarized`, `N open PRs summarized`, and repository count + names. When too many PRs exist to quiz each, select diverse work with higher technical risks, not solely the easiest or newest. Be candid about incomplete coverage. A report can legitimately have score 100 and low coverage.

**Optional confidence:** If the developer supplied high/medium/low with answers, show a descriptive calibration note (e.g. high-confidence mistakes). Do not change score based on confidence. Don't add extra questions merely to collect it.

**Interpretive bands (descriptive only, not normative):** 90-100 strong recall, 75-89 working understanding, 50-74 revisit some changes, 0-49 substantial refresh needed. If only 1-2 questions are answerable, suppress the band as unreliable. Do not use alarming or shaming language; "Blame Me" is playful, not punitive.

## Evidence quality

Best: actual merged PR patch/commits, linked tests, PR rationale, review discussion. Secondary: PR description, issue link, prior project context. Never substitute LLM confidence for code evidence. Code snippet must be accurate and short, with enough context to make the question fair. Distinguish implementation in the final merged PR from an earlier overwritten commit. Don't grade on unverifiable expectations, hypothetical future work, or code outside the authorized scope.
