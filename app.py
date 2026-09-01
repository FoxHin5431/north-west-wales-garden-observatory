from __future__ import annotations

import html
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import altair as alt
import pandas as pd
import requests
import streamlit as st


APP_ROOT = Path(__file__).resolve().parent
DATA_PATH = Path(os.getenv("GARDEN_DATA_PATH", APP_ROOT / "data" / "public_snapshot.json"))
CONTENT_PATH = APP_ROOT / "content" / "site_text.json"
PUBLIC_DATA_URL = os.getenv(
    "GARDEN_DATA_URL",
    "https://raw.githubusercontent.com/FoxHin5431/north-west-wales-garden-observatory/data/public_snapshot.json",
)
REFRESH_MS = 10 * 60 * 1000

INK = "#213129"
MUTED = "#67736c"
GREEN = "#356348"
GREEN_LIGHT = "#dce9de"
TEAL = "#46736c"
GOLD = "#b8883b"
GRID = "#dedfd9"


st.set_page_config(
    page_title="North West Wales Garden Observatory",
    page_icon="🐦",
    layout="wide",
    initial_sidebar_state="collapsed",
)


@st.cache_data(ttl=300, show_spinner=False)
def load_snapshot(path: str, modified_ns: int) -> dict[str, Any]:
    del modified_ns
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


@st.cache_data(ttl=300, show_spinner=False)
def load_remote_snapshot(url: str) -> dict[str, Any]:
    response = requests.get(url, timeout=8)
    response.raise_for_status()
    return response.json()


def snapshot() -> dict[str, Any]:
    # An explicit local path is used for development and automated tests.
    if "GARDEN_DATA_PATH" not in os.environ:
        try:
            return load_remote_snapshot(PUBLIC_DATA_URL)
        except (requests.RequestException, ValueError):
            pass
    try:
        stat = DATA_PATH.stat()
        return load_snapshot(str(DATA_PATH), stat.st_mtime_ns)
    except (OSError, json.JSONDecodeError):
        return {
            "meta": {"location_label": "North West Wales Garden", "demo": True},
            "summary": {},
            "activity_hourly": [],
            "species_today": [],
            "species_heatmap": [],
            "quality_counts": [],
            "trend_7d": [],
            "recent": [],
        }


@st.cache_data(show_spinner=False)
def load_site_text(path: str, modified_ns: int) -> dict[str, Any]:
    del modified_ns
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def site_text() -> dict[str, Any]:
    try:
        stat = CONTENT_PATH.stat()
        return load_site_text(str(CONTENT_PATH), stat.st_mtime_ns)
    except (OSError, json.JSONDecodeError):
        return {}


def wording(source: dict[str, Any], section: str, key: str, default: str) -> str:
    value = source.get(section, {}).get(key, default)
    return str(value) if value is not None else default


def esc(value: Any) -> str:
    return html.escape(str(value or ""))


def safe_http_url(value: Any) -> str:
    text = str(value or "").strip()
    parsed = urlparse(text)
    return text if parsed.scheme in {"http", "https"} and parsed.netloc else ""


def linked_text(label: Any, url: Any) -> str:
    clean_label = esc(label)
    clean_url = safe_http_url(url)
    if not clean_label:
        return ""
    if not clean_url:
        return clean_label
    return f'<a href="{esc(clean_url)}" target="_blank" rel="noopener noreferrer">{clean_label}</a>'


def photo_credit(image: dict[str, Any]) -> str:
    provider = str(image.get("source_provider") or "").replace("_", " ").title()
    parts = [
        linked_text(image.get("author_name"), image.get("author_url")),
        linked_text(image.get("license_name"), image.get("license_url")),
        esc(provider),
    ]
    return " · ".join(part for part in parts if part)


def parse_time(value: Any) -> pd.Timestamp | None:
    if not value:
        return None
    parsed = pd.to_datetime(value, errors="coerce")
    return None if pd.isna(parsed) else parsed


