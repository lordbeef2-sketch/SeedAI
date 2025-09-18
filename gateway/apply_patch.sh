#!/usr/bin/env bash
# apply_patch.sh - helper to copy files from this package into a target repo path
# Usage: ./apply_patch.sh /path/to/SeedAI/repo
TARGET="$1"
if [ -z "$TARGET" ]; then
  echo "Usage: $0 /path/to/SeedAI/repo"
  exit 1
fi
cp seedai_storage.py "$TARGET/seedai_storage.py"
cp integration_example.py "$TARGET/integration_example.py"
cp README_patch.txt "$TARGET/README_patch.txt"
echo "Copied patch files into $TARGET. Edit your server startup to call seedai_storage.init_db()"
