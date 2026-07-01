import Dashboard from "./components/Dashboard";
import { useEventStream } from "./lib/ws";

/**
 * Racine de l'app. `base` vide => same-origin : en dev le proxy Vite renvoie
 * /api et /ws vers VITE_API_BASE ; en prod le front est servi par le core.
 */
export default function App(): JSX.Element {
  const { events, agents, health, connected } = useEventStream("");

  return (
    <main className="h-full">
      <Dashboard events={events} agents={agents} health={health} connected={connected} />
    </main>
  );
}
