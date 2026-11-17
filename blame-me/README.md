# Blame Me (agent skill)

A short Monday engineering recall check based on last week's merged GitHub PRs, plus a separate recap of ongoing open PRs.

## Install

Upload `skill.zip` as a custom agent skill in a Skills-compatible agent, or place the `blame-me/` directory in the agent's supported skills directory. The GitHub connector fallback works in ChatGPT when GitHub access is enabled, but for complete commit-attribution coverage use the bundled authenticated GitHub CLI collector.

## Start a session

> Blame me on last week's changes. Check `org/backend` and `org/frontend`. Quiz me for at most 10 minutes, then give me my score and weekly digest.

If your agent has a working tree with a GitHub remote and an authenticated `gh` CLI, `--repo` can be omitted. Otherwise, provide one or more repo scopes. The first run needs GitHub login + authorized repo access. Nothing is posted back to GitHub.

## Optional direct collection

```bash
python scripts/collect_week.py --repo org/backend --repo org/frontend --output /tmp/blame-me-evidence.json
```

By default, date scope is the last completed calendar week Monday 00:00 to Monday 00:00 in Europe/Vienna. The command is read-only and writes JSON locally with restrictive permissions. It may contain private source patches; keep it private and delete when done.

For a week starting on another Monday:

```bash
python scripts/collect_week.py --repo org/backend --week-start 2026-11-09 --output /tmp/blame-me-evidence.json
```

## Score

Question answers receive 0-4 points. Final /100 is category-normalized: intent 30%, implementation 40%, code reasoning 30%, with missing categories renormalized rather than penalized. The final report states how many merged PRs were sampled and how many ongoing PRs were summarized.

## Limitations

A skill does **not** create its own Monday schedule; schedule a reminder or agent run separately. Repository scope and GitHub permissions determine coverage. GitHub commit attribution may miss agent or coauthor identities; author-owned PRs are still included but labeled appropriately. Collection and scoring are unit-tested offline; a live run against your repositories is not part of the installation package.
