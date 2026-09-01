#!/usr/bin/env bash
set -euo pipefail

source_repo="${PUBLIC_REPO_DIR:?Set PUBLIC_REPO_DIR to the main application clone}"
data_repo="${PUBLIC_DATA_REPO_DIR:?Set PUBLIC_DATA_REPO_DIR to the data-branch clone}"
cd "$source_repo"

"${EXPORT_PYTHON:-python3}" exporter/export_public_snapshot.py

# The data branch contains only the snapshot and current species thumbnail in
# one replaceable commit. Amending avoids an ever-growing public history.
cd "$data_repo"
git add -- public_snapshot.json
git add -u -- 'latest_species_*' 2>/dev/null || true
for image in latest_species_*.jpg latest_species_*.png latest_species_*.webp; do
  if [[ -f "$image" ]]; then
    git add -- "$image"
  fi
done
if git diff --cached --quiet; then
  exit 0
fi

git commit --amend --no-edit
git push --quiet --force-with-lease origin data
