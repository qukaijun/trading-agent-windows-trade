# TradingAgents Trade Frontend

React + Vite trading workbench for the local TradingAgents trade edition.

## What It Provides

- Beginner-friendly strategy draft assistant
- Gold, silver, BTC, and ETH watchlist
- K-line chart view with `lightweight-charts`
- AI analysis result review
- MT5 signal sending panel
- Scheduler status and controls

## Development

```powershell
npm install
npm run dev
```

The Vite dev server proxies `/api` and `/health` to `http://127.0.0.1:8787`.

## Build

```powershell
npm run build
```

## Safety Notes

- The UI defaults to demo-mode workflows.
- Live trading must be explicitly enabled by the backend configuration.
- Natural-language input currently creates a structured strategy draft; a full strategy compiler backend is future work.
