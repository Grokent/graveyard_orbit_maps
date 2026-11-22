#!/usr/bin/env bash
# Project-local build tools. Nothing is installed system-wide.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ ! -x "$ROOT/tools/dotnet/dotnet" ]]; then
  echo "Installing portable .NET 9 SDK into tools/dotnet ..."
  "$ROOT/tools/dotnet-install.sh" --channel 9.0 --install-dir "$ROOT/tools/dotnet" --no-path
fi

BEP="$ROOT/tools/BepInEx_win_x64_5.4.23.6.zip"
if [[ ! -f "$BEP" ]]; then
  echo "Downloading BepInEx 5.4.23.6 ..."
  curl -sSL -o "$BEP" \
    https://github.com/BepInEx/BepInEx/releases/download/v5.4.23.6/BepInEx_win_x64_5.4.23.6.zip
fi
if [[ ! -f "$ROOT/tools/BepInEx/BepInEx/core/BepInEx.dll" ]]; then
  unzip -oq "$BEP" -d "$ROOT/tools/BepInEx"
fi

echo
echo "Toolchain ready. Next:"
echo "  ./loader/build.sh"
echo "  ./loader/deploy.sh   # local test install"
echo "  ./package.sh         # redistributable zip"
