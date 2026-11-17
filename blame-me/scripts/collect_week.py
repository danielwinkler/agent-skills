#!/usr/bin/env python3
"""Read-only, repo-scoped GitHub PR collector for the Blame Me agent skill.

Requires the GitHub CLI (gh) authenticated to GitHub. No dependencies outside
Python's standard library. No GitHub mutations or repository code execution.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def run_gh(*args: str) -> str:
    cmd = ["gh", *args]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=180)
    except FileNotFoundError as exc:
        raise RuntimeError("GitHub CLI 'gh' is unavailable. Install/authenticate gh or use the GitHub connector fallback.") from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"GitHub CLI timed out while reading {args[0]}") from exc
    if proc.returncode:
        raise RuntimeError(f"GitHub read failed: {proc.stderr.strip() or 'unknown error'}")
    return proc.stdout


def gh_json(endpoint: str):
    return json.loads(run_gh("api", endpoint))


def gh_pages(endpoint: str, **query: str) -> list:
    """All paginated GitHub API items; search endpoint pages have an items array."""
    args = ["api", "--method", "GET", endpoint, "--paginate", "--slurp"]
    for key, value in query.items():
        args.extend(["-f", f"{key}={value}"])
    raw = json.loads(run_gh(*args))
    pages = raw if isinstance(raw, list) else [raw]
    output = []
    for page in pages:
        if isinstance(page, dict) and isinstance(page.get("items"), list):
            output.extend(page["items"])
        elif isinstance(page, list):
            output.extend(page)
        elif page is not None:
            raise RuntimeError(f"Unexpected GitHub response to {endpoint}")
    return output


def iso_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def window(now: datetime, zone: ZoneInfo, explicit_start: str | None = None) -> tuple[datetime, datetime]:
    if explicit_start:
        start_day = date.fromisoformat(explicit_start)
        if start_day.weekday() != 0:
            raise ValueError("--week-start must be a Monday in YYYY-MM-DD format")
    else:
        today = now.astimezone(zone).date()
        start_day = today - timedelta(days=today.weekday() + 7)
    start = datetime.combine(start_day, time.min, zone)
    end = datetime.combine(start_day + timedelta(days=7), time.min, zone)
    return start, end


def in_window(value: str | None, start: datetime, end: datetime) -> bool:
    stamp = iso_dt(value)
    return stamp is not None and start <= stamp.astimezone(start.tzinfo) < end


def match_own_commit(commit: dict, login: str, extra_emails: set[str]) -> bool:
    author = commit.get("author") or {}
    author_login = (author.get("login") or "").lower()
    email = ((commit.get("commit") or {}).get("author") or {}).get("email") or ""
    return author_login == login.lower() or email.lower() in extra_emails


def summarize_commit(commit: dict, repo: str, login: str, extra_emails: set[str]) -> dict:
    author = commit.get("author") or {}
    author_info = (commit.get("commit") or {}).get("author") or {}
    sha = commit.get("sha") or ""
    return {
        "sha": sha,
        "url": commit.get("html_url") or f"https://github.com/{repo}/commit/{sha}",
        "message": ((commit.get("commit") or {}).get("message") or "").split("\n")[0],
        "author_login": author.get("login"),
        "authored_at": author_info.get("date"),
        "owned": match_own_commit(commit, login, extra_emails),
    }


def candidate_numbers(repo: str, filter_query: str, start: datetime, end: datetime, max_candidates: int, coverage: list[str]) -> list[int]:
    # Wider UTC calendar-day search guards against local timezone boundaries.
    a = (start.astimezone(timezone.utc) - timedelta(days=1)).date().isoformat()
    b = (end.astimezone(timezone.utc) + timedelta(days=1)).date().isoformat()
    query = f"repo:{repo} is:pr {filter_query}"
    query += f" merged:>={a} merged:<={b}" if filter_query == "is:merged" else f" updated:>={a}"
    data = gh_pages("search/issues", q=query, per_page="100")
    if len(data) >= 1000:
        coverage.append(f"{repo}: GitHub search may be truncated at the 1,000-result ceiling for {filter_query}.")
    if len(data) > max_candidates:
        coverage.append(f"{repo}: examined only {max_candidates}/{len(data)} {filter_query} PR candidates; ownership coverage is incomplete.")
    return list(dict.fromkeys(row["number"] for row in data[:max_candidates] if row.get("number") is not None))


def collect_one(repo: str, login: str, extra_emails: set[str], start: datetime, end: datetime,
                max_candidates: int, max_files: int, patch_budget: int,
                include_patches: bool, coverage: list[str]) -> tuple[list[dict], list[dict]]:
    merged, ongoing = [], []
    for kind in ("is:merged", "is:open"):
        for number in candidate_numbers(repo, kind, start, end, max_candidates, coverage):
            pr = gh_json(f"repos/{repo}/pulls/{number}")
            actually_merged = pr.get("merged_at") is not None
            if kind == "is:merged" and not (actually_merged and in_window(pr.get("merged_at"), start, end)):
                continue
            if kind == "is:open" and pr.get("state") != "open":
                continue
            all_commits = gh_pages(f"repos/{repo}/pulls/{number}/commits?per_page=100")
            commits = [summarize_commit(c, repo, login, extra_emails) for c in all_commits]
            owned_commits = [c for c in commits if c["owned"]]
            owned_in_week = [c for c in owned_commits if in_window(c["authored_at"], start, end)]
            author_owned = ((pr.get("user") or {}).get("login") or "").lower() == login.lower()
            if kind == "is:merged" and not (author_owned or owned_commits):
                continue
            if kind == "is:open" and not (owned_in_week or (author_owned and in_window(pr.get("updated_at"), start, end))):
                continue

            files = []
            patches_truncated = False
            if include_patches:
                raw_files = gh_pages(f"repos/{repo}/pulls/{number}/files?per_page=100")
                patches_truncated = len(raw_files) > max_files
                remaining = patch_budget
                for f in raw_files[:max_files]:
                    filename = f.get("filename") or ""
                    # Keep metadata but avoid spending patch budget on generated/lock files.
                    is_low_signal = bool(re.search(r"(^|/)(dist|vendor|generated|build)/|(^|/)(package-lock\.json|yarn\.lock|pnpm-lock\.yaml)$", filename, re.I))
                    patch = "" if is_low_signal else (f.get("patch") or "")
                    sliced = patch[:max(0, remaining)]
                    if len(sliced) < len(patch):
                        patches_truncated = True
                    remaining -= len(sliced)
                    files.append({"path": filename, "status": f.get("status"),
                                  "additions": f.get("additions"), "deletions": f.get("deletions"),
                                  "patch": sliced, "patch_available": bool(patch),
                                  "patch_truncated": len(sliced) < len(patch)})
            if patches_truncated:
                coverage.append(f"{repo}#{number}: file patch context was truncated; fetch a target file before asking code-tracing questions.")
            record = {
                "repo": repo, "number": number,
                "url": pr.get("html_url") or f"https://github.com/{repo}/pull/{number}",
                "title": pr.get("title"), "body": (pr.get("body") or "")[:10000],
                "author_login": (pr.get("user") or {}).get("login"),
                "author_owned": author_owned, "merged_at": pr.get("merged_at"),
                "updated_at": pr.get("updated_at"), "state": pr.get("state"),
                "commits": commits, "own_commit_count": len(owned_commits),
                "own_week_commit_count": len(owned_in_week),
                "files": files, "patches_truncated": patches_truncated,
                "attribution": ("PR-authored; no matching commit identity (possible agent/bot commits)"
                                if author_owned and not owned_commits else "GitHub commit author matched"),
            }
            (merged if kind == "is:merged" else ongoing).append(record)
    return merged, ongoing


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", action="append", default=[], help="Repo in OWNER/NAME form, repeatable; defaults to current checkout")
    ap.add_argument("--login", help="GitHub login to quiz; defaults to authenticated gh account")
    ap.add_argument("--email", action="append", default=[], help="Optional extra author email identity, repeatable")
    ap.add_argument("--timezone", default="Europe/Vienna", help="IANA timezone (default Europe/Vienna)")
    ap.add_argument("--week-start", help="Monday YYYY-MM-DD, otherwise last completed week")
    ap.add_argument("--max-candidates", type=int, default=200, help="Maximum PR search candidates per repo and status")
    ap.add_argument("--max-files", type=int, default=70)
    ap.add_argument("--patch-budget", type=int, default=18000, help="Patch characters per eligible PR")
    ap.add_argument("--no-patches", action="store_true", help="Avoid collecting source patches")
    ap.add_argument("--output", help="Local JSON output path; else print JSON to stdout")
    args = ap.parse_args()
    if any(n < 1 for n in [args.max_candidates, args.max_files, args.patch_budget]):
        ap.error("candidate, file, and patch limits must be positive")
    try:
        zone = ZoneInfo(args.timezone)
    except ZoneInfoNotFoundError:
        ap.error(f"Unknown timezone: {args.timezone}")
    try:
        start, end = window(datetime.now(timezone.utc), zone, args.week_start)
        login = args.login or gh_json("user")["login"]
        repos = args.repo or [run_gh("repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner").strip()]
        repos = list(dict.fromkeys(repos))
        for repo in repos:
            if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
                ap.error(f"Invalid OWNER/NAME repository: {repo!r}")
        coverage = []
        merged, ongoing = [], []
        for repo in repos:
            m, o = collect_one(repo, login, {x.lower() for x in args.email}, start, end,
                               args.max_candidates, args.max_files, args.patch_budget,
                               not args.no_patches, coverage)
            merged.extend(m)
            ongoing.extend(o)
        merged.sort(key=lambda pr: pr["merged_at"] or "", reverse=True)
        ongoing.sort(key=lambda pr: pr["updated_at"] or "", reverse=True)
        result = {
            "meta": {
                "login": login, "repos": repos, "timezone": args.timezone,
                "start_inclusive": start.isoformat(), "end_exclusive": end.isoformat(),
                "collection_time": datetime.now(timezone.utc).isoformat(),
                "definition": "PRs merged during window, if authored by user or containing attributed user commits; open PRs with user commits or author-owned updates during window",
                "source": "authenticated gh API, read only",
            },
            "merged_prs": merged, "open_prs": ongoing,
            "coverage": {"partial": bool(coverage), "notes": sorted(set(coverage)),
                         "per_repo_scope": True,
                         "ownership_rule": "GitHub login or explicit author email; PR author ownership also included"},
            "counts": {"merged_prs": len(merged), "open_prs": len(ongoing),
                       "merged_own_commits": sum(p["own_commit_count"] for p in merged),
                       "open_week_own_commits": sum(p["own_week_commit_count"] for p in ongoing)},
        }
        encoded = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
        if args.output:
            dest = Path(args.output).expanduser()
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(encoded, encoding="utf-8")
            os.chmod(dest, 0o600)
            print(f"Saved read-only GitHub evidence: {dest}", file=sys.stderr)
            print(f"Merged: {len(merged)} PRs; open: {len(ongoing)} PRs; warnings: {len(coverage)}", file=sys.stderr)
        else:
            print(encoded, end="")
        return 0
    except (ValueError, RuntimeError, KeyError, json.JSONDecodeError) as exc:
        print(f"Blame Me collection failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
