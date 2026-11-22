using BepInEx;
using BepInEx.Logging;
using GraveyardOrbit.UI;
using HarmonyLib;
using System;

namespace GraveyardOrbit.UfoCow
{
    [BepInPlugin(PluginGuid, "Graveyard Orbit — COW ABDUCTION", PluginVersion)]
    public sealed class UfoCowPlugin : BaseUnityPlugin
    {
        public const string PluginGuid = "agentbox.graveyardorbit.ufocow";
        public const string PluginVersion = "0.1.0";

        internal static ManualLogSource Log;
        private Harmony _harmony;

        private void Awake()
        {
            Log = Logger;
            _harmony = new Harmony(PluginGuid);
            try { _harmony.PatchAll(typeof(UfoCowPlugin).Assembly); }
            catch (Exception ex) { Log.LogError("patch failed: " + ex); }

            // Do NOT touch Resources/Unity objects here. BepInEx loads plugins
            // before Unity is ready, and Resources.Load from Awake crashes the
            // process. The menu patch injects once the title menu is built.
        }

        internal static void Inject()
        {
            try { UfoCowInject.EnsureInjected(); }
            catch (Exception ex) { Log.LogError("inject failed: " + ex); }
        }

        private void OnDestroy()
        {
            try { _harmony?.UnpatchSelf(); } catch { }
        }
    }

    /// <summary>Inject the contract again whenever the title menu is rebuilt.</summary>
    [HarmonyPatch(typeof(MainMenuController), "BuildUI")]
    internal static class MenuBuildPatch
    {
        private static void Postfix()
        {
            UfoCowPlugin.Inject();
        }
    }
}
