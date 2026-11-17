# MirrorGate (agent skill)

A short Monday engineering recall check based on last week's merged GitHub PRs, plus a separate recap of ongoing open PRs.

## Install

See the [repository installation instructions](../README.md#install) to install with `npx skills` or copy the skill directory manually. For complete commit-attribution coverage, use the bundled authenticated GitHub CLI collector; an available GitHub connector provides a fallback.

## Start a session

> Use $mirror-gate on last week's changes. Check `org/backend` and `org/frontend`. Quiz me for at most 10 minutes, then give me my score and weekly digest.

If your agent has a working tree with a GitHub remote and an authenticated `gh` CLI, `--repo` can be omitted. Otherwise, provide one or more repo scopes. The first run needs GitHub login + authorized repo access. Nothing is posted back to GitHub.

## Optional direct collection

```bash
python scripts/collect_week.py --repo org/backend --repo org/frontend --output /tmp/mirror-gate-evidence.json
```

By default, date scope is the last completed calendar week Monday 00:00 to Monday 00:00 in Europe/Vienna. The command is read-only and writes JSON locally with restrictive permissions. It may contain private source patches; keep it private and delete when done.

For a week starting on another Monday:

```bash
python scripts/collect_week.py --repo org/backend --week-start 2026-11-09 --output /tmp/mirror-gate-evidence.json
```

## Score

Question answers receive 0-4 points. Final /100 is category-normalized: intent 30%, implementation 40%, code reasoning 30%, with missing categories renormalized rather than penalized. The final report states how many merged PRs were sampled and how many ongoing PRs were summarized.

## Remember progress and catch up

> Use $mirror-gate on last week's changes and enable local learning memory. Remember demonstrated strengths and gaps for future study.

Memory is optional and stays outside your repositories, by default in `${CODEX_HOME:-~/.codex}/mirror-gate-memory/<github-login>/learning.md`. You can choose another local location. It retains a compact profile of your stated goals and preferences, dated topic evidence, and assessment summaries. It does not store raw source patches or full answers. The agent reports whether saving succeeded; filesystem access is required for persistence across sessions.

> Help me catch up on the gaps from my last examination. I have 15 minutes.

Catch-up uses the saved gaps to explain a concept, give focused practice, and check understanding with a fresh question. Assisted practice and independent understanding are recorded separately, and later progress does not rewrite the original exam score. You can ask to show or correct the profile, forget a topic, disable memory, or delete it.

## Limitations

A skill does **not** create its own Monday schedule; schedule a reminder or agent run separately. Repository scope and GitHub permissions determine coverage. GitHub commit attribution may miss agent or coauthor identities; author-owned PRs are still included but labeled appropriately. Collection and scoring are unit-tested offline; a live run against your repositories is not part of the installation package.
