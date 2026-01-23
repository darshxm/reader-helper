# PDF Reader with AI Assistant

Desktop application for reading PDFs with integrated Gemini AI explanations. Built with PyQt6.

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
- Streaming responses with markdown and table formatting
- Quick actions: simplify explanations, request examples, ask why concepts matter
- Document analysis: summarize content, identify complex terms, suggest reading strategy
- Selected content appears in chat input for review before sending

**Notes & History**
- Per-PDF note taking with automatic saving
- Conversation history persisted per document
- Last page position remembered for each PDF

**Caching**
- Files uploaded to Gemini are cached by hash
- Re-opening the same PDF reuses the uploaded file reference
- Cache persists across sessions

## Module Structure

The application is organized into focused modules for better maintainability:

**`main.py`** - Main application (~570 lines)
- PDFReaderHelper window class
- PDF loading, page navigation, and user interactions
- Coordinates all components

**`utils.py`** - Utility functions
- File operations (cache, config, notes, chat history)
- Configuration management (load/save)
- Markdown to HTML conversion with table support
- File hashing for cache identification

**`gemini_worker.py`** - AI integration
- Background thread for API calls
- Streaming response handling
- Conversation history and context management
- Image attachment support

**`widgets.py`** - Custom Qt widgets
- PDFPageWidget: Displays PDF pages with text/image selection
- SelectionPopup: Context menu for selections
- PDF rendering and mouse interaction handling

**`panels.py`** - UI panels
- NotesPanel: Note-taking interface
- ChatPanel: AI chat with font controls and image preview
- Quick action buttons and chat history management

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

- **Open PDF**: Click "📂 Open PDF" from toolbar
- **Text Selection**: Click and drag to select text, then click "🤖 Explain This"
- **Image Selection**: Select a region with diagrams/charts, then click "🖼️ Explain This Image"
- **Chat**: Ask questions in the chat panel - the AI has access to the full document
- **Quick Actions**: Use "🎯 Make Simpler", "📝 Give Example", "❓ Why Important" buttons
- **Analyze**: Click "🔍 Analyze Document" for document overview
- **Complex Terms**: Click "📚 Find Complex Terms" to scan current page
- **Font Size**: Adjust chat text size using the font spinner in chat header
- **Zoom**: Set  & Module Dependencies

```
main.py
├── utils.py (configuration, file operations, markdown)
├── gemini_worker.py (AI worker thread)
├── widgets.py (PDF display, selection popup)
└── panels.py (notes and chat UI)
    └── utils.py (markdown conversion)

gemini_worker.py
└── utils.py (MODEL constant)
```

**Benefits of Modular Structure**
- Each module has a clear, single responsibility
- Smaller files are easier to navigate and understand
- Components can be imported and reused
- Isolated modules are easier to test
- Team members can work on different modules simultaneously

##Image extraction: captures selected region as high-resolution pixmap, converts to PNG bytes
- Mouse events map screen coordinates to PDF coordinates for text/image selection
- Pages rendered on-demand to minimize memory usage

**Gemini Integration**
- Uses Files API instead of inline bytes: upload once, reference multiple times
- File references valid for 48 hours (Gemini limitation)
- Streaming API (`generate_content_stream`) provides incremental responses
- System instruction sets behavior: simplify language, use analogies, provide context
- Image support: selected images sent as inline base64 PNG data with MIME type
- Multimodal requests: PDF reference + conversation history + optional image + text prompt

**File Caching Strategy**
- MD5 hash of PDF bytes serves as unique identifier
- Cache stores: file hash → {file_name, upload_time, original_path}
- Cache persisted to `.file_cache.json` in application directory
- Expired entries (>47h) automatically removed on lookup
- Decision: Hash-based caching preferred over path-based to handle renamed/moved files

**User Configuration**
- Per-user settings in `.config.json`: preferred model, default zoom, chat font size
- Per-PDF data in `.notes.json` and `.chat_history.json` keyed by file hash
- Last page position remembered per PDF
- All settings auto-saved on change

**Conversation Management**
- History stored as list of {role, content} dictionaries per PDF
- Each request includes: file reference + conversation history + current question + optional image
- History restored when reopening same PDF
- Design choice: Include full history in each request for reliable context handling

**Markdown Rendering**
- Custom `markdown_to_html()` function converts markdown to styled HTML
- Real-time rendering: accumulate chunks, convert on each update, replace HTML
- Supported: bold, italic, code blocks, inline code, headers, lists, **tables**
- Table parsing: detects pipe-delimited tables, renders with styled headers and rown boundaries
- Mouse events map screen coordinates to PDF coordinates for text selection
- Pages rendered on-demand to minimize memory usage

**Gemini Integration**
- Uses Files API instead of inline bytes: upload once, reference multiple times
- File references valid for 48 hours (Gemini limitation)
- Streaming API (`generate_content_stream`) provides incremental responses
- Systinline images for selections?**
- Selected regions are typically small (diagrams, charts)
- Immediate availability without upload delay
- No need to track uploaded image references
- PNG format provides lossless quality for text/diagrams

**Why put selections in chat input vs. sending directly?**
- User can review and edit the prompt before sending
- Allows adding context or specific questions about the selection
- User can remove unwanted image attachments
- More control over what gets sent to the AI

**Why manual history management over Chat API?**
- Chat API multipart content handling is inconsistent
- Direct API calls provide more control over context structure
- Easier to debug and modify conversation flow
- Can include file reference reliably with each request

**Why re-render markdown on each chunk?**
- Ensures consistent formatting throughout streaming
- Simpler than tracking partial markdown state
- Performance impact negligible for typical response sizes
- Alternative (append-only) breaks markdown that spans chunks (e.g., lists, table
- Each request includes: file reference + conversation history + current question
- History cleared when new document opened
- Design choice: Include full history in each request rather than using Chat API for more reliable context handling

**Markdown Rendering**
- Custom `markdown_to_html()` function converts markdown to styled HTML
- Image extraction: ~20-50ms for typical selection region

**File Upload**
- First open: Network upload time (depends on file size and connection)
- Cached open: <10ms (hash lookup + file metadata load)
- Hash computation: ~50-200ms for 10MB PDF (MD5)

**API Requests**
- Latency: 200-500ms first token with file reference
- Streaming: 20-50 tokens/second typical
- Context size: History text + file reference + optional image ~constant per request
- Image attachment: adds ~50-200KB depending on selection size

**Memory Usage**
- Base: ~50MB (Qt + libraries)
- Per page rendered: ~5-10MB (depends on resolution and zoom)
- Conversation history: ~1KB per message pair
- File cache: <1KB per cached file
- Image attachments: temporary, cleared after sending (~50-500KB during composition)ncy per request
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
