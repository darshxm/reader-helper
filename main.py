"""
PDF Reader Helper with Gemini AI Integration
A desktop app for reading complex PDFs with AI-powered explanations.
"""

import sys
import os
import re
import io
import json
import hashlib
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta
import fitz  # PyMuPDF
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QScrollArea, QLabel, QPushButton, QTextEdit,
    QFileDialog, QToolBar, QSpinBox, QMessageBox, QFrame,
    QToolTip, QMenu
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QPoint, QTimer, QRect
from PyQt6.QtGui import (
    QPixmap, QImage, QAction, QCursor, QFont, QTextCursor,
    QPainter, QColor, QPen
)
from google import genai
from google.genai import types

MODEL = "gemini-3-flash-preview"
CACHE_FILE = Path(__file__).parent / ".file_cache.json"
CACHE_EXPIRY_HOURS = 47  # Files API keeps files for 48 hours, we use 47 to be safe


def get_file_hash(file_path: str) -> str:
    """Get MD5 hash of a file to identify it uniquely."""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def load_file_cache() -> dict:
    """Load the file upload cache from disk."""
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_file_cache(cache: dict):
    """Save the file upload cache to disk."""
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(cache, f, indent=2)
    except Exception as e:
        print(f"Warning: Failed to save file cache: {e}")

def markdown_to_html(text: str) -> str:
    """Convert simple markdown to HTML."""
    # Escape HTML
    text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    
    # Bold
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    
    # Italic
    text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
    
    # Code blocks
    text = re.sub(r'```([\s\S]+?)```', r'<pre style="background-color: #2a2a2a; padding: 8px; border-radius: 4px; overflow-x: auto;">\1</pre>', text)
    
    # Inline code
    text = re.sub(r'`(.+?)`', r'<code style="background-color: #2a2a2a; padding: 2px 4px; border-radius: 3px;">\1</code>', text)
    
    # Headers
    text = re.sub(r'^### (.+)$', r'<h3 style="color: #4a9eff; margin-top: 12px;">\1</h3>', text, flags=re.MULTILINE)
    text = re.sub(r'^## (.+)$', r'<h2 style="color: #4a9eff; margin-top: 12px;">\1</h2>', text, flags=re.MULTILINE)
    text = re.sub(r'^# (.+)$', r'<h1 style="color: #4a9eff; margin-top: 12px;">\1</h1>', text, flags=re.MULTILINE)
    
    # Bullet lists
    lines = text.split('\n')
    in_list = False
    result = []
    for line in lines:
        if line.strip().startswith(('- ', '* ', '• ')):
            if not in_list:
                result.append('<ul style="margin: 8px 0;">')
                in_list = True
            item = line.strip()[2:].strip()
            result.append(f'<li>{item}</li>')
        else:
            if in_list:
                result.append('</ul>')
                in_list = False
            result.append(line)
    if in_list:
        result.append('</ul>')
    text = '\n'.join(result)
    
    # Numbered lists
    text = re.sub(r'^(\d+)\. (.+)$', r'<div style="margin-left: 20px;"><b>\1.</b> \2</div>', text, flags=re.MULTILINE)
    
    # Line breaks
    text = text.replace('\n\n', '<br><br>')
    text = text.replace('\n', '<br>')
    
    return text


class GeminiWorker(QThread):
    """Background worker for Gemini API calls with streaming."""
    chunk_received = pyqtSignal(str)
    finished_response = pyqtSignal(str)  # Emit full response for history
    error_occurred = pyqtSignal(str)
    
    def __init__(self, client, message: str, uploaded_file=None,
                 conversation_history: list = None, system_instruction: str = ""):
        super().__init__()
        self.client = client
        self.message = message
        self.uploaded_file = uploaded_file  # File reference from Files API
        self.conversation_history = conversation_history or []
        self.system_instruction = system_instruction
        self._is_cancelled = False
    
    def cancel(self):
        self._is_cancelled = True
    
    def run(self):
        try:
            # Build contents with uploaded file reference and conversation history
            contents = []
            
            # Add uploaded file reference (not raw bytes - much more efficient!)
            if self.uploaded_file:
                contents.append(self.uploaded_file)
            
            # Add conversation history for context (excluding current message)
            history_text = ""
            for msg in self.conversation_history[:-1]:  # Exclude current message
                role = "User" if msg["role"] == "user" else "Assistant"
                history_text += f"{role}: {msg['content']}\n\n"
            
            if history_text:
                contents.append(f"Previous conversation:\n{history_text}")
            
            # Add current message
            contents.append(f"Current question: {self.message}")
            
            # Make the API call with streaming
            response = self.client.models.generate_content_stream(
                model=MODEL,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction
                ) if self.system_instruction else None
            )
            
            full_response = ""
            for chunk in response:
                if self._is_cancelled:
                    break
                if chunk.text:
                    full_response += chunk.text
                    self.chunk_received.emit(chunk.text)
            
            self.finished_response.emit(full_response)
        except Exception as e:
            self.error_occurred.emit(str(e))


