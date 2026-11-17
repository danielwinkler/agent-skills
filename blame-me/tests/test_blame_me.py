"""Offline smoke tests for deterministic collection and grading."""
import importlib.util
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parents[1] / "scripts"

def load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

collector = load("collect_week")
grader = load("grade")

class BlameMeTests(unittest.TestCase):
    def test_previous_monday_week_and_dst(self):
        zone = ZoneInfo("Europe/Vienna")
        start, end = collector.window(datetime(2026, 11, 16, 20, tzinfo=timezone.utc), zone)
        self.assertEqual(start.isoformat(), "2026-11-09T00:00:00+01:00")
        self.assertEqual(end.isoformat(), "2026-11-16T00:00:00+01:00")
        self.assertTrue(collector.in_window("2026-11-15T22:59:59Z", start, end))
        self.assertFalse(collector.in_window("2026-11-15T23:00:00Z", start, end))
        dst_start, dst_end = collector.window(datetime(2026, 4, 6, 12, tzinfo=timezone.utc), zone)
        self.assertEqual(dst_start.utcoffset().total_seconds(), 7200)
        self.assertEqual(dst_end.utcoffset().total_seconds(), 7200)

    def test_grading_default(self):
        result = grader.calculate({"questions": [
            {"category": "intent", "score": 4}, {"category": "intent", "score": 3},
            {"category": "implementation", "score": 3}, {"category": "implementation", "score": 2},
            {"category": "code", "score": 1},
        ]})
        self.assertEqual(result["score"], 58.8)
        self.assertEqual(result["status"], "graded")

    def test_code_n_a_renormalizes(self):
        result = grader.calculate({"questions": [
            {"category": "intent", "score": 4},
            {"category": "implementation", "score": 2},
        ]})
        self.assertEqual(result["score"], 71.4)
        self.assertNotIn("code", result["categories"])

    def test_empty_and_partial(self):
        self.assertIsNone(grader.calculate({"questions": []})["score"])
        result = grader.calculate({"questions": [{"category": "code", "score": 3}], "planned_questions": 7})
        self.assertEqual(result["score"], 75)
        self.assertEqual(result["status"], "partial")

    def test_commit_authorship_vs_pr_author(self):
        commit = {"author": {"login": "automation-bot"},
                  "commit": {"author": {"email": "automation@example.org", "date": "2026-11-10T08:00:00Z"}}}
        self.assertFalse(collector.match_own_commit(commit, "developer", set()))
        self.assertTrue(collector.match_own_commit(commit, "developer", {"automation@example.org"}))

    def test_merged_and_open_inclusion(self):
        start, end = collector.window(datetime(2026, 11, 16, tzinfo=timezone.utc), ZoneInfo("Europe/Vienna"))
        original_candidate = collector.candidate_numbers
        original_json = collector.gh_json
        original_pages = collector.gh_pages
        prs = {
            1: {"number": 1, "state": "closed", "merged_at": "2026-11-12T12:00:00Z", "updated_at": "2026-11-12T12:00:00Z", "user": {"login": "developer"}, "title": "agent-authored"},
            2: {"number": 2, "state": "closed", "merged_at": "2026-11-13T12:00:00Z", "updated_at": "2026-11-13T12:00:00Z", "user": {"login": "colleague"}, "title": "collaboration"},
            3: {"number": 3, "state": "open", "merged_at": None, "updated_at": "2026-11-14T12:00:00Z", "user": {"login": "developer"}, "title": "wip"},
        }
        def commit(login, sha):
            return {"sha": sha, "author": {"login": login}, "commit": {"message": "test", "author": {"date": "2026-11-11T12:00:00Z"}}}
        commits = {1: [commit("automation-bot", "a")], 2: [commit("developer", "b")], 3: [commit("developer", "c")]}
        try:
            collector.candidate_numbers = lambda repo, kind, *_args: [1, 2] if kind == "is:merged" else [3]
            collector.gh_json = lambda endpoint: prs[int(endpoint.split("/")[-1])]
            collector.gh_pages = lambda endpoint, **kwargs: commits[int(endpoint.split("/")[4].split("?")[0])]
            merged, opened = collector.collect_one("org/repo", "developer", set(), start, end, 10, 10, 100, False, [])
            self.assertEqual(len(merged), 2)
            self.assertTrue(merged[0]["author_owned"])
            self.assertEqual(merged[0]["own_commit_count"], 0)
            self.assertEqual(merged[1]["own_commit_count"], 1)
            self.assertEqual(len(opened), 1)
            self.assertEqual(opened[0]["own_week_commit_count"], 1)
        finally:
            collector.candidate_numbers = original_candidate
            collector.gh_json = original_json
            collector.gh_pages = original_pages

if __name__ == "__main__":
    unittest.main()
