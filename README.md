# PDF Reader with AI Assistant

Desktop application for reading PDFs with integrated Gemini AI explanations. Built with PyQt6.

This was inspired by Andrej Karpathy's https://github.com/karpathy/reader3.git with a different way to do things. This is a fully local desktop application with a tiny chat window on the side (currently only has support for Gemini with document understanding and file upload) with shortcuts to send pdf content to chat and preset prompts. This was created more in mind to read scientific papers for research and not books as such (Karpathy's version might be better for books). License is MIT, GPL, all of that. I won't sue. I would be happy to collaborate on its development however, so feel free to open issues/PRs.

## Features

**PDF Viewing**
- Standard navigation and zoom controls with customizable default zoom
- Text and image selection
- Page-by-page browsing
- Remembers last page position per PDF

**AI Integration**
- Select text or images to get explanations
- Image support: explain diagrams, charts, figures, and visual elements
- Chat interface with document context and adjustable font size
- Streaming responses with markdown, LaTeX (KaTeX), and table formatting
- Quick actions: simplify explanations, request examples, ask why concepts matter
- Document analysis: summarize content, identify complex terms, suggest reading strategy
- Selected content appears in chat input for review before sending
- Multiple model support (Gemini 3 Flash/Pro, Gemini 2.5 Flash/Pro)

**Notes & History**
- Per-PDF note taking with automatic saving
- Conversation history persisted per document
- Last page position remembered for each PDF

**Resizable UI**
- Horizontal splitter between PDF viewer and chat panel
- Vertical splitter between chat display and input area
- Drag handles to customize layout to your preference

**Caching**
- Files uploaded to Gemini are cached by content hash
- Re-opening the same PDF reuses the uploaded file reference
- Cache persists across sessions (expires after 47 hours)

## Windows Download

Pre-built Windows executables are available on the [Releases](../../releases) page. Download the latest `PDFReaderHelper-windows.zip`, extract it, and run `PDFReaderHelper.exe`.

You will still need to create a `.env` file in the same directory as the executable with your Gemini API key:
```
GEMINI_API_KEY=your_api_key_here
```

## Setup (from source)

1. Get an API key from [Google AI Studio](https://aistudio.google.com/apikey)

2. Run the setup script (creates venv, installs deps, prompts for API key):
   ```bash
   ./setup.sh
   ```

   Or manually:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   echo "GEMINI_API_KEY=your_key" > .env
   ```

3. Run:
   ```bash
   ./run.sh
   # or
   .venv/bin/python main.py
   ```

## Usage

- **Open PDF**: Click "Open PDF" from toolbar
- **Text Selection**: Click and drag to select text, then click "Explain This"
- **Image Selection**: Select a region with diagrams/charts, then click "Explain This Image"
- **Chat**: Ask questions in the chat panel - the AI has access to the full document
- **Quick Actions**: Use "Make Simpler", "Give Example", "Why Important" buttons
- **Analyze**: Click "Analyze Document" for document overview
- **Complex Terms**: Click "Find Complex Terms" to scan current page
- **Font Size**: Adjust chat text size using the font spinner in chat header
- **Zoom**: Use the zoom spinner in the toolbar; click "Set Default Zoom" to save
- **Model**: Switch AI models from the toolbar dropdown; click "Set as Default" to save
- **Resize Panels**: Drag the splitter handles between the PDF viewer and chat, or between the chat display and input area

## Module Structure

```
main.py          - Main application window and entry point
├── utils.py     - Configuration, file operations, markdown conversion
├── gemini_worker.py - AI worker thread for streaming responses
├── widgets.py   - PDF display widget and selection popup
└── panels.py    - Notes and chat UI panels
    └── utils.py - Markdown conversion

tests/
└── test_utils.py - Tests for utility functions
```

## Development

### Linting & Formatting

The project uses [ruff](https://docs.astral.sh/ruff/) for linting and formatting:

```bash
# Check for lint errors
ruff check .

# Auto-fix lint errors
ruff check --fix .

# Check formatting
ruff format --check .

# Apply formatting
ruff format .
```

### Running Tests

```bash
pytest tests/ -v
```

### CI/CD

GitHub Actions workflows are configured for:

- **CI** (`.github/workflows/ci.yml`): Runs on every push to `main` and on pull requests. Checks linting (`ruff check`), formatting (`ruff format --check`), and runs tests (`pytest`).
- **Release** (`.github/workflows/release.yml`): Triggered by pushing a version tag (e.g., `v1.0.0`). Builds a Windows executable with PyInstaller and attaches it to a GitHub Release.

### Creating a Release

Tag and push to trigger a release build:

```bash
git tag v1.0.0
git push origin v1.0.0
```

This will automatically create a GitHub Release with a downloadable `PDFReaderHelper-windows.zip`.

## Technical Details

**PDF Rendering**
- PyMuPDF renders pages to pixmaps with configurable zoom matrix
- Image extraction captures selected regions as high-resolution PNG
- Mouse events map screen coordinates to PDF coordinates for text/image selection
- Pages rendered on-demand to minimize memory usage

**Gemini Integration**
- Uses Files API instead of inline bytes: upload once, reference multiple times
- File references valid for 48 hours (Gemini limitation), cached locally for 47 hours
- Streaming API (`generate_content_stream`) provides incremental responses
- System instruction sets behavior: simplify language, use analogies, provide context
- Multimodal requests: PDF reference + conversation history + optional image + text prompt

**File Caching Strategy**
- MD5 hash of PDF bytes serves as unique identifier
- Cache stores: file hash -> {file_name, upload_time, original_path}
- Cache persisted to `.file_cache.json` in application directory
- Expired entries (>47h) automatically removed on lookup

**User Configuration**
- Per-user settings in `.config.json`: preferred model, default zoom, chat font size
- Per-PDF data in `.notes.json` and `.chat_history.json` keyed by file hash
- All settings auto-saved on change

**Markdown Rendering**
- Custom `markdown_to_html()` function converts markdown to styled HTML
- Supported: bold, italic, code blocks, inline code, headers, lists, tables
- LaTeX math rendered via KaTeX (inline `$...$` and display `$$...$$`)
- Real-time rendering: accumulate chunks, convert on each update

## Dependencies

```
PyQt6
PyQt6-WebEngine
PyMuPDF
google-genai
python-dotenv
```

Dev dependencies: `ruff`, `pytest`, `pyinstaller`
