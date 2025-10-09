#!/bin/bash
set -ex

# Pre-package script for mcp-servers helm chart
# This script patches the toolhive-operator subchart before packaging

CHART_DIR="$1"

if [ -z "$CHART_DIR" ]; then
  echo "Usage: $0 <chart-directory>"
  exit 1
fi

echo "Running pre-package script for mcp-servers"

# Patch toolhive-operator subchart if it exists (excluding CRDs)
TOOLHIVE_TGZ=$(ls "$CHART_DIR/charts/toolhive-operator-"*.tgz 2>/dev/null | grep -v "crds" || true)
if [ -n "$TOOLHIVE_TGZ" ]; then
  echo "Patching toolhive-operator subchart"
  TEMP_DIR=$(mktemp -d)
  tar -xzf "$TOOLHIVE_TGZ" -C "$TEMP_DIR"

  # Convert ClusterRole to Role in role.yaml
  sed -i 's/kind: ClusterRole/kind: Role/' \
    "$TEMP_DIR/toolhive-operator/templates/clusterrole/role.yaml"

  # Re-package the modified chart
  rm "$TOOLHIVE_TGZ"
  tar -czf "$TOOLHIVE_TGZ" -C "$TEMP_DIR" toolhive-operator
  rm -rf "$TEMP_DIR"

  echo "Toolhive-operator subchart patched successfully"
else
  echo "No toolhive-operator subchart found, skipping patch"
fi

echo "Pre-package script completed"
