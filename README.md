# PDF Reader Helper

AI-powered PDF reading assistant with Google Gemini. Available as a **web app** (deployed on Vercel) and a **local desktop app** (PyQt6).

Inspired by [Andrej Karpathy's reader3](https://github.com/karpathy/reader3) — built with a focus on reading scientific papers rather than books. Select any text or region, send it to Gemini, and get instant explanations.

---

## Web App

Live at **[reader-helper.vercel.app](https://reader-helper.vercel.app)**

New visitors get **10 free messages** powered by the developer's API key. After that, bring your own free Gemini key from [Google AI Studio](https://aistudio.google.com/apikey).

### Features

- Upload any PDF up to 4 MB — sent directly to Gemini, nothing stored on the server
- Click and drag to select text or an image region, then click **Explain this**
- Full chat interface with streaming responses and markdown rendering
- Quick follow-up buttons: Simpler / Example / Why important
- Per-PDF conversation history and notes, persisted in the browser
- Model selector (Gemini Flash, Flash Thinking, Pro)
- Remembers last page and zoom level per PDF

### Self-hosting on Vercel

1. Fork the repo and import it into Vercel, setting the **root directory** to `web/`

2. Add these environment variables in **Vercel → Settings → Environment Variables** (no quotes around values):

   | Variable | Description |
   |---|---|
   | `GEMINI_API_KEY` | Your Gemini API key — used for the free tier |
   | `UPSTASH_REDIS_REST_URL` | Upstash Redis REST URL (e.g. `https://xxx.upstash.io`) |
   | `UPSTASH_REDIS_REST_TOKEN` | Upstash Redis REST token |

   Create a free Redis database at [upstash.com](https://upstash.com) — no setup needed, keys are created automatically on first use.

   If you omit the Redis/Gemini vars, the app still works but requires every visitor to supply their own API key.

3. Redeploy — the free tier will be active immediately.

### Local development

```bash
cd web
npm install
npm run dev
```

For local free-tier testing, create `web/.env.local`:
```
GEMINI_API_KEY=your_key_here
UPSTASH_REDIS_REST_URL=https://xxx.upstash.io
UPSTASH_REDIS_REST_TOKEN=your_token_here
```

---

## Desktop App

A fully local PyQt6 application — no server, no deployment. Everything runs on your machine.

### Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Add your API key
echo "GEMINI_API_KEY=your_key_here" > .env

# Run
python main.py
```

Or use the setup script:
```bash
./setup.sh   # creates .venv, installs deps, prompts for API key
./run.sh     # activates venv and runs the app
```

### Features

- All web app features, plus:
- Native OS file picker
- Adjustable chat font size
- Document analysis and complex term detection
- All data stored locally as JSON files

### Architecture

| Module | Responsibility |
|---|---|
| `main.py` | Main window, PDF loading/navigation, worker lifecycle |
| `utils.py` | Constants, file I/O, config, hash, markdown→HTML |
| `gemini_worker.py` | Background thread for streaming Gemini calls |
| `widgets.py` | PDF page rendering, text/image selection |
| `panels.py` | Chat UI, notes panel |

---

## Tech Stack

**Web:** Next.js · React · Material UI · Gemini API · Upstash Redis · Vercel  
**Desktop:** Python · PyQt6 · PyMuPDF · google-genai SDK

---

## Contributing

Issues and PRs are welcome. MIT licensed — use it however you like.
