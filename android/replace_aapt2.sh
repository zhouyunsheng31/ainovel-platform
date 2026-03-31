#!/bin/bash
AAPT2_ARM64="/storage/emulated/0/Download/Operit/workspace/workspace_backup/workspace_backup/android/tools/aapt2-arm64"
find /root/.gradle/caches -name "aapt2" -type f 2>/dev/null | while read f; do
  echo "Replacing: $f"
  cp "$AAPT2_ARM64" "$f"
  chmod +x "$f"
done
echo "AAPT2 replacement complete"