class PDFPageWidget(QLabel):
    """Widget to display a single PDF page with text selection support."""
    text_selected = pyqtSignal(str, QPoint)  # Selected text and position
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMouseTracking(True)
        self.page = None
        self.zoom = 1.5
        self.selection_start = None
        self.selection_end = None
        self.selected_text = ""
        self.text_blocks = []  # Store text positions for hover detection
        self.complex_terms = []  # Terms detected as complex
        
    def set_page(self, page: fitz.Page, zoom: float = 1.5):
        """Render and display a PDF page."""
        self.page = page
        self.zoom = zoom
        self.selection_start = None
        self.selection_end = None
        self.selected_text = ""
        
        # Render page to pixmap
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        
        # Convert to QImage
        img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(img)
        
        self.setPixmap(pixmap)
        self.setFixedSize(pixmap.size())
        
        # Extract text blocks for hover tooltips
        self.text_blocks = page.get_text("dict")["blocks"]
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.page:
            self.selection_start = event.pos()
            self.selection_end = None
    
    def mouseMoveEvent(self, event):
        if self.selection_start and event.buttons() == Qt.MouseButton.LeftButton:
            self.selection_end = event.pos()
            self.update()
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.page and self.selection_start:
            self.selection_end = event.pos()
            
            # Convert screen coordinates to PDF coordinates
            x0 = min(self.selection_start.x(), self.selection_end.x()) / self.zoom
            y0 = min(self.selection_start.y(), self.selection_end.y()) / self.zoom
            x1 = max(self.selection_start.x(), self.selection_end.x()) / self.zoom
            y1 = max(self.selection_start.y(), self.selection_end.y()) / self.zoom
            
            # Extract text from selection rectangle
            rect = fitz.Rect(x0, y0, x1, y1)
            self.selected_text = self.page.get_text("text", clip=rect).strip()
            
            if self.selected_text:
                # Emit signal with text and position for popup button
                self.text_selected.emit(self.selected_text, event.globalPosition().toPoint())
    
    def paintEvent(self, event):
        super().paintEvent(event)
        
        # Draw selection rectangle
        if self.selection_start and self.selection_end:
            painter = QPainter(self)
            painter.setPen(QPen(QColor(0, 120, 215), 2))
            painter.setBrush(QColor(0, 120, 215, 50))
            
            rect = QRect(self.selection_start, self.selection_end).normalized()
            painter.drawRect(rect)
            painter.end()


