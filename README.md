# PDF Reader with AI Assistant

Desktop application for reading PDFs with integrated Gemini AI explanations. Built with PyQt6.

This was inspired by Andrej Karpathy's https://github.com/karpathy/reader3.git with a different way to do things. This is a fully local desktop application with a tiny chat window on the side (currently only has support for Gemini with document understanding and file upload) with shortcuts to send pdf content to chat and preset prompts. This was created more in mind to read scientific papers for research and not books as such (Karpathy's version might be better for books). License is MIT, GPL, all of that. I won't sue. I would be happy to collaborate on its development however, so feel free to open issues/PRs.

## Features

**PDF Viewing**
- Standard navigation and zoom controls
- Text selection
- Page-by-page browsing

**AI Integration**
- Select text to get explanations
- Chat interface with document context
- Streaming responses with markdown formatting
- Quick actions: simplify explanations, request examples, ask why concepts matter
- Document analysis: summarize content, identify complex terms, suggest reading strategy

**Caching**
- Files uploaded to Gemini are cached by hash
- Re-opening the same PDF reuses the uploaded file reference
- Cache persists across sessions

## Setup

1. Get API key from [Google AI Studio](https://aistudio.google.com/apikey)

2. Create `.env` file:
   ```bash
   GEMINI_API_KEY=your_api_key_here
   ```

3. Run:
   ```bash
   python main.py
   ```

## Usage

- Open PDF from toolbar
- Select text for inline explanations
- Use chat panel for questions
- "Analyze Document" provides document overview
- "Find Complex Terms" scans current page

## Technical Details

### Architecture

**Component Structure**
- `PDFReaderHelper` (QMainWindow): Main application window, coordinates all components
- `PDFPageWidget` (QLabel): Handles PDF rendering and text selection with coordinate mapping
- `ChatPanel` (QWidget): Manages chat UI, markdown rendering, and message accumulation
- `GeminiWorker` (QThread): Asynchronous API calls to prevent UI blocking
- `SelectionPopup` (QFrame): Floating button that appears on text selection

**Data Flow**
```
User opens PDF → Hash computed → Check cache → Upload if new → Store file reference
User selects text → Coordinates mapped to PDF space → Text extracted → Popup shown
User asks question → Added to history → Sent with file reference → Stream chunks → Render markdown
```

### Implementation Details

**PDF Handling**
- PyMuPDF (fitz) renders pages to QPixmap at configurable zoom levels
- Text extraction uses PDF coordinate system for accurate selection boundaries
- Mouse events map screen coordinates to PDF coordinates for text selection
- Pages rendered on-demand to minimize memory usage

**Gemini Integration**
- Uses Files API instead of inline bytes: upload once, reference multiple times
- File references valid for 48 hours (Gemini limitation)
- Streaming API (`generate_content_stream`) provides incremental responses
- System instruction sets behavior: simplify language, use analogies, provide context

**File Caching Strategy**
- SHA-256 hash of PDF bytes serves as unique identifier
- Cache stores: file hash → {uri, name, upload_time}
- Cache persisted to `.pdf_cache.json` in application directory
- Expired entries (>48h) automatically removed on lookup
- Decision: Hash-based caching preferred over path-based to handle renamed/moved files

**Conversation Management**
- History stored as list of {role, content} dictionaries
- Each request includes: file reference + conversation history + current question
- History cleared when new document opened
- Design choice: Include full history in each request rather than using Chat API for more reliable context handling

**Markdown Rendering**
- Custom `markdown_to_html()` function converts markdown to styled HTML
- Real-time rendering: accumulate chunks, convert on each update, replace HTML
- Supported: bold, italic, code blocks, inline code, headers, lists
- HTML entities escaped to prevent injection attacks
- Trade-off: Re-rendering entire message on each chunk vs. partial updates (chose simplicity)

**Threading Model**
- `GeminiWorker` runs in separate thread to avoid freezing UI during API calls
- Signals for chunk updates, completion, and errors
- Cancellable: user can interrupt long-running requests
- Worker instances replaced (not reused) to prevent state contamination

### Design Decisions

**Why Files API over inline bytes?**
- Reduces bandwidth: ~10MB PDF sent once vs. on every message
- Faster responses: no upload latency per request
- Lower token usage: file reference is minimal vs. full document encoding
- Gemini recommendation for documents >20 pages

**Why manual history management over Chat API?**
- Chat API multipart content handling is inconsistent
- Direct API calls provide more control over context structure
- Easier to debug and modify conversation flow
- Can include file reference reliably with each request

**Why re-render markdown on each chunk?**
- Ensures consistent formatting throughout streaming
- Simpler than tracking partial markdown state
- Performance impact negligible for typical response sizes
- Alternative (append-only) breaks markdown that spans chunks (e.g., lists)

**Why QThread over async/await?**
- PyQt6's event loop integrates cleanly with QThread
- Signals/slots provide type-safe cross-thread communication
- More explicit threading model for Qt applications
- Async would require event loop coordination with Qt

### Performance Characteristics

**PDF Loading**
- Initial load: O(1) for PyMuPDF open, O(n) for first page render
- Page switching: Single page render (~50-100ms for typical page)
- Text selection: O(blocks) where blocks = text regions on page

**File Upload**
- First open: Network upload time (depends on file size and connection)
- Cached open: <10ms (hash lookup + file metadata load)
- Hash computation: ~50-200ms for 10MB PDF

**API Requests**
- Latency: 200-500ms first token with file reference
- Streaming: 20-50 tokens/second typical
- Context size: History text + file reference ~constant per request

**Memory Usage**
- Base: ~50MB (Qt + libraries)
- Per page rendered: ~5-10MB (depends on resolution and zoom)
- Conversation history: ~1KB per message pair
- File cache: <1KB per cached file

## Dependencies

```
PyQt6
PyMuPDF
google-genai
python-dotenv
```
