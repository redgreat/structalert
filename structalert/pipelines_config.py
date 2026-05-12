"""
将「三段式」pipelines 配置展开为代码中沿用的顶层键：schedule_set、sync、archive_sync 等。
无 pipelines 时保持原配置文件完全兼容。
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


def _sched_entry(
    se: dict,
    default_cron: str,
    default_module: str,
    default_function: str,
) -> dict[str, Any]:
    cron = se.get("cron") or se.get("schedule") or default_cron
    return {
        "enabled": bool(se.get("enabled", False)),
        "schedule": cron,
        "module": se.get("module", default_module),
        "function": se.get("function", default_function),
    }


def apply_pipeline_layout(config: dict | None) -> dict | None:
    if not config or not isinstance(config, dict):
        return config
    pipes = config.get("pipelines")
    if not isinstance(pipes, dict) or not pipes:
        return config

    out = deepcopy(config)
    sched: dict[str, Any] = dict(out.get("schedule_set") or {})

    # ----- 1) 表结构对比 -----
    if "struct_compare" in pipes:
        p1 = pipes.get("struct_compare") or {}
        se = p1.get("schedule") or {}
        jid = se.get("job_id") or "daily_struct_compare"
        sched[jid] = _sched_entry(
            se,
            "0 2 * * *",
            "structalert.tasks",
            "run_daily_comparison",
        )

    # ----- 2) 基础数据迁移 -----
    if "base_data_sync" in pipes:
        p2 = pipes.get("base_data_sync") or {}
        se = p2.get("schedule") or {}
        jid = se.get("job_id") or "weekly_data_sync"
        sched[jid] = _sched_entry(
            se,
            "0 3 * * 0",
            "structalert.tasks",
            "run_weekly_sync",
        )
        if isinstance(p2.get("sync"), dict):
            merged_sync = {**(out.get("sync") or {})}
            merged_sync.update(p2["sync"])
            out["sync"] = merged_sync

    # ----- 3) 特殊业务表（归档 / 自定义水位）-----
    if "special_tables_sync" in pipes:
        p3 = pipes.get("special_tables_sync") or {}
        se = p3.get("schedule") or {}
        jid = se.get("job_id") or "workorder_archive_sync"
        sched[jid] = _sched_entry(
            se,
            "45 3 * * *",
            "structalert.tasks",
            "run_workorder_archive_sync",
        )
        arch: dict[str, Any] = {}
        skip = {"schedule"}
        for k, v in p3.items():
            if k in skip:
                continue
            arch[k] = deepcopy(v) if isinstance(v, dict) else v
        out["archive_sync"] = arch

    out["schedule_set"] = sched
    return out
