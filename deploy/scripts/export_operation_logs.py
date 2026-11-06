#!/usr/bin/env python3
"""Download operation logs and save them under exports/ with survey CSVs.

Usage:
  source deploy/.env.aws
  python3 deploy/scripts/export_operation_logs.py              # download from production
  python3 deploy/scripts/export_operation_logs.py --zip a.zip  # use an already downloaded zip

Writes exports/operation-logs-<date>/, exports/operation-logs-<date>.zip,
exports/intent-surveys-<date>.csv and exports/post-surveys-<date>.csv.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import sys
import urllib.request
import zipfile
from datetime import date
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_URL = "https://play.adaptation-game.com/api/admin/operation-logs.zip"

INTENT_COLUMNS = [
    "session_id", "user_name", "team_name", "client_started_at", "cycle", "year_range",
    "submitted_at", "version", "target_objectives", "free_text", "sliders",
]
# play_count was added in post survey version 9; it stays empty for older answers.
POST_COLUMNS = [
    "session_id", "user_name", "team_name", "client_started_at", "submitted_at", "version",
    "age_decade", "play_count", "prior_climate_adaptation_knowledge",
    "prior_basin_flood_management_knowledge", "understood_policy_effects",
    "adaptation_can_reduce_disaster", "game_impression", "priority_indicators",
    "what_learned", "learning_free_text", "other_comments", "research_focus",
]


def _cell(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return value


def _session_fields(session: dict[str, Any]) -> dict[str, Any]:
    return {
        "session_id": session.get("session_id"),
        "user_name": session.get("user_name"),
        "team_name": session.get("team_name"),
        "client_started_at": session.get("client_started_at"),
    }


def build_rows(log_dir: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    intent_rows: list[dict[str, Any]] = []
    post_rows: list[dict[str, Any]] = []
    for path in sorted(log_dir.glob("*.json")):
        try:
            log = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"[WARN] Skipped unreadable {path.name}: {exc}", file=sys.stderr)
            continue
        session = log.get("session")
        if not session:
            # e.g. deploy-smoke-test.json
            continue
        base = _session_fields(session)

        for intent in log.get("intent_surveys") or []:
            answers = intent.get("answers") or {}
            intent_rows.append({
                **base,
                "cycle": intent.get("cycle"),
                "year_range": intent.get("year_range"),
                "submitted_at": intent.get("submitted_at"),
                "version": intent.get("version"),
                "target_objectives": answers.get("target_objectives"),
                "free_text": answers.get("free_text"),
                "sliders": intent.get("sliders"),
            })

        survey = log.get("survey")
        if survey:
            answers = survey.get("answers") or {}
            post_rows.append({
                **base,
                **{key: answers.get(key) for key in POST_COLUMNS if key in answers},
                "submitted_at": survey.get("submitted_at"),
                "version": survey.get("version"),
                "research_focus": survey.get("research_focus"),
            })
    return intent_rows, post_rows


def write_csv(path: Path, columns: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_NONNUMERIC, lineterminator="\n")
        writer.writerow(columns)
        for row in rows:
            writer.writerow([_cell(row.get(column)) for column in columns])


def download_zip(url: str, token: str, dest: Path) -> None:
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(request, timeout=120) as response, dest.open("wb") as f:
        shutil.copyfileobj(response, f)


def main() -> int:
    parser = argparse.ArgumentParser(description="Save operation logs and survey CSVs under exports/")
    parser.add_argument("--zip", type=Path, help="use this zip instead of downloading")
    parser.add_argument("--date", default=date.today().isoformat(), help="suffix, default today")
    parser.add_argument("--out", type=Path, default=ROOT_DIR / "exports")
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--force", action="store_true", help="overwrite existing outputs")
    args = parser.parse_args()

    out_dir: Path = args.out
    log_dir = out_dir / f"operation-logs-{args.date}"
    zip_path = out_dir / f"operation-logs-{args.date}.zip"
    intent_csv = out_dir / f"intent-surveys-{args.date}.csv"
    post_csv = out_dir / f"post-surveys-{args.date}.csv"

    existing = [p for p in (zip_path, intent_csv, post_csv) if p.exists()]
    if log_dir.exists() and any(log_dir.iterdir()):
        existing.append(log_dir)
    if existing and not args.force:
        print("Already exists (use --force to overwrite): " + ", ".join(map(str, existing)), file=sys.stderr)
        return 1

    out_dir.mkdir(parents=True, exist_ok=True)
    if args.zip:
        shutil.copyfile(args.zip, zip_path)
    else:
        token = (os.environ.get("ADMIN_EXPORT_TOKEN") or "").strip()
        if not token:
            print("ADMIN_EXPORT_TOKEN is not set. Run: source deploy/.env.aws", file=sys.stderr)
            return 1
        download_zip(args.url, token, zip_path)

    if log_dir.exists():
        shutil.rmtree(log_dir)
    log_dir.mkdir()
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(log_dir)

    intent_rows, post_rows = build_rows(log_dir)
    write_csv(intent_csv, INTENT_COLUMNS, intent_rows)
    write_csv(post_csv, POST_COLUMNS, post_rows)

    log_count = len(list(log_dir.glob("*.json")))
    print(f"{log_dir}  ({log_count} files)")
    print(f"{zip_path}")
    print(f"{intent_csv}  ({len(intent_rows)} rows)")
    print(f"{post_csv}  ({len(post_rows)} rows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
