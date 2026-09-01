# North West Wales Garden Observatory

A privacy-safe public Streamlit view of acoustic bird activity from a garden in North West Wales.

The public app deliberately publishes only a cleaned JSON snapshot. It does **not** publish precise coordinates, raw BirdNET databases, audio, spectrograms, clip paths, host details, credentials, or lower-confidence review data.

## Run the public app

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1`.

## Public data boundary

`data/public_snapshot.json` is the only generated file intended for publication. It contains:

- the broad label `North West Wales Garden`
- cleaned Strong and Probable detections
- aggregate hourly and species counts
- a short recent-detections list without IDs or media
- broad weather observations
- civil dawn and sunrise times

The exporter requires exact coordinates only while it runs privately on the garden monitor to calculate solar times. Coordinates are never written to the snapshot.

## Private exporter configuration

Install the exporter dependencies on the private monitor with `requirements-exporter.txt`, then provide these environment variables outside the repository:

```text
BIRDNET_DB=/private/path/to/birdnet.db
WEATHER_DB=/private/path/to/weather.db
GARDEN_LATITUDE=<private latitude>
GARDEN_LONGITUDE=<private longitude>
PUBLIC_SNAPSHOT_PATH=/path/to/repository/data/public_snapshot.json
PUBLIC_REPO_DIR=/path/to/repository
EXPORT_PYTHON=/path/to/python
```

Never commit that environment file. `scripts/publish_snapshot.sh` updates and pushes only the public snapshot.

## Deploy on Streamlit Community Cloud

1. Push this repository to GitHub.
2. In Streamlit Community Cloud, create an app from the repository.
3. Set the entry point to `app.py`.
4. Deploy. No Streamlit secrets are required for the public page.

Each privacy-safe snapshot pushed by the garden monitor triggers Streamlit to update the app.

## Interpretation

BirdNET detections measure acoustic activity. Multiple detections can come from one bird, so the figures must not be interpreted as abundance or individual bird counts.

