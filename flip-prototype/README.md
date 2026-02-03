## MirrorView — Flip Prototype (Next.js)

Prototype UI to demonstrate a “post flipping” workflow:

- Paste a post
- Click **Flip** (calls the backend API)
- Give **thumbs up / thumbs down**
- If thumbs down, write **your version** and **Submit** (still mocked; no network)

This UI is designed to call the FastAPI backend endpoint `POST /generate_response`.

## Getting Started

Install dependencies and run the dev server:

```bash
npm install
npm run dev
```

Open `http://localhost:3000` in your browser.

### Configure backend URL

Set `NEXT_PUBLIC_API_URL` to your backend base URL.

Local dev example (FastAPI on port 8000):

```bash
export NEXT_PUBLIC_API_URL="http://localhost:8000"
npm run dev
```

### Key files

- `app/page.tsx`: main UI (input → flip → result → feedback → optional custom version)
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
- Flip calls `POST /generate_response` on the backend and displays `flipped_text`.
