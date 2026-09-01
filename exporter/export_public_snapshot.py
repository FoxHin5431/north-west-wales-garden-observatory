#!/usr/bin/env python3
"""Create the only dataset that may be published by the garden observatory."""

from __future__ import annotations

import json
import os
import sqlite3
from collections import Counter
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import NamedTemporaryFile
from zoneinfo import ZoneInfo

import pandas as pd
from astral import Observer
from astral.sun import sun


TIMEZONE_NAME = os.getenv("GARDEN_TIMEZONE", "Europe/London")
TIMEZONE = ZoneInfo(TIMEZONE_NAME)
LOCATION_LABEL = "North West Wales Garden"
BIRDNET_DB = Path(os.environ["BIRDNET_DB"])
WEATHER_DB = Path(os.environ["WEATHER_DB"])
OUTPUT_PATH = Path(os.getenv("PUBLIC_SNAPSHOT_PATH", "data/public_snapshot.json"))

# BirdNET-Go installations do not all store localized names in the database.
# Keep the garden's small, curated UK list as a display fallback; any species
# not listed here remains available under its scientific name.
COMMON_NAMES = {
    "Larus argentatus": "Herring Gull",
    "Sterna hirundo": "Common Tern",
    "Erithacus rubecula": "Robin",
    "Turdus merula": "Blackbird",
    "Turdus iliacus": "Redwing",
    "Parus major": "Great Tit",
    "Cyanistes caeruleus": "Blue Tit",
    "Periparus ater": "Coal Tit",
    "Aegithalos caudatus": "Long-tailed Tit",
    "Passer domesticus": "House Sparrow",
    "Passer montanus": "Tree Sparrow",
    "Sturnus vulgaris": "Starling",
    "Troglodytes troglodytes": "Wren",
    "Prunella modularis": "Dunnock",
    "Fringilla coelebs": "Chaffinch",
    "Chloris chloris": "Greenfinch",
    "Carduelis carduelis": "Goldfinch",
    "Spinus spinus": "Siskin",
    "Pyrrhula pyrrhula": "Bullfinch",
    "Columba palumbus": "Woodpigeon",
    "Streptopelia decaocto": "Collared Dove",
    "Corvus corone": "Carrion Crow",
    "Corvus frugilegus": "Rook",
    "Coloeus monedula": "Jackdaw",
    "Pica pica": "Magpie",
    "Garrulus glandarius": "Jay",
    "Apus apus": "Swift",
    "Hirundo rustica": "Barn Swallow",
    "Delichon urbicum": "House Martin",
    "Phylloscopus collybita": "Chiffchaff",
    "Sylvia atricapilla": "Blackcap",
    "Regulus regulus": "Goldcrest",
    "Sitta europaea": "Nuthatch",
    "Certhia familiaris": "Treecreeper",
    "Dendrocopos major": "Great Spotted Woodpecker",
    "Picus viridis": "Green Woodpecker",
    "Tyto alba": "Barn Owl",
    "Strix aluco": "Tawny Owl",
    "Buteo buteo": "Common Buzzard",
    "Falco tinnunculus": "Kestrel",
    "Falco peregrinus": "Peregrine",
    "Ardea cinerea": "Grey Heron",
    "Haematopus ostralegus": "Oystercatcher",
    "Numenius arquata": "Curlew",
    "Vanellus vanellus": "Lapwing",
    "Anthus trivialis": "Tree Pipit",
    "Phasianus colchicus": "Common Pheasant",
    "Fulica atra": "Coot",
    "Motacilla cinerea": "Grey Wagtail",
    "Gallinula chloropus": "Moorhen",
    "Melanitta nigra": "Common Scoter",
}


def readonly_connection(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}


def tables(connection: sqlite3.Connection) -> set[str]:
    return {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}


def species_labels(connection: sqlite3.Connection) -> str | None:
    label_columns = columns(connection, "labels")
    if "scientific_name" not in label_columns:
        raise RuntimeError("BirdNET labels table has no scientific_name column")
    return next((name for name in ("common_name", "common_name_en", "english_name") if name in label_columns), None)


