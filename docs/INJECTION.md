# Injecting the map as a contract

`StructureCatalog` is a ScriptableObject asset populated at startup. To add a
contract at runtime, follow the pattern below from a Harmony postfix on
`MainMenuController.BuildUI` (as the included loader does). Do not run it from a
plugin `Awake` — BepInEx loads plugins before Unity resources are ready, and
`StructureCatalog.I` will crash the process there. It is the same approach the
Graveyard Orbit co-op mod used for its combined contract.

```csharp
using System;
using System.IO;
using System.Linq;
using GraveyardOrbit;
using Newtonsoft.Json.Linq;
using UnityEngine;
using HarmonyLib;

static void InjectCowAbduction(string pluginDir)
{
    string contractJson = File.ReadAllText(
        Path.Combine(pluginDir, "contracts", "ufo_cow.contract.json"));
    string mapJson = File.ReadAllText(
        Path.Combine(pluginDir, "maps", "ufo_cow.json"));

    var c = JObject.Parse(contractJson);

    // Fail early if the map JSON is malformed; the game parses this same text.
    MegastructureData check = MegastructureData.FromJson(mapJson);

    var def = ScriptableObject.CreateInstance<StructureDef>();
    def.id          = (string)c["id"];                  // "ufo_cow"
    def.displayName = (string)c["displayName"];         // "COW ABDUCTION"
    def.description = (string)c["description"];
    def.cellCount   = (int)c["cellCount"];              // must equal check.count
    def.sealedLayers = (bool?)c["sealedLayers"] ?? false;
    def.startingMoney = (int?)c["startingMoney"] ?? 0;
    def.glyphCount  = (int?)c["glyphCount"] ?? 0;
    def.greenCount  = (int?)c["greenCount"] ?? -1;

    def.cells = new TextAsset(mapJson);                 // the map itself

    def.bands = c["bands"].Select(b => new BandDef
    {
        layer       = (int)b["layer"],
        outerFrac   = (float?)b["outerFrac"] ?? 1f,
        hpSealed    = (int?)b["hpSealed"] ?? 75,
        special1    = (int?)b["special1"] ?? 0,
        special2    = (int?)b["special2"] ?? 0,
        special3    = (int?)b["special3"] ?? 0,
        meta1       = (int?)b["meta1"] ?? 0,
        explosive   = (int?)b["explosive"] ?? 0,
        lightning   = (int?)b["lightning"] ?? 0,
        voidTiles   = (int?)b["voidTiles"] ?? 0,
        swarm       = (int?)b["swarm"] ?? 0,
        unsealedLook = (int?)b["unsealedLook"] ?? 0,
    }).ToArray();

    def.artifactCells = (c["artifactCells"] as JArray ?? new JArray())
        .Select(a => new Vector2Int((int)a[0], (int)a[1]))
        .ToArray();

    // Prepend so it is first in the contract list (campaign + ladder).
    StructureCatalog catalog = StructureCatalog.I;
    if (catalog == null) return;
    catalog.campaign = Prepend(catalog.campaign, def);
    catalog.ladder   = Prepend(catalog.ladder, def);

    // StructureCatalog.Resolve uses a private cache; keep it in sync.
    var cacheField = AccessTools.Field(typeof(StructureCatalog), "_cache");
    if (cacheField?.GetValue(null) is System.Collections.Generic.Dictionary<string, StructureDef> cache)
        cache[def.id] = def;
}

static StructureDef[] Prepend(StructureDef[] arr, StructureDef def)
{
    var list = new System.Collections.Generic.List<StructureDef> { def };
    if (arr != null) list.AddRange(arr);
    return list.ToArray();
}
```

## Notes and gotchas

- **Do not call this from a BepInEx plugin's `Awake`/`Start`.** BepInEx loads
  plugins before Unity's `Resources` system is ready; `StructureCatalog.I`
  calls `Resources.Load` and crashes the process there. Inject from a
  `MainMenuController.BuildUI` postfix (as `loader/UfoCowPlugin.cs` does), or
  from any later scene callback. This was the cause of a real startup crash.
- `def.cells` is a `TextAsset`; creating one from the JSON text is what the
  catalog-asset contracts do internally.
- `cellCount` must match the map's `count`; both are 50,221.
- `MegastructureData.FromJson(mapJson)` is a cheap sanity check. If it throws,
  the `bounds` block or a parallel array is wrong.
- If the contract is **not** in `catalog.campaign`, `PaintGreenShards` will not
  add procedural crates and some campaign-only logic is skipped. Appending to
  both `campaign` and `ladder` makes it appear in both contract lists.
- The map is added in memory only; nothing in the game folder or save is
  modified. Removing the plugin removes the contract.
- Place `maps/` and `contracts/` next to your plugin DLL, or bundle the JSON as
  resources.
- `ufo_cow` is not a campaign id; `StructureCatalog.IsCampaign("ufo_cow")`
  returns true once it is in `campaign`, which is what enables green/glyph
  generation. Keep it in `campaign` if you want those.
- This snippet is a starting point, not a built plugin. Compile it against the
  installed game's `Assembly-CSharp.dll` + BepInEx/Harmony, as the co-op mod
  does.
