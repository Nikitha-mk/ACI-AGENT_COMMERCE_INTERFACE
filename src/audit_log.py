"""
audit_log.py — Stage 5. One flat, readable trail: parse -> normalize ->
validate -> ACI record built -> agent decision -> budget check ->
consent check -> payment result -> outcome.

Deliberately a plain list of dict rows, not a database — for a hackathon
demo, "readable table you can screenshot" beats "queryable store."
"""

import csv
import uuid
from datetime import datetime, timezone


class AuditLog:
    def __init__(self):
        self.rows: list[dict] = []

    def log(self, run_id: str, record_id: str, stage: str, detail: str) -> None:
        self.rows.append({
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "run_id": run_id,
            "record_id": record_id,
            "stage": stage,
            "detail": detail,
        })

    def trail_for(self, record_id: str) -> list[dict]:
        return [r for r in self.rows if r["record_id"] == record_id]

    def save_csv(self, path: str) -> None:
        if not self.rows:
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(self.rows[0].keys()))
            writer.writeheader()
            writer.writerows(self.rows)


def new_run_id() -> str:
    return uuid.uuid4().hex[:12]
