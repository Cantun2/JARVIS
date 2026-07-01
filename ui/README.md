# jarvis-suit · UI (Mission Control)

HUD web "Stark Industries" pour jarvis-suit. Vite + React 18 + TypeScript (strict)
+ TailwindCSS + framer-motion + Recharts. Tests Vitest + @testing-library/react.

## Démarrage

```bash
cd ui
npm install
npm run dev      # http://localhost:5173 (proxy /api + /ws vers VITE_API_BASE)
npm run build    # tsc -b + vite build -> dist/
npm run test -- --run
npm run lint     # optionnel
```

## Configuration

- `VITE_API_BASE` (défaut `http://127.0.0.1:8000`) : base du backend FastAPI.
  Copier `.env.example` en `.env.local` pour surcharger.
- En dev, le proxy Vite renvoie `/api` (REST) et `/ws` (WebSocket) vers cette base.

## Structure

- `src/lib/` : `types.ts` (miroir du contrat de câble), `api.ts` (REST typé),
  `ws.ts` (hook `useEventStream` + fonction pure `applyWsMessage`), `theme.ts`
  (mappings couleur statut/type).
- `src/components/` : `Dashboard`, `Clock`, `ConnectionBadge`, `AgentStatusArc`,
  `EventFeed`, `EventRow`.
- `src/test/` : tests Vitest (jsdom).
- `src-tauri/` : scaffold Tauri (config uniquement). **Packaging différé** :
  webkit2gtk absent sur la machine de dev, ne pas lancer `tauri dev/build` ici.
  Voir `docs/MANUAL_SETUP.md`.
