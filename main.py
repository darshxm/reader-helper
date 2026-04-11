"""
PDF Reader Helper with Gemini AI Integration
A desktop app for reading complex PDFs with AI-powered explanations.

Main application window and entry point.
"""

import sys
import os
import io
from pathlib import Path
from datetime import datetime, timedelta

import fitz  # PyMuPDF
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QScrollArea, QLabel, QPushButton, QFileDialog, 
    QToolBar, QSpinBox, QMessageBox, QComboBox, QTabWidget
)
from PyQt6.QtCore import Qt, QTimer, QPoint
from PyQt6.QtGui import QAction
from google import genai

from utils import (
    load_config, save_config, load_notes, save_notes,
    load_chat_history, save_chat_history, load_file_cache, 
    save_file_cache, get_file_hash, MODEL, AVAILABLE_MODELS, 
    CACHE_EXPIRY_HOURS
)
from gemini_worker import GeminiWorker
from widgets import PDFPageWidget, SelectionPopup
from panels import NotesPanel, ChatPanel


class PDFReaderHelper(QMainWindow):
    """Main application window."""

    MIN_ZOOM_PERCENT = 50
    MAX_ZOOM_PERCENT = 800

    def __init__(self):
        super().__init__()
        self.setWindowTitle("PDF Reader Helper")
        self.setGeometry(100, 100, 1400, 900)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1a1a1a;
            }
            QToolBar {
                background-color: #2d2d2d;
                border: none;
                spacing: 8px;
                padding: 4px;
            }
            QToolBar QLabel {
                color: #e0e0e0;
            }
            QSpinBox {
                background-color: #3d3d3d;
                color: #e0e0e0;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 4px;
            }
        """)
        
        # Initialize Gemini client
        self.gemini_client = None
        self.gemini_chat = None
        self.current_worker = None
        self.pdf_bytes = None
        self.init_gemini()
        
        # PDF document
        self.doc = None
        self.current_page = 0
        self.current_pdf_hash = None  # Track current PDF for notes
        
        # Load user configuration and notes
        self.config = load_config()
        self.selected_model = self.config.get("preferred_model", MODEL)
        saved_zoom = self.config.get("default_zoom", 1.5)
        self.zoom = max(
            self.MIN_ZOOM_PERCENT / 100.0,
            min(saved_zoom, self.MAX_ZOOM_PERCENT / 100.0),
        )
        self.chat_font_size = self.config.get("chat_font_size", 14)  # Load chat font size from config
        self.all_notes = load_notes()  # All PDF notes
        self.all_chat_history = load_chat_history()  # All PDF chat histories
        
        # Setup UI
        self.setup_ui()
        self.setup_toolbar()
        
        # Selection popup
        self.selection_popup = SelectionPopup()
        self.selection_popup.explain_clicked.connect(self.explain_selection)
    
    def init_gemini(self):
        """Initialize Gemini client."""
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            # Try loading from .env file
            env_path = Path(__file__).parent / ".env"
            if env_path.exists():
                with open(env_path) as f:
                    for line in f:
                        if line.startswith("GEMINI_API_KEY="):
                            api_key = line.split("=", 1)[1].strip().strip('"\'')
                            os.environ["GEMINI_API_KEY"] = api_key
                            break
        
        if api_key:
            try:
                self.gemini_client = genai.Client(api_key=api_key)
                print("Gemini client initialized successfully")
            except Exception as e:
                print(f"Failed to initialize Gemini: {e}")
        else:
            print("Warning: GEMINI_API_KEY not found. AI features will be disabled.")
    
    def setup_ui(self):
        """Setup the main UI layout."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QHBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Splitter for PDF viewer and chat panel
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # PDF Viewer (left side)
        pdf_container = QWidget()
        pdf_layout = QVBoxLayout(pdf_container)
        pdf_layout.setContentsMargins(0, 0, 0, 0)
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: #333;
                border: none;
            }
        """)
        
        self.page_widget = PDFPageWidget()
        self.page_widget.text_selected.connect(self.on_text_selected)
        self.page_widget.selection_made.connect(self.on_selection_made)
        self.scroll_area.setWidget(self.page_widget)
        
        pdf_layout.addWidget(self.scroll_area)
        
        # Page navigation
        nav_layout = QHBoxLayout()
        nav_layout.setContentsMargins(8, 4, 8, 4)
        
        self.prev_btn = QPushButton("◀ Previous")
        self.prev_btn.clicked.connect(self.prev_page)
        self.prev_btn.setStyleSheet("""
            QPushButton {
                background-color: #3d3d3d;
                color: #e0e0e0;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover { background-color: #4d4d4d; }
        """)
        nav_layout.addWidget(self.prev_btn)
        
        self.page_label = QLabel("Page 0 / 0")
        self.page_label.setStyleSheet("color: #e0e0e0;")
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nav_layout.addWidget(self.page_label)
        
        self.next_btn = QPushButton("Next ▶")
        self.next_btn.clicked.connect(self.next_page)
        self.next_btn.setStyleSheet("""
            QPushButton {
                background-color: #3d3d3d;
                color: #e0e0e0;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover { background-color: #4d4d4d; }
        """)
        nav_layout.addWidget(self.next_btn)
        
        pdf_layout.addLayout(nav_layout)
        
        # Right side: Tabbed interface for Chat and Notes
        right_panel = QTabWidget()
        right_panel.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #333;
                background-color: #252525;
            }
            QTabBar::tab {
                background-color: #2d2d2d;
                color: #e0e0e0;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #252525;
                color: #4a9eff;
            }
            QTabBar::tab:hover {
                background-color: #3d3d3d;
            }
        """)
        
        # Chat Panel
        self.chat_panel = ChatPanel()
        self.chat_panel.set_font_size(self.chat_font_size)  # Apply saved font size
        self.chat_panel.send_btn.clicked.connect(self.send_message)
        self.chat_panel.simplify_btn.clicked.connect(self.request_simpler)
        self.chat_panel.example_btn.clicked.connect(self.request_example)
        self.chat_panel.why_btn.clicked.connect(self.request_why_important)
        self.chat_panel.font_size_spin.valueChanged.connect(self.on_chat_font_size_changed)
        right_panel.addTab(self.chat_panel, "💬 Chat")
        
        # Notes Panel
        self.notes_panel = NotesPanel()
        self.notes_panel.notes_changed.connect(self.on_notes_changed)
        right_panel.addTab(self.notes_panel, "📝 Notes")
        
        # Add to splitter
        splitter.addWidget(pdf_container)
        splitter.addWidget(right_panel)
        splitter.setSizes([900, 500])
        splitter.setHandleWidth(6)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #444;
            }
            QSplitter::handle:hover {
                background-color: #4a9eff;
            }
        """)

        layout.addWidget(splitter)
    
    def setup_toolbar(self):
        """Setup the toolbar."""
        toolbar = QToolBar()
        self.addToolBar(toolbar)
        
        # Open file action
        open_action = QAction("📂 Open PDF", self)
        open_action.triggered.connect(self.open_pdf)
        toolbar.addAction(open_action)
        
        toolbar.addSeparator()
        
        # Zoom controls
        toolbar.addWidget(QLabel("Zoom:"))
        
        self.zoom_spin = QSpinBox()
        self.zoom_spin.setRange(self.MIN_ZOOM_PERCENT, self.MAX_ZOOM_PERCENT)
        self.zoom_spin.setValue(int(self.zoom * 100))  # Use saved default zoom
        self.zoom_spin.setSuffix("%")
        self.zoom_spin.valueChanged.connect(self.change_zoom)
        toolbar.addWidget(self.zoom_spin)
        
        # Set as default zoom button
        set_default_zoom_btn = QAction("⭐ Set Default Zoom", self)
        set_default_zoom_btn.triggered.connect(self.set_zoom_as_default)
        toolbar.addAction(set_default_zoom_btn)
        
        toolbar.addSeparator()
        
        # Analyze document button
        analyze_action = QAction("🔍 Analyze Document", self)
        analyze_action.triggered.connect(self.analyze_document)
        toolbar.addAction(analyze_action)
        
        # Detect complex terms button
        detect_action = QAction("📚 Find Complex Terms", self)
        detect_action.triggered.connect(self.detect_complex_terms)
        toolbar.addAction(detect_action)
        
        toolbar.addSeparator()
        
        # Model selector
        toolbar.addWidget(QLabel("AI Model:"))
        
        self.model_selector = QComboBox()
        self.model_selector.addItems(AVAILABLE_MODELS)
        self.model_selector.setCurrentText(self.selected_model)
        self.model_selector.setStyleSheet("""
            QComboBox {
                background-color: #3d3d3d;
                color: #e0e0e0;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 4px 8px;
                min-width: 180px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 6px solid #e0e0e0;
                margin-right: 6px;
            }
            QComboBox QAbstractItemView {
                background-color: #3d3d3d;
                color: #e0e0e0;
                selection-background-color: #4a9eff;
                border: 1px solid #555;
            }
        """)
        self.model_selector.currentTextChanged.connect(self.on_model_changed)
        self.model_selector.setToolTip("Select AI model for explanations")
        toolbar.addWidget(self.model_selector)
        
        # Set as default button
        set_default_btn = QAction("⭐ Set as Default", self)
        set_default_btn.triggered.connect(self.set_model_as_default)
        toolbar.addAction(set_default_btn)
    
    def open_pdf(self):
        """Open a PDF file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open PDF", "", "PDF Files (*.pdf)"
        )
        
        if file_path:
            try:
                self.doc = fitz.open(file_path)
                
                # Get file hash for cache, notes, chat, and last page
                file_hash = get_file_hash(file_path)
                self.current_pdf_hash = file_hash
                
                # Restore last page or start at beginning
                pdf_data = self.all_chat_history.get(file_hash, {})
                last_page = pdf_data.get("last_page", 0)
                self.current_page = min(last_page, len(self.doc) - 1)  # Ensure valid page
                
                self.render_page()
                self.update_page_label()
                
                # Load notes for this PDF
                pdf_notes = self.all_notes.get(file_hash, "")
                self.notes_panel.set_notes(pdf_notes)
                
                # Restore chat history for this PDF
                saved_history = pdf_data.get("conversation", [])
                self.conversation_history = saved_history.copy()
                
                # Check cache for existing upload
                cache = load_file_cache()
                cached_entry = cache.get(file_hash)
                
                self.uploaded_file = None
                
                # Check if we have a valid cached upload
                if cached_entry:
                    cached_time = datetime.fromisoformat(cached_entry["upload_time"])
                    if datetime.now() - cached_time < timedelta(hours=CACHE_EXPIRY_HOURS):
                        # Try to get the cached file from Gemini
                        try:
                            self.chat_panel.set_status("Using cached upload...")
                            self.uploaded_file = self.gemini_client.files.get(
                                name=cached_entry["file_name"]
                            )
                            print(f"Using cached file: {self.uploaded_file.name}")
                        except Exception as e:
                            print(f"Cached file expired or invalid: {e}")
                            self.uploaded_file = None
                            # Remove invalid cache entry
                            del cache[file_hash]
                            save_file_cache(cache)
                
                # Upload if not cached or cache invalid
                if not self.uploaded_file:
                    self.chat_panel.set_status("Uploading document to Gemini...")
                    try:
                        pdf_bytes = Path(file_path).read_bytes()
                        pdf_io = io.BytesIO(pdf_bytes)
                        self.uploaded_file = self.gemini_client.files.upload(
                            file=pdf_io,
                            config={"mime_type": "application/pdf"}
                        )
                        print(f"Uploaded file: {self.uploaded_file.name}")
                        
                        # Save to cache
                        cache[file_hash] = {
                            "file_name": self.uploaded_file.name,
                            "upload_time": datetime.now().isoformat(),
                            "original_path": file_path
                        }
                        save_file_cache(cache)
                    except Exception as e:
                        print(f"Warning: Failed to upload to Files API: {e}")
                        self.uploaded_file = None
                
                # Initialize chat with document context (only reset if no saved history)
                if not saved_history:
                    self.conversation_history = []  # Reset history for new document
                self.init_chat_with_document()
                self.chat_panel.clear()
                self.chat_panel.add_ai_message_start()
                
                cache_status = "(cached)" if cached_entry and self.uploaded_file else "(uploaded)"
                welcome_msg = (
                    f"📄 Loaded: {Path(file_path).name} {cache_status}\n\n"
                    "I'm ready to help you understand this document. You can:\n"
                    "• Select any text and click 'Explain This'\n"
                    "• Ask me questions in the chat\n"
                    "• Use 'Analyze Document' for an overview\n"
                    "• Use 'Find Complex Terms' to identify difficult concepts"
                )
                
                # If we have saved chat history, restore it, otherwise show welcome
                if saved_history:
                    self.chat_panel.restore_chat_history(saved_history)
                    self.chat_panel.add_ai_message_start()
                    self.chat_panel.add_ai_chunk(f"\n\n📄 Reopened: {Path(file_path).name} {cache_status}\nYour previous conversation has been restored.")
                    self.chat_panel.add_ai_message_end()
                else:
                    self.chat_panel.add_ai_chunk(welcome_msg)
                    self.chat_panel.add_ai_message_end()
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to open PDF: {e}")
    
    def render_page(self):
        """Render the current page."""
        if self.doc and 0 <= self.current_page < len(self.doc):
            page = self.doc[self.current_page]
            self.page_widget.set_page(page, self.zoom)
    
    def update_page_label(self):
        """Update the page number label."""
        if self.doc:
            self.page_label.setText(f"Page {self.current_page + 1} / {len(self.doc)}")
        else:
            self.page_label.setText("Page 0 / 0")
    
    def prev_page(self):
        """Go to previous page."""
        if self.doc and self.current_page > 0:
            self.current_page -= 1
            self.render_page()
            self.update_page_label()
            self.save_current_page()
    
    def next_page(self):
        """Go to next page."""
        if self.doc and self.current_page < len(self.doc) - 1:
            self.current_page += 1
            self.render_page()
            self.update_page_label()
            self.save_current_page()
    
    def save_current_page(self):
        """Save the current page number for this PDF."""
        if self.current_pdf_hash:
            if self.current_pdf_hash not in self.all_chat_history:
                self.all_chat_history[self.current_pdf_hash] = {}
            self.all_chat_history[self.current_pdf_hash]["last_page"] = self.current_page
            save_chat_history(self.all_chat_history)
    
    def change_zoom(self, value):
        """Change zoom level."""
        self.zoom = value / 100.0
        self.render_page()
    
    def on_model_changed(self, model: str):
        """Handle model selection change."""
        self.selected_model = model
        self.chat_panel.set_status(f"Switched to {model}")
        QTimer.singleShot(2000, lambda: self.chat_panel.set_status(""))  # Clear after 2s
    
    def set_model_as_default(self):
        """Save current model as user's default."""
        self.config["preferred_model"] = self.selected_model
        save_config(self.config)
        QMessageBox.information(
            self,
            "Default Set",
            f"✓ {self.selected_model} is now your default model."
        )
    
    def set_zoom_as_default(self):
        """Save current zoom as user's default."""
        self.config["default_zoom"] = self.zoom
        save_config(self.config)
        QMessageBox.information(
            self,
            "Default Set",
            f"✓ Zoom level {int(self.zoom * 100)}% is now your default."
        )
    
    def on_chat_font_size_changed(self, size: int):
        """Handle chat font size change and save to config."""
        self.chat_font_size = size
        self.config["chat_font_size"] = size
        save_config(self.config)
    
    def on_notes_changed(self, notes_text: str):
        """Handle notes changes and save to disk."""
        if self.current_pdf_hash:
            self.all_notes[self.current_pdf_hash] = notes_text
            save_notes(self.all_notes)
    
    def on_text_selected(self, text: str, pos: QPoint):
        """Handle text selection (backward compatibility)."""
        if text:
            self.selection_popup.show_at(text, None, pos)
    
    def on_selection_made(self, text: str, image_bytes: object, pos: QPoint):
        """Handle selection with text and/or image."""
        if text or image_bytes:
            self.selection_popup.show_at(text, image_bytes, pos)
    
    def explain_selection(self, text: str, image_bytes: object):
        """Prepare selection explanation - put in chat input for user to review."""
        # Build a default prompt based on what was selected
        if text and image_bytes:
            prompt = f"Please explain this text and image:\n\n{text}"
        elif image_bytes:
            prompt = "What is shown in this image? Please explain any diagrams, charts, or visual elements."
        else:
            prompt = f"Please explain this text in simple terms:\n\n{text}"
        
        # Put the selection in the chat input for user to review/edit
        if image_bytes:
            self.chat_panel.set_image_attachment(image_bytes, prompt)
        else:
            self.chat_panel.input_field.setPlainText(prompt)
            self.chat_panel.input_field.setFocus()
    
    def send_message(self):
        """Send user's message to Gemini."""
        text = self.chat_panel.input_field.toPlainText().strip()
        image_bytes = self.chat_panel.get_image_attachment()
        
        if text or image_bytes:
            self.chat_panel.input_field.clear()
            self.chat_panel.clear_image()
            self.send_to_gemini(text, display_text=text, image_bytes=image_bytes)
    
    def request_simpler(self):
        """Request a simpler explanation of the last response."""
        prompt = "Please explain that in even simpler terms. Pretend I'm a complete beginner with no background in this topic. Use everyday language and simple analogies."
        self.send_to_gemini(prompt, display_text="Make it simpler")
    
    def request_example(self):
        """Request a concrete example."""
        prompt = "Can you give me a concrete, real-world example of this concept? Something I might encounter in everyday life."
        self.send_to_gemini(prompt, display_text="Give me an example")
    
    def request_why_important(self):
        """Ask why this concept is important."""
        prompt = "Why is this concept important? What problems does it solve or what would happen without it?"
        self.send_to_gemini(prompt, display_text="Why is this important?")
    
    def analyze_document(self):
        """Analyze the entire document."""
        if not getattr(self, 'uploaded_file', None):
            QMessageBox.warning(self, "No Document", "Please open a PDF first.")
            return
        
        prompt = """Please analyze this document and provide:
1. A brief summary (2-3 sentences)
2. The main topics covered
3. Key terms that might need explanation
4. The assumed background knowledge needed to understand it
5. Suggested reading order or focus areas

Be concise but helpful."""
        
        self.send_to_gemini(prompt, display_text="Analyze this document", include_pdf=True)
    
    def detect_complex_terms(self):
        """Detect complex terms in the current page."""
        if not self.doc:
            QMessageBox.warning(self, "No Document", "Please open a PDF first.")
            return
        
        page = self.doc[self.current_page]
        page_text = page.get_text()
        
        prompt = f"""Analyze this page text and identify complex or technical terms that a general reader might not understand. For each term, provide a brief definition.

Page text:
{page_text}

Format as:
**Term**: Brief definition

List the most important 5-10 terms."""
        
        self.send_to_gemini(prompt, display_text=f"Find complex terms on page {self.current_page + 1}")
    
    def init_chat_with_document(self):
        """Initialize chat session with document context."""
        if not self.gemini_client or not self.uploaded_file:
            return
        
        self.system_instruction = """You are a helpful reading assistant. Your job is to help users understand complex documents, papers, and books. 

Key behaviors:
- Explain concepts in simple, accessible language
- Define technical terms when they appear
- Use analogies and real-world examples
- Be concise but thorough
- If asked to simplify, really dumb it down - assume zero background knowledge
- Reference specific parts of the document when relevant
- You have access to the full document - use it to provide context-aware answers"""
        
        self.document_initialized = True
    
    def send_to_gemini(self, prompt: str, display_text: str = None, include_pdf: bool = False, image_bytes: bytes = None):
        """Send a message to Gemini with streaming response."""
        if not self.gemini_client:
            QMessageBox.warning(
                self, "API Key Missing",
                "Please set GEMINI_API_KEY environment variable or add it to .env file."
            )
            return
        
        # Cancel any ongoing request
        if self.current_worker and self.current_worker.isRunning():
            self.current_worker.cancel()
            self.current_worker.wait()
        
        # Display user message (with image indicator if present)
        display_msg = display_text or prompt
        if image_bytes:
            display_msg = "🖼️ " + display_msg
        self.chat_panel.add_user_message(display_msg)
        self.chat_panel.add_ai_message_start()
        self.chat_panel.set_status("Thinking...")
        self.chat_panel.set_buttons_enabled(False)
        
        # Build conversation history for context
        if not hasattr(self, 'conversation_history'):
            self.conversation_history = []
        
        # Add current prompt to history
        self.conversation_history.append({"role": "user", "content": prompt})
        
        # Send request with uploaded file reference (efficient - no re-upload!)
        self.current_worker = GeminiWorker(
            self.gemini_client,
            prompt,
            self.selected_model,  # Use selected model
            getattr(self, 'uploaded_file', None),  # Use uploaded file reference
            self.conversation_history,
            getattr(self, 'system_instruction', ''),
            image_bytes
        )
        self.current_worker.chunk_received.connect(self.on_chunk_received)
        self.current_worker.finished_response.connect(self.on_response_finished)
        self.current_worker.error_occurred.connect(self.on_error)
        self.current_worker.start()
    
    def on_chunk_received(self, text: str):
        """Handle streaming chunk."""
        self.chat_panel.add_ai_chunk(text)
    
    def on_response_finished(self, full_response: str):
        """Handle completed response."""
        self.chat_panel.add_ai_message_end()
        self.chat_panel.set_status("")
        self.chat_panel.set_buttons_enabled(True)
        
        # Save response to conversation history
        if hasattr(self, 'conversation_history'):
            self.conversation_history.append({"role": "assistant", "content": full_response})
            
            # Save conversation history to disk
            if self.current_pdf_hash:
                if self.current_pdf_hash not in self.all_chat_history:
                    self.all_chat_history[self.current_pdf_hash] = {}
                self.all_chat_history[self.current_pdf_hash]["conversation"] = self.conversation_history
                save_chat_history(self.all_chat_history)
    
    def on_error(self, error: str):
        """Handle API error."""
        self.chat_panel.add_ai_chunk(f"\n\n❌ Error: {error}")
        self.chat_panel.add_ai_message_end()
        self.chat_panel.set_status("")
        self.chat_panel.set_buttons_enabled(True)
    
    def closeEvent(self, event):
        """Clean up on close."""
        if self.current_worker and self.current_worker.isRunning():
            self.current_worker.cancel()
            self.current_worker.wait()
        
        # Save any unsaved notes and chat history
        if self.current_pdf_hash:
            # Save notes
            notes_text = self.notes_panel.get_notes()
            self.all_notes[self.current_pdf_hash] = notes_text
            save_notes(self.all_notes)
            
            # Save current page and conversation
            if self.current_pdf_hash not in self.all_chat_history:
                self.all_chat_history[self.current_pdf_hash] = {}
            self.all_chat_history[self.current_pdf_hash]["last_page"] = self.current_page
            self.all_chat_history[self.current_pdf_hash]["conversation"] = getattr(self, 'conversation_history', [])
            save_chat_history(self.all_chat_history)
        
        if self.doc:
            self.doc.close()
        event.accept()


def main():
    app = QApplication(sys.argv)
    
    # Set dark theme
    app.setStyle("Fusion")
    
    window = PDFReaderHelper()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
