#!/usr/bin/env bash
# Compatibility wrapper for the repository-level product shell launcher.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
exec "$ROOT/start.sh"