def quality_for(confidence: float, repeat_count: int, has_clip: bool, unlikely: bool) -> tuple[str, float]:
    score = confidence
    if repeat_count >= 2:
        score += 0.08
    if repeat_count >= 4:
        score += 0.04
    if has_clip:
        score += 0.03
    if unlikely:
        score -= 0.25
    score = min(1.0, max(0.0, score))
    if score >= 0.90:
        return "Strong", score
    if score >= 0.78:
        return "Probable", score
    if score >= 0.62:
        return "Possible", score
    return "Review", score


def load_detections(now: datetime) -> pd.DataFrame:
    start = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=7)
    with closing(readonly_connection(BIRDNET_DB)) as connection:
        common_column = species_labels(connection)
        detection_columns = columns(connection, "detections")
        available_tables = tables(connection)
        model_label_columns = columns(connection, "model_labels") if "model_labels" in available_tables else set()
        can_resolve_raw_label = {"label_id", "model_id", "raw_label"}.issubset(model_label_columns) and "model_id" in detection_columns
        if common_column:
            common_sql = f"l.{common_column}"
            model_label_join = ""
        elif can_resolve_raw_label:
            # BirdNET raw labels use the documented ScientificName_CommonName format.
            common_sql = "CASE WHEN instr(ml.raw_label, '_') > 0 THEN substr(ml.raw_label, instr(ml.raw_label, '_') + 1) END"
            model_label_join = "LEFT JOIN model_labels ml ON ml.label_id = d.label_id AND ml.model_id = d.model_id"
        else:
            common_sql = "NULL"
            model_label_join = ""
        clip_sql = "d.clip_name" if "clip_name" in detection_columns else "NULL"
        unlikely_sql = "d.unlikely" if "unlikely" in detection_columns else "0"
        query = f"""
            SELECT d.detected_at, d.confidence, l.scientific_name,
                   {common_sql} AS common_name,
                   {clip_sql} AS clip_name,
                   {unlikely_sql} AS unlikely
            FROM detections d
            JOIN labels l ON l.id = d.label_id
            {model_label_join}
            WHERE d.detected_at >= ?
            ORDER BY d.detected_at
        """
        rows = connection.execute(query, (int(start.timestamp()),)).fetchall()

    if not rows:
        return pd.DataFrame(columns=["dt", "confidence", "scientific_name", "common_name", "quality", "display_score"])

    result = pd.DataFrame([dict(row) for row in rows])
    result["dt"] = pd.to_datetime(result["detected_at"], unit="s", utc=True).dt.tz_convert(TIMEZONE_NAME)
    mapped_names = result["scientific_name"].map(COMMON_NAMES)
    result["common_name"] = result["common_name"].fillna(mapped_names).fillna(result["scientific_name"])
    result["confidence"] = pd.to_numeric(result["confidence"], errors="coerce").fillna(0.0)
    result["unlikely"] = result["unlikely"].fillna(0).astype(bool)

    repeat_counts: list[int] = []
    for index, row in result.iterrows():
        window = (result["dt"] >= row["dt"] - pd.Timedelta(minutes=5)) & (result["dt"] <= row["dt"] + pd.Timedelta(minutes=5))
        repeat_counts.append(int((window & (result["scientific_name"] == row["scientific_name"])).sum()))
    result["repeat_count"] = repeat_counts
    scored = result.apply(
        lambda row: quality_for(float(row["confidence"]), int(row["repeat_count"]), bool(row["clip_name"]), bool(row["unlikely"])),
        axis=1,
    )
    result[["quality", "display_score"]] = pd.DataFrame(scored.tolist(), index=result.index)
    return result[result["quality"].isin(["Strong", "Probable"])].copy()


def latest_weather() -> dict | None:
    try:
        with closing(readonly_connection(WEATHER_DB)) as connection:
            required = ["observed_at", "temperature", "humidity", "wind_speed", "weather_description"]
            weather_table = next(
                (name for name in sorted(tables(connection)) if set(required).issubset(columns(connection, name))),
                None,
            )
            if weather_table is None:
                return None
            row = connection.execute(
                f'''SELECT observed_at, temperature, humidity, wind_speed, weather_description
                    FROM "{weather_table}" ORDER BY observed_at DESC LIMIT 1'''
            ).fetchone()
    except (OSError, sqlite3.Error):
        return None
    if row is None:
        return None
    observed = datetime.fromtimestamp(int(row["observed_at"]), TIMEZONE).isoformat()
    return {
        "observed_at": observed,
        "temperature": row["temperature"],
        "humidity": row["humidity"],
        "wind_speed": row["wind_speed"],
        "condition": row["weather_description"],
    }


