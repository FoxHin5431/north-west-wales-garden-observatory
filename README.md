# North West Wales Garden Observatory

A live Streamlit view of acoustic bird activity from a garden in North West Wales.

The public app deliberately publishes only a cleaned JSON snapshot and a small, attributed species reference image. It does **not** publish precise coordinates, garden photographs, raw BirdNET databases, audio, spectrograms, clip paths, host details, credentials, or lower-confidence review data.

## Run the public app

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1`.

## Public data boundary

The generated public data consists of `data/public_snapshot.json` and, when available, one species reference image. It contains:

- the broad label `North West Wales Garden`
- cleaned Strong and Probable detections
- aggregate hourly and species counts
- a short recent-detections list without IDs or media
- broad weather observations
- civil dawn and sunrise times
- a BirdNET-Go species thumbnail with its supplied photographer and licence details

The exporter requires exact coordinates only while it runs privately on the garden monitor to calculate solar times. Coordinates are never written to the snapshot.

## Private exporter configuration

Install the exporter dependencies on the private monitor with `requirements-exporter.txt`, then provide these environment variables outside the repository:

```text
BIRDNET_DB=/private/path/to/birdnet.db
WEATHER_DB=/private/path/to/weather.db
GARDEN_LATITUDE=<private latitude>
GARDEN_LONGITUDE=<private longitude>
PUBLIC_SNAPSHOT_PATH=/path/to/data-branch-clone/public_snapshot.json
PUBLIC_REPO_DIR=/path/to/main-application-clone
PUBLIC_DATA_REPO_DIR=/path/to/data-branch-clone
EXPORT_PYTHON=/path/to/python
```

Never commit that environment file. `scripts/publish_snapshot.sh` updates only the public snapshot on a dedicated `data` branch. It amends one replaceable commit so ten-minute updates do not create an ever-growing Git history.

On a Pi with user lingering enabled, the files in `deploy/user` can be copied to `~/.config/systemd/user/` and enabled without root access.

## Deploy on Streamlit Community Cloud

1. Push this repository to GitHub.
2. In Streamlit Community Cloud, create an app from the repository.
3. Set the entry point to `app.py`.
4. Deploy. No Streamlit secrets are required for the public page.

The app checks the privacy-safe `data` branch every five minutes. The page itself refreshes every ten minutes.

## Edit the page wording

All visible headings and explanatory text live in [`content/site_text.json`](content/site_text.json). Edit that one file in GitHub and commit the change; Streamlit will update the page automatically.

The content file is separate from the Python layout, so changing the wording cannot expose the private database, recordings, or coordinates. Keep the location description broad when editing it.

## Interpretation

BirdNET detections measure acoustic activity. Multiple detections can come from one bird, so the figures must not be interpreted as abundance or individual bird counts.
