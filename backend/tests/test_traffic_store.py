
import sqlite3
from datetime import datetime

import pytest

from app.services.traffic_store import (
    get_evaluation,
    initialize_store,
    record_actual_trip,
    record_prediction,
)

DEPARTURE = datetime.fromisoformat("2026-10-27T09:00:00+00:00")


def create_prediction(db_path, duration=20):
    return record_prediction(
        origin_name="University of Ghana, Legon",
        destination_name="Accra Mall",
        origin_lat=5.6466,
        origin_lng=-0.1880,
        destination_lat=5.6228,
        destination_lng=-0.1740,
        departure_at=DEPARTURE,
        predicted_duration_min=duration,
        baseline_duration_min=15,
        source="mapbox_driving_traffic",
        simulated=False,
        db_path=db_path,
    )


def test_initialize_store_is_safe_to_repeat(tmp_path):
    db_path = tmp_path / "traffic.sqlite3"

    initialize_store(db_path)
    initialize_store(db_path)

    assert db_path.exists()


def test_record_prediction_returns_id(tmp_path):
    prediction_id = create_prediction(tmp_path / "traffic.sqlite3")

    assert prediction_id > 0
    assert get_evaluation(tmp_path / "traffic.sqlite3") == {
        "matched_observations": 0,
        "mae_minutes": None,
        "mean_signed_error_minutes": None,
    }


def test_evaluation_calculates_mae(tmp_path):
    db_path = tmp_path / "traffic.sqlite3"

    first_id = create_prediction(db_path, duration=20)
    second_id = create_prediction(db_path, duration=30)

    record_actual_trip(
        prediction_id=first_id,
        actual_duration_min=25,
        db_path=db_path,
    )
    record_actual_trip(
        prediction_id=second_id,
        actual_duration_min=26,
        db_path=db_path,
    )

    # Errors: +5 and -4 minutes. MAE = (5 + 4) / 2 = 4.5.
    assert get_evaluation(db_path) == {
        "matched_observations": 2,
        "mae_minutes": 4.5,
        "mean_signed_error_minutes": 0.5,
    }


def test_invalid_durations_are_rejected(tmp_path):
    with pytest.raises(ValueError, match="positive"):
        create_prediction(tmp_path / "traffic.sqlite3", duration=0)


def test_actual_trip_must_reference_a_prediction(tmp_path):
    db_path = tmp_path / "traffic.sqlite3"

    with pytest.raises(sqlite3.IntegrityError):
        record_actual_trip(
            prediction_id=9999,
            actual_duration_min=20,
            db_path=db_path,
        )


def test_actual_duration_must_be_positive(tmp_path):
    db_path = tmp_path / "traffic.sqlite3"
    prediction_id = create_prediction(db_path)

    with pytest.raises(ValueError, match="positive"):
        record_actual_trip(
            prediction_id=prediction_id,
            actual_duration_min=0,
            db_path=db_path,
        )
