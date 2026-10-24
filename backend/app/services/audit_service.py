import hashlib
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from ..models import ActivityLog

GENESIS_HASH = "0" * 64


def canonical_json(data: Dict[str, Any]) -> str:
    """Produces a deterministic, canonical JSON representation with sorted keys."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)


def canonical_timestamp_str(dt: Any) -> str:
    """Produces a deterministic canonical timestamp string formatted to seconds."""
    if isinstance(dt, datetime):
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    dt_str = str(dt).replace("T", " ").split("+")[0].split(".")[0]
    return dt_str.strip()



def compute_event_hash(
    previous_hash: str,
    deal_id: str,
    actor_id: Optional[str],
    event_type: str,
    canonical_data: str,
    timestamp_str: str,
) -> str:
    """Computes SHA-256 hash across canonical event components."""
    content = f"{previous_hash}|{deal_id}|{actor_id or ''}|{event_type}|{canonical_data}|{timestamp_str}"
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def record_activity(
    db: Session,
    deal_id: str,
    actor_id: Optional[str],
    event_type: str,
    event_data: Dict[str, Any],
) -> ActivityLog:
    """
    Appends a new event to the deal's tamper-evident SHA-256 hash-chained audit log.
    """
    # Fetch the latest log entry for this deal
    latest_log = (
        db.query(ActivityLog)
        .filter(ActivityLog.deal_id == deal_id)
        .order_by(ActivityLog.created_at.desc())
        .first()
    )

    previous_hash = latest_log.event_hash if latest_log else GENESIS_HASH
    now = datetime.now(timezone.utc)
    timestamp_str = canonical_timestamp_str(now)
    clean_event_data = json.loads(json.dumps(event_data, default=str)) if event_data else {}
    data_json = canonical_json(clean_event_data)

    event_hash = compute_event_hash(
        previous_hash=previous_hash,
        deal_id=str(deal_id),
        actor_id=str(actor_id) if actor_id else None,
        event_type=event_type,
        canonical_data=data_json,
        timestamp_str=timestamp_str,
    )

    log_entry = ActivityLog(
        deal_id=str(deal_id),
        actor_id=str(actor_id) if actor_id else None,
        event_type=event_type,
        event_data=clean_event_data,
        previous_hash=previous_hash,
        event_hash=event_hash,
        created_at=now,
    )

    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    return log_entry


def verify_activity_chain(db: Session, deal_id: str) -> Dict[str, Any]:
    """
    Verifies the integrity of the stored event sequence for a deal room.
    Checks each event's hash, previous-event hash links, and deterministic data match.
    """
    logs = (
        db.query(ActivityLog)
        .filter(ActivityLog.deal_id == deal_id)
        .order_by(ActivityLog.created_at.asc())
        .all()
    )

    total_events = len(logs)
    if total_events == 0:
        return {
            "valid": True,
            "total_events": 0,
            "verified_events": 0,
            "broken_at_id": None,
            "message": "No activity recorded yet. The audit chain is initialized.",
        }

    expected_prev_hash = GENESIS_HASH
    verified_count = 0

    for i, log in enumerate(logs):
        # 1. Verify link to previous event
        if log.previous_hash != expected_prev_hash:
            return {
                "valid": False,
                "total_events": total_events,
                "verified_events": verified_count,
                "broken_at_id": log.id,
                "message": f"Link integrity violation at event index {i} ({log.event_type}). Previous hash mismatch.",
            }

        # 2. Recompute current event hash
        timestamp_str = canonical_timestamp_str(log.created_at)
        data_json = canonical_json(log.event_data)
        recomputed_hash = compute_event_hash(
            previous_hash=log.previous_hash,
            deal_id=log.deal_id,
            actor_id=log.actor_id,
            event_type=log.event_type,
            canonical_data=data_json,
            timestamp_str=timestamp_str,
        )


        if recomputed_hash != log.event_hash:
            return {
                "valid": False,
                "total_events": total_events,
                "verified_events": verified_count,
                "broken_at_id": log.id,
                "message": f"Hash integrity failure at event index {i} ({log.event_type}). Event payload or hash modified.",
            }

        expected_prev_hash = log.event_hash
        verified_count += 1

    return {
        "valid": True,
        "total_events": total_events,
        "verified_events": verified_count,
        "broken_at_id": None,
        "message": f"All {total_events} events verified successfully. Tamper-evident SHA-256 chain is intact.",
    }
