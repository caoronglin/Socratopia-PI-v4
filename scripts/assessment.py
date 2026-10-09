#!/usr/bin/env python3
"""Validate and report objective-aligned Socratopia v4 assessments."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.lib.assessment import quality_report, reteach_candidates, validate_objective  # noqa: E402
from scripts.lib.repository import course_dir, read_json_list, validate_course_name, write_json_atomic  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="课程评估质量检查")
    parser.add_argument("command", choices=["validate", "report", "reteach"])
    parser.add_argument("--course", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    validate_course_name(args.course)

    runtime = course_dir(ROOT, args.course) / "runtime"
    objectives = read_json_list(runtime / "objectives.json", "objectives")
    items = read_json_list(runtime / "assessment_items.json", "items")
    objective_ids = {str(r.get("id")) for r in objectives if r.get("id")}
    report = quality_report(items, objective_ids)
    report["objective_errors"] = {
        str(obj.get("id") or f"objective[{i}]"): validate_objective(obj)
        for i, obj in enumerate(objectives)
    }

    if args.command == "validate":
        errors = [e for errs in report["errors"].values() for e in errs]
        errors += [f"{key}: 缺少 {field}" for key, missing in report["objective_errors"].items() for field in missing]
        if not objectives or not items:
            errors.append("学习目标与评估题目均不能为空")
        print("有效" if not errors else "\n".join(errors))
        return 0 if not errors else 1
    if args.command == "report":
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    if not args.apply:
        raise SystemExit("写入补讲候选需要 --apply。")
    payload = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "candidates": reteach_candidates(items),
    }
    write_json_atomic(runtime / "assessment_reteach_candidates.json", payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
