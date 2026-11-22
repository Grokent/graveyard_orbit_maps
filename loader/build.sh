#!/usr/bin/env bash
# Build the COW ABDUCTION loader plugin with the project-local .NET SDK.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="$(cd "$ROOT/.." && pwd)"

DOTNET="${DOTNET:-$PROJECT/tools/dotnet}"
if [[ ! -x "$DOTNET/dotnet" ]]; then
  DOTNET="$(command -v dotnet || true)"
fi
[[ -n "$DOTNET" ]] || { echo "No dotnet SDK found. Set DOTNET=/path/to/dotnet." >&2; exit 1; }

export DOTNET_ROOT="$DOTNET"
export PATH="$DOTNET:$PATH"
export DOTNET_CLI_TELEMETRY_OPTOUT=1
export DOTNET_NOLOGO=1

dotnet build "$ROOT/GraveyardOrbit.UfoCow.csproj" -c Release "$@"
