# PDF Reader Helper

AI-powered PDF reading assistant with Google Gemini. Available as a **[web app](https://reader-helper.vercel.app)** and a **local desktop app** (PyQt6).

Inspired by [Andrej Karpathy's reader3](https://github.com/karpathy/reader3), but with a focus on reading scientific papers. Select any text or region, send it to Gemini, and get instant explanations. I would like to add support for all sorts of providers later on, but I mainly used Gemini for its document upload feature. I can see this working with openrouter, but maybe a bit into the future (depends on demand, I guess). Please let me know through issues what you think is a problem, or what a good feature could be. Happy to have PRs as well.

---

## Web App

Live at **[reader-helper.vercel.app](https://reader-helper.vercel.app)**

New visitors get **10 free messages** powered by my API key (to get started, but this will be removed soon). After that, bring your own free Gemini key from [Google AI Studio](https://aistudio.google.com/apikey).

### Features

- Upload any PDF up to 4 MB — sent directly to Gemini, nothing stored on the server
- Click and drag to select text or an image region, then click **Explain this**
- Full chat interface with streaming responses and markdown rendering
- Quick follow-up buttons: Simpler / Example / Why important
- Per-PDF conversation history and notes, persisted in the browser
- Model selector (Gemini Flash, Flash Thinking, Pro)
- Remembers last page and zoom level per PDF

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

A fully local PyQt6 application. Everything runs on your machine. Just download from releases (I recommedn the webapp though, the desktop app does not look as great.)

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

Issues and PRs are welcome. MIT licensed: use it however you like.
