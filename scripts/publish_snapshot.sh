#!/usr/bin/env bash
set -euo pipefail

repo_dir="${PUBLIC_REPO_DIR:?Set PUBLIC_REPO_DIR to the local clone of the public repository}"
cd "$repo_dir"

"${EXPORT_PYTHON:-python3}" exporter/export_public_snapshot.py

# This is intentionally the only generated data file added by the publisher.
git add -- data/public_snapshot.json
if git diff --cached --quiet; then
  exit 0
fi

git commit -m "data: refresh public garden snapshot"
git push --quiet origin HEAD

