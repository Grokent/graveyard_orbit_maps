#!/usr/bin/env bash
# Copy the loader + map data into the Graveyard Orbit BepInEx plugins folder.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="$(cd "$ROOT/.." && pwd)"
GAME="${GAME_DIR:-$HOME/.local/share/Steam/steamapps/common/Graveyard Orbit}"
DLL="$ROOT/bin/Release/GraveyardOrbit.UfoCow.dll"
DEST="$GAME/BepInEx/plugins/GraveyardOrbit.UfoCow"
MAPS=(ufo_cow battle_moon)

[[ -d "$GAME/BepInEx" ]] || { echo "BepInEx not found in $GAME" >&2; exit 1; }
[[ -f "$DLL" ]] || { echo "Build first: ./build.sh" >&2; exit 1; }

mkdir -p "$DEST/maps" "$DEST/contracts"
cp -f "$DLL" "$DEST/"

for id in "${MAPS[@]}"; do
  [[ -f "$PROJECT/maps/$id.json" ]] || { echo "missing maps/$id.json" >&2; exit 1; }
  [[ -f "$PROJECT/contracts/$id.contract.json" ]] || { echo "missing contracts/$id.contract.json" >&2; exit 1; }
  cp -f "$PROJECT/maps/$id.json" "$DEST/maps/"
  cp -f "$PROJECT/contracts/$id.contract.json" "$DEST/contracts/"
done

echo "Deployed -> $DEST"
echo "  GraveyardOrbit.UfoCow.dll"
for id in "${MAPS[@]}"; do
  echo "  maps/$id.json"
  echo "  contracts/$id.contract.json"
done
echo
echo "Launch the game; the injected contracts appear at the top of the list."
echo "Log: $GAME/BepInEx/LogOutput.log  (grep ufocow)"
