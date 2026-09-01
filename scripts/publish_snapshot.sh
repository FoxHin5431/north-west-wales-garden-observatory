#!/usr/bin/env bash
set -euo pipefail

source_repo="${PUBLIC_REPO_DIR:?Set PUBLIC_REPO_DIR to the main application clone}"
data_repo="${PUBLIC_DATA_REPO_DIR:?Set PUBLIC_DATA_REPO_DIR to the data-branch clone}"
cd "$source_repo"

"${EXPORT_PYTHON:-python3}" exporter/export_public_snapshot.py

# The data branch contains one file and one replaceable commit. Amending avoids
# building an ever-growing public history from ten-minute observations.
cd "$data_repo"
git add -- public_snapshot.json
if git diff --cached --quiet; then
  exit 0
fi

git commit --amend --no-edit
git push --quiet --force-with-lease origin data
