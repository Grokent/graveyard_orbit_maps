using HarmonyLib;
using Newtonsoft.Json.Linq;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEngine;

namespace GraveyardOrbit.UfoCow
{
    /// <summary>
    /// Loads every map/contract pair listed in <see cref="MapIds"/> from the
    /// plugin folder and inserts the missing ones into the live
    /// StructureCatalog. Ships COW ABDUCTION and BATTLE MOON.
    /// </summary>
    internal static class UfoCowInject
    {
        internal static bool Done { get; private set; }

        private static readonly string[] MapIds = { "ufo_cow", "battle_moon" };

        private static readonly HashSet<string> _errorLogged = new HashSet<string>();

        internal static void EnsureInjected()
        {
            if (Done) return;

            StructureCatalog catalog = StructureCatalog.I;
            if (catalog == null) return;

            foreach (string id in MapIds)
            {
                if (Has(catalog.campaign, id) || Has(catalog.ladder, id)) continue;
                InjectOne(catalog, id);
            }

            bool all = true;
            foreach (string id in MapIds)
            {
                if (!Has(catalog.campaign, id) && !Has(catalog.ladder, id)) all = false;
            }
            Done = all;
        }

        private static void InjectOne(StructureCatalog catalog, string id)
        {
            string dir = Path.GetDirectoryName(typeof(UfoCowPlugin).Assembly.Location);
            string mapPath = Path.Combine(dir ?? ".", "maps", id + ".json");
            string contractPath = Path.Combine(dir ?? ".", "contracts", id + ".contract.json");
            if (!File.Exists(mapPath) || !File.Exists(contractPath))
            {
                if (_errorLogged.Add(id))
                {
                    UfoCowPlugin.Log.LogError(
                        "[ufocow] missing data for '" + id + "'. Expected:\n  "
                        + mapPath + "\n  " + contractPath);
                }
                return;
            }

            string mapJson = File.ReadAllText(mapPath);
            JObject c = JObject.Parse(File.ReadAllText(contractPath));

            // Cheap sanity check using the game's own parser.
            MegastructureData check = MegastructureData.FromJson(mapJson);

            var def = ScriptableObject.CreateInstance<StructureDef>();
            def.name = (string)c["id"];
            def.id = (string)c["id"];
            def.displayName = (string)c["displayName"];
            def.description = (string)c["description"];
            def.cellCount = check.count;
            def.sealedLayers = (bool?)c["sealedLayers"] ?? false;
            def.startingMoney = (int?)c["startingMoney"] ?? 0;
            def.glyphCount = (int?)c["glyphCount"] ?? 0;
            def.greenCount = (int?)c["greenCount"] ?? -1;
            def.cells = new TextAsset(mapJson);

            JArray bands = c["bands"] as JArray;
            def.bands = bands == null ? new BandDef[0] : bands.Select(b => new BandDef
            {
                layer = (int)b["layer"],
                outerFrac = (float?)b["outerFrac"] ?? 1f,
                hpSealed = (int?)b["hpSealed"] ?? 75,
                special1 = (int?)b["special1"] ?? 0,
                special2 = (int?)b["special2"] ?? 0,
                special3 = (int?)b["special3"] ?? 0,
                meta1 = (int?)b["meta1"] ?? 0,
                explosive = (int?)b["explosive"] ?? 0,
                lightning = (int?)b["lightning"] ?? 0,
                voidTiles = (int?)b["voidTiles"] ?? 0,
                swarm = (int?)b["swarm"] ?? 0,
                unsealedLook = (int?)b["unsealedLook"] ?? 0,
            }).ToArray();

            JArray artifacts = c["artifactCells"] as JArray;
            def.artifactCells = artifacts == null
                ? new Vector2Int[0]
                : artifacts.Select(a => new Vector2Int((int)a[0], (int)a[1])).ToArray();

            int contractCount = (int?)c["cellCount"] ?? -1;
            if (contractCount != check.count)
            {
                UfoCowPlugin.Log.LogWarning(
                    $"[ufocow] '{id}' contract cellCount {contractCount} != map count {check.count}; using {check.count}");
            }

            catalog.campaign = Prepend(catalog.campaign, def);
            catalog.ladder = Prepend(catalog.ladder, def);

            var cacheField = AccessTools.Field(typeof(StructureCatalog), "_cache");
            if (cacheField?.GetValue(null) is Dictionary<string, StructureDef> cache)
            {
                cache[def.id] = def;
            }

            UfoCowPlugin.Log.LogInfo(
                $"[ufocow] injected '{def.id}' ({check.count:N0} cells, {def.bands.Length} bands)");
        }

        private static bool Has(StructureDef[] list, string id)
        {
            if (list == null) return false;
            foreach (StructureDef d in list)
            {
                if (d != null && d.id == id) return true;
            }
            return false;
        }

        private static StructureDef[] Prepend(StructureDef[] list, StructureDef def)
        {
            var outList = new List<StructureDef> { def };
            if (list != null) outList.AddRange(list);
            return outList.ToArray();
        }
    }
}
