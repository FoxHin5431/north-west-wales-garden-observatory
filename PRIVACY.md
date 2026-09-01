# Privacy boundary

The repository is designed to be public.

Allowed public data:

- `North West Wales Garden` as the only location label
- cleaned aggregate bird detections
- scientific and common species names
- observation times and confidence values for accepted detections
- broad weather values
- calculated dawn and sunrise times

Never publish:

- latitude, longitude, address, map pin, or exact locality
- LAN/WAN addresses, hostnames, usernames, ports, or filesystem layout
- API credentials, GitHub tokens, SSH keys, or Streamlit secrets
- SQLite databases or raw BirdNET rows
- audio, spectrograms, clip names, or media paths
- Possible/Review detections awaiting manual validation

The exporter is the trust boundary. Any new field must be reviewed before it is added to `data/public_snapshot.json`.

