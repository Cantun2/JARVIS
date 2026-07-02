import { useState } from "react";
import { motion } from "framer-motion";
import Clock from "./components/Clock";
import ConnectionBadge from "./components/ConnectionBadge";
import Dashboard from "./components/Dashboard";
import InboxPanel from "./components/InboxPanel";
import BriefingPanel from "./components/BriefingPanel";
import TabBar, { type TabId } from "./components/TabBar";
import { useEventStream } from "./lib/ws";

/**
 * Racine de l'app. `base` vide => same-origin : en dev le proxy Vite renvoie
 * /api et /ws vers VITE_API_BASE ; en prod le front est servi par le core.
 * Navigation par onglets ; instance unique de `useEventStream` conservée ici,
 * chaque vue étant dérivée du même flux `events`.
 */
export default function App(): JSX.Element {
  const { events, agents, health, connected } = useEventStream("");
  const [tab, setTab] = useState<TabId>("dashboard");

  return (
    <main className="flex h-full flex-col gap-4 p-4 md:p-6">
      <motion.header
        className="hud-panel flex flex-wrap items-center justify-between gap-4 px-4 py-3 md:px-6"
        initial={{ opacity: 0, y: -12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
      >
        <div className="flex items-center gap-6">
          <div>
            <div className="text-sm font-bold tracking-[0.3em] text-hud-cyan">JARVIS</div>
            <div className="hud-label">Mission Control</div>
          </div>
          <TabBar active={tab} onChange={setTab} />
        </div>
        <div className="flex items-center gap-4">
          <Clock />
          <ConnectionBadge connected={connected} health={health} />
        </div>
      </motion.header>

      <div className="flex min-h-0 flex-1 flex-col">
        {tab === "dashboard" && (
          <Dashboard events={events} agents={agents} health={health} />
        )}
        {tab === "inbox" && <InboxPanel events={events} />}
        {tab === "briefing" && <BriefingPanel events={events} />}
      </div>
    </main>
  );
}
