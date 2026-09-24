#!/usr/bin/env bash
set -euo pipefail

# CapMesh — 60-Second Adversarial Judging Demo Runner
# TUM Blockchain & AI Hackathon (Munich, Oct 2026)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"

# Activate virtualenv if present
if [[ -f ".venv/bin/activate" ]]; then
    source .venv/bin/activate
fi

echo "================================================================="
echo "   Launching CapMesh Adversarial Judging Demo"
echo "================================================================="

# Pass through arguments (e.g. --simulated, --timeout 4)
python -m capmesh.agent.demo "$@"