def iso_records(dataframe: pd.DataFrame, date_columns: tuple[str, ...] = ()) -> list[dict]:
    clean = dataframe.copy()
    for column in date_columns:
        if column in clean.columns:
            clean[column] = clean[column].map(lambda value: value.isoformat() if pd.notna(value) else None)
    return json.loads(clean.to_json(orient="records"))


def build_snapshot(now: datetime) -> dict:
    detections = load_detections(now)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today = detections[detections["dt"] >= today_start].copy()
    last_hour = today[today["dt"] >= now - timedelta(hours=1)]

    hours = pd.date_range(today_start, today_start + timedelta(hours=23), freq="h")
    hourly_counts = today.set_index("dt").resample("h").size() if not today.empty else pd.Series(dtype=int)
    hourly = pd.DataFrame({"hour": hours, "detections": [int(hourly_counts.get(hour, 0)) for hour in hours]})

    species = (
        today.groupby(["common_name", "scientific_name"], as_index=False)
        .size()
        .rename(columns={"size": "detections"})
        .sort_values("detections", ascending=False)
    ) if not today.empty else pd.DataFrame(columns=["common_name", "scientific_name", "detections"])

    top_names = species.head(8)["common_name"].tolist() if not species.empty else []
    heat = today[today["common_name"].isin(top_names)].copy()
    if not heat.empty:
        heat["hour"] = heat["dt"].dt.floor("h")
        heat = heat.groupby(["common_name", "hour"], as_index=False).size().rename(columns={"size": "detections"})
    else:
        heat = pd.DataFrame(columns=["common_name", "hour", "detections"])

    trend_source = detections.copy()
    if not trend_source.empty:
        trend_source["date"] = trend_source["dt"].dt.date
        trend = trend_source.groupby("date").agg(detections=("dt", "size"), species=("scientific_name", "nunique")).reset_index()
    else:
        trend = pd.DataFrame(columns=["date", "detections", "species"])

    recent_columns = ["dt", "common_name", "scientific_name", "confidence", "quality"]
    recent = today.sort_values("dt", ascending=False).head(20)[recent_columns].rename(columns={"dt": "detected_at"})
    latest = recent.iloc[0].to_dict() if not recent.empty else None
    if latest:
        latest["detected_at"] = latest["detected_at"].isoformat()
        latest["confidence"] = round(float(latest["confidence"]), 4)

    quality_counts = Counter(today["quality"].tolist())
    latitude = float(os.environ["GARDEN_LATITUDE"])
    longitude = float(os.environ["GARDEN_LONGITUDE"])
    solar = sun(Observer(latitude=latitude, longitude=longitude), date=now.date(), tzinfo=TIMEZONE)

    return {
        "schema_version": 1,
        "meta": {
            "generated_at": now.isoformat(),
            "location_label": LOCATION_LABEL,
            "timezone": TIMEZONE_NAME,
            "demo": False,
        },
        "summary": {
            "detections_today": int(len(today)),
            "species_today": int(today["scientific_name"].nunique()),
            "detections_last_hour": int(len(last_hour)),
            "species_7d": int(detections["scientific_name"].nunique()),
        },
        "latest": latest,
        "dawn": {"civil_dawn": solar["dawn"].isoformat(), "sunrise": solar["sunrise"].isoformat()},
        "weather": latest_weather(),
        "activity_hourly": iso_records(hourly, ("hour",)),
        "species_today": iso_records(species),
        "species_heatmap": iso_records(heat, ("hour",)),
        "quality_counts": [{"quality": key, "count": int(quality_counts.get(key, 0))} for key in ("Strong", "Probable")],
        "trend_7d": iso_records(trend, ("date",)),
        "recent": iso_records(recent, ("detected_at",)),
    }


def write_atomic(payload: dict) -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", dir=OUTPUT_PATH.parent, delete=False) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temporary = Path(handle.name)
    temporary.replace(OUTPUT_PATH)


if __name__ == "__main__":
    write_atomic(build_snapshot(datetime.now(TIMEZONE)))
    print(f"Wrote privacy-filtered snapshot to {OUTPUT_PATH}")
