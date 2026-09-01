import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ExporterTests(unittest.TestCase):
    def test_export_is_cleaned_and_contains_no_private_fields(self):
        with tempfile.TemporaryDirectory() as folder:
            temp = Path(folder)
            bird_db = temp / "bird.db"
            weather_db = temp / "weather.db"
            output = temp / "snapshot.json"
            now = int(datetime.now().timestamp())

            with closing(sqlite3.connect(bird_db)) as connection:
                connection.executescript(
                    """
                    CREATE TABLE labels (id INTEGER PRIMARY KEY, scientific_name TEXT NOT NULL);
                    CREATE TABLE model_labels (id INTEGER PRIMARY KEY, model_id INTEGER, label_id INTEGER, raw_label TEXT);
                    CREATE TABLE detections (
                        id INTEGER PRIMARY KEY, model_id INTEGER, label_id INTEGER,
                        detected_at INTEGER, confidence REAL, clip_name TEXT, unlikely INTEGER
                    );
                    CREATE TABLE detection_reviews (
                        id INTEGER PRIMARY KEY, detection_id INTEGER NOT NULL, verified TEXT NOT NULL
                    );
                    INSERT INTO labels VALUES (1, 'Erithacus rubecula');
                    INSERT INTO model_labels VALUES (1, 1, 1, 'Erithacus rubecula_European Robin');
                    INSERT INTO detection_reviews VALUES (1, 2, 'false_positive');
                    """
                )
                connection.executemany(
                    "INSERT INTO detections VALUES (?, 1, 1, ?, ?, ?, ?)",
                    [
                        (1, now - 60, 0.95, 'private-audio.m4a', 0),
                        (2, now - 120, 0.91, 'private-audio-2.m4a', 0),
                        (3, now - 180, 0.20, 'review-only.m4a', 1),
                        (4, now - 240, 0.99, 'unlikely-high-confidence.m4a', 1),
                    ],
                )
                connection.commit()

            with closing(sqlite3.connect(weather_db)) as connection:
                connection.executescript(
                    f"""
                    CREATE TABLE observations (
                        observed_at INTEGER, temperature REAL, humidity REAL,
                        wind_speed REAL, weather_description TEXT
                    );
                    INSERT INTO observations VALUES ({now}, 14.5, 75, 2.1, 'light cloud');
                    """
                )
                connection.commit()

            env = os.environ.copy()
            env.update(
                {
                    "BIRDNET_DB": str(bird_db),
                    "WEATHER_DB": str(weather_db),
                    "GARDEN_LATITUDE": "1.0",
                    "GARDEN_LONGITUDE": "2.0",
                    "PUBLIC_SNAPSHOT_PATH": str(output),
                    "PUBLIC_SPECIES_IMAGES": "0",
                }
            )
            completed = subprocess.run(
                [sys.executable, str(ROOT / "exporter" / "export_public_snapshot.py")],
                cwd=ROOT,
                env=env,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)

            payload = json.loads(output.read_text(encoding="utf-8"))
            serialised = json.dumps(payload)
            self.assertEqual(payload["latest"]["common_name"], "European Robin")
            self.assertEqual(payload["summary"]["detections_today"], 1)
            self.assertEqual(payload["weather"]["condition"], "light cloud")
            self.assertNotIn("private-audio", serialised)
            self.assertNotIn("clip_name", serialised)
            self.assertNotIn("latitude", serialised)
            self.assertNotIn("longitude", serialised)
            self.assertNotIn("Review", serialised)


if __name__ == "__main__":
    unittest.main()
