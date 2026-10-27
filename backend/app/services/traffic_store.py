
"""SQLite storage for traffic predictions and actual journey outcomes."""

import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

DEFAULT_DB_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "traffic_history.sqlite3"
)


def _resolve_path(db_path: str | Path | None = None) -> Path:
    """Resolve the database path, allowing tests to use temporary files."""
    if db_path is not None:
        return Path(db_path)

    configured_path = os.getenv("TRAFFIC_DB_PATH")
    if configured_path:
        return Path(configured_path)

    return DEFAULT_DB_PATH


def _connect(db_path: str | Path | None = None) -> sqlite3.Connection:
    path = _resolve_path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_store(
    db_path: str | Path | None = None,
) -> None:
    """Create the storage tables if they do not already exist."""
    connection = _connect(db_path)
    try:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                origin_name TEXT NOT NULL,
                destination_name TEXT NOT NULL,
                origin_lat REAL NOT NULL,
                origin_lng REAL NOT NULL,
                destination_lat REAL NOT NULL,
                destination_lng REAL NOT NULL,
                departure_at TEXT NOT NULL,
                predicted_duration_min INTEGER NOT NULL
                    CHECK (predicted_duration_min > 0),
                baseline_duration_min INTEGER,
                source TEXT NOT NULL,
                simulated INTEGER NOT NULL
                    CHECK (simulated IN (0, 1)),
                predicted_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS actual_trips (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prediction_id INTEGER NOT NULL UNIQUE,
                actual_duration_min INTEGER NOT NULL
                    CHECK (actual_duration_min > 0),
                observed_at TEXT NOT NULL,
                observation_source TEXT NOT NULL,
                FOREIGN KEY (prediction_id)
                    REFERENCES predictions(id)
                    ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_predictions_route_time
                ON predictions (
                    origin_name,
                    destination_name,
                    departure_at
                );
            """
        )
        connection.commit()
    finally:
        connection.close()


def record_prediction(
    *,
    origin_name: str,
    destination_name: str,
    origin_lat: float,
    origin_lng: float,
    destination_lat: float,
    destination_lng: float,
    departure_at: datetime,
    predicted_duration_min: int,
    baseline_duration_min: int | None,
    source: str,
    simulated: bool,
    db_path: str | Path | None = None,
) -> int:
    """Persist a prediction and return its database ID."""
    if predicted_duration_min <= 0:
        raise ValueError("Predicted duration must be positive.")

    if baseline_duration_min is not None and baseline_duration_min <= 0:
        raise ValueError("Baseline duration must be positive.")

    initialize_store(db_path)
    connection = _connect(db_path)

    try:
        cursor = connection.execute(
            """
            INSERT INTO predictions (
                origin_name, destination_name,
                origin_lat, origin_lng,
                destination_lat, destination_lng,
                departure_at, predicted_duration_min,
                baseline_duration_min, source, simulated,
                predicted_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                origin_name,
                destination_name,
                origin_lat,
                origin_lng,
                destination_lat,
                destination_lng,
                departure_at.isoformat(),
                predicted_duration_min,
                baseline_duration_min,
                source,
                int(simulated),
                datetime.now(UTC).isoformat(),
            ),
        )
        connection.commit()
        return int(cursor.lastrowid)
    finally:
        connection.close()


def record_actual_trip(
    *,
    prediction_id: int,
    actual_duration_min: int,
    observation_source: str = "user_reported",
    observed_at: datetime | None = None,
    db_path: str | Path | None = None,
) -> int:
    """Record an actual journey duration against one prediction."""
    if actual_duration_min <= 0:
        raise ValueError("Actual duration must be positive.")

    if not observation_source.strip():
        raise ValueError("Observation source cannot be empty.")

    initialize_store(db_path)
    connection = _connect(db_path)

    try:
        cursor = connection.execute(
            """
            INSERT INTO actual_trips (
                prediction_id, actual_duration_min,
                observed_at, observation_source
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                prediction_id,
                actual_duration_min,
                (observed_at or datetime.now(UTC)).isoformat(),
                observation_source,
            ),
        )
        connection.commit()
        return int(cursor.lastrowid)
    finally:
        connection.close()


def get_evaluation(
    db_path: str | Path | None = None,
) -> dict:
    """Evaluate predictions that have matching actual journey durations."""
    initialize_store(db_path)
    connection = _connect(db_path)

    try:
        rows = connection.execute(
            """
            SELECT
                p.predicted_duration_min,
                a.actual_duration_min
            FROM predictions AS p
            JOIN actual_trips AS a
                ON a.prediction_id = p.id
            """
        ).fetchall()
    finally:
        connection.close()

    if not rows:
        return {
            "matched_observations": 0,
            "mae_minutes": None,
            "mean_signed_error_minutes": None,
        }

    errors = [
        row["actual_duration_min"] - row["predicted_duration_min"]
        for row in rows
    ]

    return {
        "matched_observations": len(errors),
        "mae_minutes": round(
            sum(abs(error) for error in errors) / len(errors), 2
        ),
        "mean_signed_error_minutes": round(
            sum(errors) / len(errors), 2
        ),
    }
