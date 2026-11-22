#!/usr/bin/env bash
# Copy the loader + map data into the Graveyard Orbit BepInEx plugins folder.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="$(cd "$ROOT/.." && pwd)"
GAME="${GAME_DIR:-$HOME/.local/share/Steam/steamapps/common/Graveyard Orbit}"
DLL="$ROOT/bin/Release/GraveyardOrbit.UfoCow.dll"
DEST="$GAME/BepInEx/plugins/GraveyardOrbit.UfoCow"

[[ -d "$GAME/BepInEx" ]] || { echo "BepInEx not found in $GAME" >&2; exit 1; }
[[ -f "$DLL" ]] || { echo "Build first: ./build.sh" >&2; exit 1; }

mkdir -p "$DEST/maps" "$DEST/contracts"
cp -f "$DLL" "$DEST/"
cp -f "$PROJECT/maps/ufo_cow.json" "$DEST/maps/"
cp -f "$PROJECT/contracts/ufo_cow.contract.json" "$DEST/contracts/"

echo "Deployed -> $DEST"
echo "  GraveyardOrbit.UfoCow.dll"
echo "  maps/ufo_cow.json"
echo "  contracts/ufo_cow.contract.json"
echo
echo "Launch the game and look for COW ABDUCTION at the top of the contract list."
echo "Log: $GAME/BepInEx/LogOutput.log  (grep ufocow)"