class SelectionPopup(QFrame):
    """Popup button that appears when text is selected."""
    explain_clicked = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setStyleSheet("""
            QFrame {
                background-color: #2d2d2d;
                border: 1px solid #555;
                border-radius: 8px;
                padding: 4px;
            }
            QPushButton {
                background-color: #4a9eff;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3a8eef;
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        
        self.explain_btn = QPushButton("🤖 Explain This")
        self.explain_btn.clicked.connect(self._on_explain)
        layout.addWidget(self.explain_btn)
        
        self.selected_text = ""
    
    def show_at(self, text: str, pos: QPoint):
        self.selected_text = text
        self.move(pos.x() - self.width() // 2, pos.y() + 10)
        self.show()
    
    def _on_explain(self):
        self.hide()
        self.explain_clicked.emit(self.selected_text)


class ChatPanel(QWidget):
    """Chat panel for interacting with Gemini."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Header
        header = QLabel("🤖 AI Reading Assistant")
        header.setStyleSheet("font-size: 16px; font-weight: bold; padding: 8px;")
        layout.addWidget(header)
        
        # Chat display
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #e0e0e0;
                border: 1px solid #333;
                border-radius: 8px;
                padding: 12px;
                font-size: 14px;
            }
        """)
        layout.addWidget(self.chat_display)
        
        # Quick action buttons
        actions_layout = QHBoxLayout()
        
        self.simplify_btn = QPushButton("🎯 Make Simpler")
        self.simplify_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 12px;
            }
            QPushButton:hover { background-color: #218838; }
            QPushButton:disabled { background-color: #666; }
        """)
        actions_layout.addWidget(self.simplify_btn)
        
        self.example_btn = QPushButton("📝 Give Example")
        self.example_btn.setStyleSheet("""
            QPushButton {
                background-color: #17a2b8;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 12px;
            }
            QPushButton:hover { background-color: #138496; }
            QPushButton:disabled { background-color: #666; }
        """)
        actions_layout.addWidget(self.example_btn)
        
        self.why_btn = QPushButton("❓ Why Important")
        self.why_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffc107;
                color: black;
                border: none;
                border-radius: 4px;
                padding: 8px 12px;
            }
            QPushButton:hover { background-color: #e0a800; }
            QPushButton:disabled { background-color: #666; }
        """)
        actions_layout.addWidget(self.why_btn)
        
        layout.addLayout(actions_layout)
        
        # Input area
        input_layout = QHBoxLayout()
        
        self.input_field = QTextEdit()
        self.input_field.setPlaceholderText("Ask a question about what you're reading...")
        self.input_field.setMaximumHeight(80)
        self.input_field.setStyleSheet("""
            QTextEdit {
                background-color: #2d2d2d;
                color: #e0e0e0;
                border: 1px solid #444;
                border-radius: 8px;
                padding: 8px;
            }
        """)
        input_layout.addWidget(self.input_field)
        
        self.send_btn = QPushButton("Send")
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a9eff;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 12px 24px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #3a8eef; }
            QPushButton:disabled { background-color: #666; }
        """)
        input_layout.addWidget(self.send_btn)
        
        layout.addLayout(input_layout)
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #888; font-size: 12px;")
        layout.addWidget(self.status_label)
    
    def add_user_message(self, text: str):
        self.chat_display.append(f'<div style="color: #4a9eff; margin: 8px 0;"><b>You:</b></div>')
        self.chat_display.append(f'<div style="margin-left: 12px; margin-bottom: 16px;">{text}</div>')
        self.chat_display.verticalScrollBar().setValue(
            self.chat_display.verticalScrollBar().maximum()
        )
    
    def add_ai_message_start(self):
        self.chat_display.append(f'<div style="color: #28a745; margin: 8px 0;"><b>AI Assistant:</b></div>')
        self.current_message = ""  # Accumulate chunks
        # Store the HTML before we start adding chunks
        self.html_before_message = self.chat_display.toHtml()
    
    def add_ai_chunk(self, text: str):
        # Accumulate the chunk
        self.current_message += text
        
        # Convert current accumulated message to HTML
        html_content = markdown_to_html(self.current_message)
        
        # Replace entire HTML with base + new formatted content
        # This prevents duplication by always starting from the saved state
        self.chat_display.setHtml(self.html_before_message)
        self.chat_display.append(f'<div style="margin-left: 12px;">{html_content}</div>')
        
        # Scroll to bottom
        self.chat_display.verticalScrollBar().setValue(
            self.chat_display.verticalScrollBar().maximum()
        )
    
    def add_ai_message_end(self):
        # Final render with proper formatting
        html_content = markdown_to_html(self.current_message)
        
        # Final update from the saved state
        self.chat_display.setHtml(self.html_before_message)
        self.chat_display.append(f'<div style="margin-left: 12px;">{html_content}</div><br>')
        
        self.chat_display.verticalScrollBar().setValue(
            self.chat_display.verticalScrollBar().maximum()
        )
        self.current_message = ""
        self.html_before_message = ""
    
    def set_status(self, text: str):
        self.status_label.setText(text)
    
    def set_buttons_enabled(self, enabled: bool):
        self.send_btn.setEnabled(enabled)
        self.simplify_btn.setEnabled(enabled)
        self.example_btn.setEnabled(enabled)
        self.why_btn.setEnabled(enabled)


class PDFReaderHelper(QMainWindow):
    """Main application window."""
    
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
        self.zoom = 1.5
        
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
        
        # Chat Panel (right side)
        self.chat_panel = ChatPanel()
        self.chat_panel.send_btn.clicked.connect(self.send_message)
        self.chat_panel.simplify_btn.clicked.connect(self.request_simpler)
        self.chat_panel.example_btn.clicked.connect(self.request_example)
        self.chat_panel.why_btn.clicked.connect(self.request_why_important)
        
        # Add to splitter
        splitter.addWidget(pdf_container)
        splitter.addWidget(self.chat_panel)
        splitter.setSizes([900, 500])
        
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
        self.zoom_spin.setRange(50, 300)
        self.zoom_spin.setValue(150)
        self.zoom_spin.setSuffix("%")
        self.zoom_spin.valueChanged.connect(self.change_zoom)
        toolbar.addWidget(self.zoom_spin)
        
        toolbar.addSeparator()
        
        # Analyze document button
        analyze_action = QAction("🔍 Analyze Document", self)
        analyze_action.triggered.connect(self.analyze_document)
        toolbar.addAction(analyze_action)
        
        # Detect complex terms button
        detect_action = QAction("📚 Find Complex Terms", self)
        detect_action.triggered.connect(self.detect_complex_terms)
        toolbar.addAction(detect_action)
    
    def open_pdf(self):
        """Open a PDF file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open PDF", "", "PDF Files (*.pdf)"
        )
        
        if file_path:
            try:
                self.doc = fitz.open(file_path)
                self.current_page = 0
                self.render_page()
                self.update_page_label()
                
                # Check cache for existing upload
                file_hash = get_file_hash(file_path)
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
                
                # Initialize chat with document context
                self.conversation_history = []  # Reset history for new document
                self.init_chat_with_document()
                self.chat_panel.chat_display.clear()
                self.chat_panel.add_ai_message_start()
                
                cache_status = "(cached)" if cached_entry and self.uploaded_file else "(uploaded)"
                self.chat_panel.add_ai_chunk(
                    f"📄 Loaded: {Path(file_path).name} {cache_status}\n\n"
                    "I'm ready to help you understand this document. You can:\n"
                    "• Select any text and click 'Explain This'\n"
                    "• Ask me questions in the chat\n"
                    "• Use 'Analyze Document' for an overview\n"
                    "• Use 'Find Complex Terms' to identify difficult concepts"
                )
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
    
    def next_page(self):
        """Go to next page."""
        if self.doc and self.current_page < len(self.doc) - 1:
            self.current_page += 1
            self.render_page()
            self.update_page_label()
    
    def change_zoom(self, value):
        """Change zoom level."""
        self.zoom = value / 100.0
        self.render_page()
    
    def on_text_selected(self, text: str, pos: QPoint):
        """Handle text selection."""
        if text:
            self.selection_popup.show_at(text, pos)
    
    def explain_selection(self, text: str):
        """Explain the selected text."""
        prompt = f"""Please explain this text in simple terms. The user is reading a document and selected this passage:

"{text}"

Provide a clear, beginner-friendly explanation. If it contains technical terms, define them. If it's a concept, give a simple analogy."""
        
        self.send_to_gemini(prompt, display_text=f"Explain: \"{text[:100]}{'...' if len(text) > 100 else ''}\"")
    
    def send_message(self):
        """Send user's message to Gemini."""
        text = self.chat_panel.input_field.toPlainText().strip()
        if text:
            self.chat_panel.input_field.clear()
            self.send_to_gemini(text, display_text=text)
    
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
    
    def send_to_gemini(self, prompt: str, display_text: str = None, include_pdf: bool = False):
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
        
        # Display user message
        self.chat_panel.add_user_message(display_text or prompt)
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
            getattr(self, 'uploaded_file', None),  # Use uploaded file reference
            self.conversation_history,
            getattr(self, 'system_instruction', '')
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
