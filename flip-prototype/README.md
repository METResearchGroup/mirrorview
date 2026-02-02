## MirrorView — Flip Prototype (Frontend Only)

Prototype UI to demonstrate a “post flipping” workflow:

- Paste a post
- Click **Flip** (mocked client-side transform)
- Give **thumbs up / thumbs down**
- If thumbs down, write **your version** and **Submit** (still mocked; no network)

This repo currently contains **no backend** by design. The LLM-powered flip will be added later.

## Getting Started

Install dependencies and run the dev server:

```bash
npm install
npm run dev
```

Open `http://localhost:3000` in your browser.

### Key files

- `app/page.tsx`: main UI (input → flip → result → feedback → optional custom version)
- `lib/mockFlip.ts`: deterministic mock flip logic
- `app/layout.tsx`: app layout + toasts

### Production build

```bash
npm run build
```

## Deploy to Vercel

This app is designed to deploy cleanly to Vercel with **no environment variables**.

### If this repo is deployed as a monorepo

When importing the Git repo into Vercel, set:

- **Root Directory**: `flip-prototype`
- **Build Command**: `npm run build` (default)
- **Output**: Next.js (auto-detected)

Then click **Deploy**.

## Notes

- Feedback submission currently just logs to the console and shows a toast.
- When the backend is added, the flip action will call an API endpoint and the feedback will be persisted.
