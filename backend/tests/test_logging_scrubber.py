"""The PHI scrubber is a compliance backstop, so it is tested directly."""

from __future__ import annotations

import json
import logging

from app.logging_config import JsonFormatter, PHIScrubbingFilter


def _emit(**extra: object) -> dict:
    record = logging.makeLogRecord(
        {"msg": "processed batch", "levelname": "INFO", "name": "test", **extra}
    )
    PHIScrubbingFilter().filter(record)
    return json.loads(JsonFormatter().format(record))


def test_top_level_phi_fields_are_redacted() -> None:
    out = _emit(patient_name="Jane Doe", dob="1990-01-01", batch_id="b-1")
    assert out["patient_name"] == "[REDACTED]"
    assert out["dob"] == "[REDACTED]"
    # Non-PHI operational context survives.
    assert out["batch_id"] == "b-1"


def test_nested_phi_is_redacted() -> None:
    out = _emit(
        appointment={
            "patient_name": "Jane Doe",
            "subscriber_id": "ABC123",
            "appt_time": "09:00",
        }
    )
    appt = out["appointment"]
    assert appt["patient_name"] == "[REDACTED]"
    assert appt["subscriber_id"] == "[REDACTED]"
    assert appt["appt_time"] == "09:00"


def test_phi_inside_lists_is_redacted() -> None:
    out = _emit(patients=[{"name": "A"}, {"name": "B", "member_id": "M1"}])
    assert out["patients"][0]["name"] == "[REDACTED]"
    assert out["patients"][1]["member_id"] == "[REDACTED]"


def test_payer_name_is_not_treated_as_phi() -> None:
    # Payer/plan names are not identifiers; they must remain loggable.
    out = _emit(payer_name="Delta Dental", plan="PPO")
    assert out["payer_name"] == "Delta Dental"
    assert out["plan"] == "PPO"