def clock(value: Any) -> str:
    parsed = parse_time(value)
    return "—" if parsed is None else parsed.strftime("%H:%M")


def compact_number(value: Any) -> str:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return "—"
    return f"{number:,}"


def panel_heading(title: str, description: str = "") -> None:
    st.markdown(
        f'<div class="panel-heading"><h2>{esc(title)}</h2>'
        f'<p>{esc(description)}</p></div>',
        unsafe_allow_html=True,
    )


def empty_state(message: str) -> None:
    st.markdown(
        f'<div class="empty-state"><span>○</span>{esc(message)}</div>',
        unsafe_allow_html=True,
    )


def frame(data: list[dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame(data or [])


st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Newsreader:opsz,wght@6..72,500;6..72,600&display=swap');

:root {
  --paper: #f3f1ea;
  --surface: #fbfaf6;
  --surface-soft: #ebece5;
  --ink: #213129;
  --muted: #67736c;
  --green: #356348;
  --green-light: #dce9de;
  --line: #d9ddd6;
}

.stApp {
  color: var(--ink);
  background:
    radial-gradient(circle at 92% 2%, rgba(126, 159, 125, .18), transparent 24rem),
    var(--paper);
}

[data-testid="stHeader"], [data-testid="stToolbar"] { background: transparent; }
[data-testid="stAppViewContainer"] > .main .block-container {
  max-width: 1260px;
  padding: 2.4rem 2rem 4rem;
}

html, body, [class*="css"] { font-family: "DM Sans", sans-serif; }
h1, h2, h3, p { color: var(--ink); }

.hero {
  position: relative;
  overflow: hidden;
  min-height: 264px;
  padding: clamp(1.6rem, 4vw, 3.3rem);
  margin-bottom: 1rem;
  border: 1px solid rgba(53, 99, 72, .19);
  border-radius: 32px;
  background: linear-gradient(120deg, #f9f7f1 0%, #eef2e9 100%);
  box-shadow: 0 18px 50px rgba(44, 58, 48, .07);
}
.hero::after {
  content: "";
  position: absolute;
  width: 310px;
  height: 310px;
  right: -60px;
  top: -100px;
  border: 1px solid rgba(53, 99, 72, .2);
  border-radius: 50%;
  box-shadow: 0 0 0 42px rgba(53, 99, 72, .035), 0 0 0 86px rgba(53, 99, 72, .025);
}
.eyebrow {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: .6rem;
  margin-bottom: 1.1rem;
  color: var(--green);
  font-size: .73rem;
  font-weight: 700;
  letter-spacing: .15em;
  text-transform: uppercase;
}
.eyebrow-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #4f8a61;
  box-shadow: 0 0 0 5px rgba(79, 138, 97, .13);
}
.hero h1 {
  position: relative;
  z-index: 1;
  max-width: 760px;
  margin: 0 0 .65rem;
  font-family: "Newsreader", Georgia, serif;
  font-size: clamp(3rem, 7vw, 5.8rem);
  font-weight: 500;
  letter-spacing: -.055em;
  line-height: .9;
}
.hero-copy {
  position: relative;
  z-index: 1;
  max-width: 620px;
  margin: 0;
  color: var(--muted);
  font-size: 1.02rem;
  line-height: 1.55;
}
.hero-meta {
  position: relative;
  z-index: 1;
  display: flex;
  flex-wrap: wrap;
  gap: .55rem;
  margin-top: 1.5rem;
}
.chip {
  display: inline-flex;
  align-items: center;
  padding: .42rem .72rem;
  border: 1px solid rgba(53, 99, 72, .16);
  border-radius: 999px;
  background: rgba(255, 255, 255, .58);
  color: #4f5e55;
  font-size: .76rem;
  font-weight: 600;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: .8rem;
  margin: .8rem 0;
}
.metric-card {
  display: flex;
  flex-direction: column;
  min-height: 118px;
  padding: 1.15rem 1.25rem;
  border: 1px solid var(--line);
  border-radius: 22px;
  background: rgba(251, 250, 246, .88);
  box-shadow: 0 8px 24px rgba(44, 58, 48, .035);
}
.metric-value {
  margin-bottom: .25rem;
  font-family: "Newsreader", Georgia, serif;
  color: var(--ink);
  font-size: 2.45rem;
  font-weight: 600;
  line-height: 1;
}
.metric-label { color: var(--muted); font-size: .82rem; font-weight: 600; }
.metric-note { margin-top: auto; padding-top: .38rem; color: #8b958f; font-size: .72rem; }

[data-testid="stHorizontalBlock"] { align-items: stretch; }
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"] { display: flex; }
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"] > div {
  display: flex;
  width: 100%;
  flex: 1 1 auto;
  flex-direction: column;
}
[data-testid="stHorizontalBlock"] [data-testid="stVerticalBlockBorderWrapper"] {
  height: 100%;
}

[data-testid="stVerticalBlockBorderWrapper"],
[data-testid="stColumn"] [data-testid="stLayoutWrapper"] > [data-testid="stVerticalBlock"] {
  border-color: var(--line) !important;
  border-radius: 24px !important;
  background: rgba(251, 250, 246, .92) !important;
  box-shadow: 0 9px 28px rgba(44, 58, 48, .04);
}
[data-testid="stVerticalBlockBorderWrapper"] > div { padding: .35rem .4rem .45rem; }
[data-testid="stColumn"] [data-testid="stLayoutWrapper"] {
  height: 100%;
}
[data-testid="stColumn"] [data-testid="stLayoutWrapper"] > [data-testid="stVerticalBlock"] {
  height: 100%;
  padding: 1rem;
}
.panel-heading { margin: .15rem 0 .75rem; }
.panel-heading h2 {
  margin: 0 0 .22rem;
  font-family: "Newsreader", Georgia, serif;
  font-size: 1.55rem;
  font-weight: 600;
  letter-spacing: -.02em;
}
.panel-heading p { margin: 0; color: var(--muted); font-size: .8rem; line-height: 1.4; }

.latest-species {
  padding: .5rem 0 .65rem;
  border-bottom: 1px solid var(--line);
}
.latest-content.has-image {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 138px;
  gap: 1rem;
  align-items: start;
}
.species-photo { margin: 0; }
.species-photo img {
  display: block;
  width: 100%;
  aspect-ratio: 4 / 3;
  object-fit: cover;
  border: 1px solid var(--line);
  border-radius: 17px;
  background: var(--surface-soft);
}
.species-photo figcaption {
  margin-top: .38rem;
  color: #7a857e;
  font-size: .61rem;
  line-height: 1.35;
}
.species-photo figcaption a { color: #5c7365; text-decoration-thickness: 1px; }
.latest-species h3 {
  margin: 0;
  font-family: "Newsreader", Georgia, serif;
  font-size: clamp(2.25rem, 5vw, 3.7rem);
  font-weight: 500;
  letter-spacing: -.04em;
  line-height: .95;
}
.latin { margin-top: .5rem; color: var(--muted); font-family: Georgia, serif; font-size: .98rem; font-style: italic; }
.latest-details { display: flex; flex-wrap: wrap; gap: .5rem; margin-top: .9rem; }
.status-pill {
  display: inline-flex;
  padding: .38rem .7rem;
  border-radius: 999px;
  background: var(--green-light);
  color: #2f5a40;
  font-size: .75rem;
  font-weight: 700;
}
.detail-pill {
  display: inline-flex;
  padding: .38rem .7rem;
  border-radius: 999px;
  background: #ecebe5;
  color: #59645e;
  font-size: .75rem;
  font-weight: 600;
}

.weather-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: .55rem;
}
.weather-item {
  display: flex;
  min-height: 82px;
  padding: .8rem;
  flex-direction: column;
  justify-content: space-between;
  border-radius: 16px;
  background: #f0f1eb;
}
.weather-item strong { display: block; color: var(--ink); font-size: 1.25rem; }
.weather-item span { color: var(--muted); font-size: .7rem; font-weight: 600; }

.recent-row {
  display: grid;
  grid-template-columns: 68px minmax(0, 1fr) auto;
  gap: .8rem;
  align-items: center;
  padding: .72rem 0;
  border-top: 1px solid var(--line);
}
.recent-time { color: var(--green); font-size: .79rem; font-weight: 700; }
.recent-name { color: var(--ink); font-weight: 700; }
.recent-latin { color: var(--muted); font-family: Georgia, serif; font-size: .77rem; font-style: italic; }
.recent-score { color: var(--muted); font-size: .74rem; }

.empty-state {
  display: flex;
  align-items: center;
  gap: .55rem;
  min-height: 150px;
  color: var(--muted);
  font-size: .86rem;
}
.empty-state span { color: var(--green); font-size: 1.5rem; }

.method-note {
  margin-top: .9rem;
  padding: 1rem 1.15rem;
  border-left: 3px solid #77957d;
  border-radius: 0 14px 14px 0;
  background: rgba(220, 233, 222, .45);
  color: #56655c;
  font-size: .78rem;
  line-height: 1.55;
}
.footer {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  margin-top: 1.2rem;
  padding: 1.1rem .2rem;
  border-top: 1px solid var(--line);
  color: var(--muted);
  font-size: .72rem;
}

@media (max-width: 800px) {
  [data-testid="stAppViewContainer"] > .main .block-container { padding: 1.1rem .8rem 2.5rem; }
  .hero { min-height: 230px; border-radius: 25px; }
  .metric-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .weather-strip { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .footer { flex-direction: column; }
}
@media (max-width: 520px) {
  .latest-content.has-image { grid-template-columns: 1fr; }
  .species-photo img { max-height: 210px; }
}
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    f"""
<script>
setTimeout(function () {{ window.parent.location.reload(); }}, {REFRESH_MS});
</script>
""",
    unsafe_allow_html=True,
)

data = snapshot()
copy = site_text()
meta = data.get("meta", {})
summary = data.get("summary", {})
location = meta.get("location_label") or "North West Wales Garden"
generated_at = parse_time(meta.get("generated_at"))
is_demo = bool(meta.get("demo", False))

updated_label = (
    wording(copy, "status", "waiting", "Waiting for live data")
    if generated_at is None
    else f"{wording(copy, 'status', 'updated_prefix', 'Updated')} {generated_at.strftime('%H:%M')}"
)
hero_title = esc(wording(copy, "hero", "title", "Listening to\nthe garden.")).replace("\n", "<br>")
st.markdown(
    f"""
<section class="hero">
  <div class="eyebrow"><span class="eyebrow-dot"></span>{esc(location)} · {esc(wording(copy, 'hero', 'eyebrow_suffix', 'acoustic observatory'))}</div>
  <h1>{hero_title}</h1>
  <p class="hero-copy">{esc(wording(copy, 'hero', 'description', 'Birds heard from a garden in North West Wales, recorded through the day.'))}</p>
  <div class="hero-meta">
    <span class="chip">● {esc(wording(copy, 'hero', 'live_chip', 'Observatory live'))}</span>
    <span class="chip">{esc(updated_label)}</span>
    <span class="chip">{esc(wording(copy, 'hero', 'data_chip', 'Checked detections'))}</span>
  </div>
</section>
""",
    unsafe_allow_html=True,
)

if is_demo:
    st.info(wording(copy, "status", "setup_message", "The page is ready. Data will appear after the first update."))

metrics = [
    (compact_number(summary.get("detections_today")), wording(copy.get("metrics", {}), "detections_today", "label", "Detections today"), wording(copy.get("metrics", {}), "detections_today", "note", "Recorded calls, not individual birds")),
    (compact_number(summary.get("species_today")), wording(copy.get("metrics", {}), "species_today", "label", "Species today"), wording(copy.get("metrics", {}), "species_today", "note", "Species in the checked results")),
    (compact_number(summary.get("detections_last_hour")), wording(copy.get("metrics", {}), "detections_last_hour", "label", "Last hour"), wording(copy.get("metrics", {}), "detections_last_hour", "note", "Recent calling activity")),
    (compact_number(summary.get("species_7d")), wording(copy.get("metrics", {}), "species_7d", "label", "Species this week"), wording(copy.get("metrics", {}), "species_7d", "note", "Rolling seven-day total")),
]
st.markdown(
    '<div class="metric-grid">'
    + "".join(
        f'<div class="metric-card"><div class="metric-value">{esc(value)}</div>'
        f'<div class="metric-label">{esc(label)}</div><div class="metric-note">{esc(note)}</div></div>'
        for value, label, note in metrics
    )
    + "</div>",
    unsafe_allow_html=True,
)

left, right = st.columns([0.82, 1.35], gap="medium")
with left:
    with st.container(border=True):
        panel_heading(wording(copy.get("sections", {}), "latest", "title", "Latest detection"), wording(copy.get("sections", {}), "latest", "description", "Most recent confident match."))
        latest = data.get("latest")
        if latest:
            confidence = latest.get("confidence")
            confidence_text = "—" if confidence is None else f"{float(confidence):.0%} confidence"
            image = latest.get("image") if isinstance(latest.get("image"), dict) else {}
            image_url = safe_http_url(image.get("url"))
            image_html = ""
            if image_url:
                species_name = latest.get("common_name") or latest.get("scientific_name") or "bird"
                credit = photo_credit(image)
                caption = f"<figcaption>{credit}</figcaption>" if credit else ""
                image_html = (
                    f'<figure class="species-photo"><img src="{esc(image_url)}" '
                    f'alt="Reference photograph of {esc(species_name)}">{caption}</figure>'
                )
            content_class = "latest-content has-image" if image_html else "latest-content"
            st.markdown(
                f"""
<div class="{content_class}">
<div>
<div class="latest-species">
  <h3>{esc(latest.get('common_name') or latest.get('scientific_name') or 'Unknown species')}</h3>
  <div class="latin">{esc(latest.get('scientific_name'))}</div>
</div>
<div class="latest-details">
  <span class="status-pill">{esc(latest.get('quality', 'Cleaned'))}</span>
  <span class="detail-pill">{esc(clock(latest.get('detected_at')))}</span>
  <span class="detail-pill">{esc(confidence_text)}</span>
</div>
</div>
{image_html}
</div>
""",
                unsafe_allow_html=True,
            )
        else:
            empty_state(wording(copy.get("sections", {}), "latest", "empty", "No confident detections yet today."))

with right:
    with st.container(border=True):
        panel_heading(wording(copy.get("sections", {}), "activity", "title", "Activity today"), wording(copy.get("sections", {}), "activity", "description", "Detections by hour since midnight."))
        hourly = frame(data.get("activity_hourly", []))
        if not hourly.empty and {"hour", "detections"}.issubset(hourly.columns):
            hourly["hour"] = pd.to_datetime(hourly["hour"], errors="coerce")
            hourly = hourly.dropna(subset=["hour"])
            base = alt.Chart(hourly).encode(x=alt.X("hour:T", title=None, axis=alt.Axis(format="%H:%", labelAngle=0)))
            area = base.mark_area(
                line={"color": GREEN, "strokeWidth": 2.5},
                color=alt.Gradient(
                    gradient="linear",
                    stops=[alt.GradientStop(color="#86a78e", offset=0), alt.GradientStop(color="#eef3ec", offset=1)],
                    x1=1,
                    x2=1,
                    y1=0,
                    y2=1,
                ),
                interpolate="monotone",
            ).encode(y=alt.Y("detections:Q", title="Detections", axis=alt.Axis(tickMinStep=1)))
            layers: list[alt.Chart] = [area]
            dawn = data.get("dawn", {})
            markers = []
            for label, key in (("Civil dawn", "civil_dawn"), ("Sunrise", "sunrise")):
                value = parse_time(dawn.get(key))
                if value is not None:
                    markers.append({"time": value, "label": label})
            if markers:
                marker_df = pd.DataFrame(markers)
                rules = alt.Chart(marker_df).mark_rule(strokeDash=[4, 4], color=GOLD).encode(x="time:T")
                labels = alt.Chart(marker_df).mark_text(angle=270, align="right", dx=-5, color="#816126", fontSize=10).encode(x="time:T", text="label:N")
                layers.extend([rules, labels])
            chart = alt.layer(*layers).properties(height=265).configure_view(stroke=None).configure_axis(
                gridColor=GRID, domain=False, tickColor=GRID, labelColor=MUTED, titleColor=MUTED
            )
            st.altair_chart(chart, width="stretch")
        else:
            empty_state(wording(copy.get("sections", {}), "activity", "empty", "Hourly activity will appear after the first detections."))

left, right = st.columns([1.1, 0.9], gap="medium")
with left:
    with st.container(border=True):
        panel_heading(wording(copy.get("sections", {}), "community", "title", "Birds heard today"), wording(copy.get("sections", {}), "community", "description", "The species detected most often so far."))
        species = frame(data.get("species_today", []))
        if not species.empty and {"common_name", "detections"}.issubset(species.columns):
            species = species.sort_values("detections", ascending=True).tail(10)
            ranking = (
                alt.Chart(species)
                .mark_bar(color=TEAL, cornerRadiusEnd=5, height=17)
                .encode(
                    x=alt.X("detections:Q", title="Detections", axis=alt.Axis(tickMinStep=1)),
                    y=alt.Y("common_name:N", title=None, sort=None),
                    tooltip=["common_name:N", "scientific_name:N", "detections:Q"],
                )
                .properties(height=max(220, len(species) * 31))
                .configure_view(stroke=None)
                .configure_axis(gridColor=GRID, domain=False, tickColor=GRID, labelColor=MUTED, titleColor=MUTED)
            )
            st.altair_chart(ranking, width="stretch")
        else:
            empty_state(wording(copy.get("sections", {}), "community", "empty", "The species list will build through the day."))

with right:
    with st.container(border=True):
        panel_heading(wording(copy.get("sections", {}), "weather", "title", "Garden weather"), wording(copy.get("sections", {}), "weather", "description", "Conditions at the latest weather check."))
        weather = data.get("weather") or {}
        if weather:
            temperature = weather.get("temperature")
            humidity = weather.get("humidity")
            wind = weather.get("wind_speed")
            values = [
                ("—" if temperature is None else f"{float(temperature):.1f}°", wording(copy, "weather_labels", "temperature", "Temperature")),
                ("—" if humidity is None else f"{float(humidity):.0f}%", wording(copy, "weather_labels", "humidity", "Humidity")),
                ("—" if wind is None else f"{float(wind):.1f} m/s", wording(copy, "weather_labels", "wind", "Wind")),
                (weather.get("condition") or "—", wording(copy, "weather_labels", "conditions", "Conditions")),
            ]
            st.markdown(
                '<div class="weather-strip">'
                + "".join(f'<div class="weather-item"><strong>{esc(v)}</strong><span>{esc(k)}</span></div>' for v, k in values)
                + "</div>",
                unsafe_allow_html=True,
            )
        else:
            empty_state(wording(copy.get("sections", {}), "weather", "empty", "Weather will appear with the next update."))

        panel_heading(wording(copy.get("sections", {}), "quality", "title", "Detection quality"), wording(copy.get("sections", {}), "quality", "description", "Only Strong and Probable matches are shown."))
        quality = frame(data.get("quality_counts", []))
        if not quality.empty and {"quality", "count"}.issubset(quality.columns):
            qchart = (
                alt.Chart(quality)
                .mark_arc(innerRadius=58, outerRadius=88, cornerRadius=5)
                .encode(
                    theta=alt.Theta("count:Q"),
                    color=alt.Color(
                        "quality:N",
                        scale=alt.Scale(domain=["Strong", "Probable"], range=[GREEN, "#9aaa73"]),
                        legend=alt.Legend(title=None, orient="bottom"),
                    ),
                    tooltip=["quality:N", "count:Q"],
                )
                .properties(height=245)
                .configure_view(stroke=None)
            )
            st.altair_chart(qchart, width="stretch")
        else:
            empty_state(wording(copy.get("sections", {}), "quality", "empty", "Quality totals will appear with live data."))

left, right = st.columns([1.25, 0.75], gap="medium")
with left:
    with st.container(border=True):
        panel_heading(wording(copy.get("sections", {}), "rhythm", "title", "When birds were active"), wording(copy.get("sections", {}), "rhythm", "description", "The hours when today's leading species were heard."))
        heatmap = frame(data.get("species_heatmap", []))
        if not heatmap.empty and {"common_name", "hour", "detections"}.issubset(heatmap.columns):
            heatmap["hour_label"] = pd.to_datetime(heatmap["hour"], errors="coerce").dt.strftime("%H")
            heatmap = heatmap.dropna(subset=["hour_label"])
            rhythm = (
                alt.Chart(heatmap)
                .mark_rect(cornerRadius=2)
                .encode(
                    x=alt.X("hour_label:O", title="Hour", axis=alt.Axis(labelAngle=0)),
                    y=alt.Y("common_name:N", title=None, sort="-x"),
                    color=alt.Color("detections:Q", scale=alt.Scale(range=["#edf1ea", "#2f6545"]), legend=None),
                    tooltip=["common_name:N", alt.Tooltip("hour_label:O", title="Hour"), "detections:Q"],
                )
                .properties(height=max(230, heatmap["common_name"].nunique() * 29))
                .configure_view(stroke=None)
                .configure_axis(domain=False, tickColor=GRID, labelColor=MUTED, titleColor=MUTED)
            )
            st.altair_chart(rhythm, width="stretch")
        else:
            empty_state(wording(copy.get("sections", {}), "rhythm", "empty", "Activity patterns will appear as detections arrive."))

with right:
    with st.container(border=True):
        panel_heading(wording(copy.get("sections", {}), "recent", "title", "Recently heard"), wording(copy.get("sections", {}), "recent", "description", "Latest confident matches. Recordings stay private."))
        recent = data.get("recent", [])[:8]
        if recent:
            rows = []
            for item in recent:
                confidence = item.get("confidence")
                score = "" if confidence is None else f"{float(confidence):.0%}"
                rows.append(
                    f'<div class="recent-row"><div class="recent-time">{esc(clock(item.get("detected_at")))}</div>'
                    f'<div><div class="recent-name">{esc(item.get("common_name") or item.get("scientific_name"))}</div>'
                    f'<div class="recent-latin">{esc(item.get("scientific_name"))}</div></div>'
                    f'<div class="recent-score">{esc(score)}</div></div>'
                )
            st.markdown("".join(rows), unsafe_allow_html=True)
        else:
            empty_state(wording(copy.get("sections", {}), "recent", "empty", "Recent detections will appear here."))

st.markdown(
    f'<div class="method-note"><strong>{esc(wording(copy, "method", "title", "About these numbers."))}</strong> '
    f'{esc(wording(copy, "method", "body", "BirdNET can record the same bird more than once. These charts show detected calls, not a count of individual birds. Less certain matches are held back for checking."))}</div>',
    unsafe_allow_html=True,
)
st.markdown(
    f'<footer class="footer"><span>{esc(wording(copy, "footer", "location", "North West Wales Garden · approximate location only"))}</span>'
    f'<span>{esc(wording(copy, "footer", "data", "Privacy-filtered data · refreshed every 10 minutes"))}</span></footer>',
    unsafe_allow_html=True,
)
