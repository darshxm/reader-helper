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
    QToolTip, QMenu, QComboBox, QTabWidget
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QPoint, QTimer, QRect
from PyQt6.QtGui import (
    QPixmap, QImage, QAction, QCursor, QFont, QTextCursor,
    QPainter, QColor, QPen
)
from google import genai
from google.genai import types

MODEL = "gemini-3-flash-preview"  # Default model
AVAILABLE_MODELS = [
    "gemini-3-flash-preview",
    "gemini-3-pro-preview",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.5-pro"
]
CACHE_FILE = Path(__file__).parent / ".file_cache.json"
CONFIG_FILE = Path(__file__).parent / ".config.json"
NOTES_FILE = Path(__file__).parent / ".notes.json"
CHAT_HISTORY_FILE = Path(__file__).parent / ".chat_history.json"
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


def load_config() -> dict:
    """Load user configuration from disk."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_config(config: dict):
    """Save user configuration to disk."""
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        print(f"Warning: Failed to save config: {e}")


def load_notes() -> dict:
    """Load all PDF notes from disk."""
    if NOTES_FILE.exists():
        try:
            with open(NOTES_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_notes(notes: dict):
    """Save all PDF notes to disk."""
    try:
        with open(NOTES_FILE, "w") as f:
            json.dump(notes, f, indent=2)
    except Exception as e:
        print(f"Warning: Failed to save notes: {e}")


def load_chat_history() -> dict:
    """Load all PDF chat histories from disk."""
    if CHAT_HISTORY_FILE.exists():
        try:
            with open(CHAT_HISTORY_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_chat_history(chat_history: dict):
    """Save all PDF chat histories to disk."""
    try:
        with open(CHAT_HISTORY_FILE, "w") as f:
            json.dump(chat_history, f, indent=2)
    except Exception as e:
        print(f"Warning: Failed to save chat history: {e}")

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
    
    def __init__(self, client, message: str, model: str = MODEL,
                 uploaded_file=None, conversation_history: list = None,
                 system_instruction: str = ""):
        super().__init__()
        self.client = client
        self.message = message
        self.model = model
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
                model=self.model,
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


class NotesPanel(QWidget):
    """Notes panel for taking PDF-specific notes."""
    notes_changed = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self._save_timer = QTimer()
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._emit_notes_changed)
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Header
        header = QLabel("📝 My Notes")
        header.setStyleSheet("font-size: 16px; font-weight: bold; padding: 8px;")
        layout.addWidget(header)
        
        # Info label
        info = QLabel("Notes are automatically saved for this PDF")
        info.setStyleSheet("color: #888; font-size: 12px; padding: 0 8px 8px 8px;")
        layout.addWidget(info)
        
        # Notes editor
        self.notes_editor = QTextEdit()
        self.notes_editor.setPlaceholderText(
            "Take notes here...\n\n"
            "• Jot down key insights\n"
            "• Questions to explore\n"
            "• Important concepts\n"
            "• Your thoughts and reflections"
        )
        self.notes_editor.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #e0e0e0;
                border: 1px solid #333;
                border-radius: 8px;
                padding: 12px;
                font-size: 14px;
                font-family: 'Courier New', monospace;
            }
        """)
        self.notes_editor.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.notes_editor)
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #888; font-size: 11px; padding: 4px 8px;")
        layout.addWidget(self.status_label)
    
    def _on_text_changed(self):
        """Debounce text changes before saving."""
        self._save_timer.stop()
        self._save_timer.start(1000)  # Save after 1 second of inactivity
        self.status_label.setText("Unsaved changes...")
    
    def _emit_notes_changed(self):
        """Emit signal with current notes content."""
        self.notes_changed.emit(self.notes_editor.toPlainText())
        self.status_label.setText("✓ Saved")
        QTimer.singleShot(2000, lambda: self.status_label.setText(""))
    
    def set_notes(self, text: str):
        """Load notes into the editor."""
        self.notes_editor.blockSignals(True)  # Prevent triggering save
        self.notes_editor.setPlainText(text)
        self.notes_editor.blockSignals(False)
        self.status_label.setText("")
    
    def get_notes(self) -> str:
        """Get current notes content."""
        return self.notes_editor.toPlainText()
    
    def clear_notes(self):
        """Clear the notes editor."""
        self.notes_editor.blockSignals(True)
        self.notes_editor.clear()
        self.notes_editor.blockSignals(False)
        self.status_label.setText("")


class ChatPanel(QWidget):
    """Chat panel for interacting with Gemini."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.chat_font_size = 14  # Default font size
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Header with font size control
        header_layout = QHBoxLayout()
        header = QLabel("🤖 AI Reading Assistant")
        header.setStyleSheet("font-size: 16px; font-weight: bold; padding: 8px;")
        header_layout.addWidget(header)
        
        header_layout.addStretch()
        
        # Font size control
        font_size_label = QLabel("Font:")
        font_size_label.setStyleSheet("color: #e0e0e0; padding: 4px;")
        header_layout.addWidget(font_size_label)
        
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(10, 24)
        self.font_size_spin.setValue(self.chat_font_size)
        self.font_size_spin.setSuffix(" pt")
        self.font_size_spin.setToolTip("Adjust chat text size")
        self.font_size_spin.setStyleSheet("""
            QSpinBox {
                background-color: #3d3d3d;
                color: #e0e0e0;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 4px;
            }
        """)
        self.font_size_spin.valueChanged.connect(self.change_font_size)
        header_layout.addWidget(self.font_size_spin)
        
        layout.addLayout(header_layout)
        
        # Chat display
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.update_chat_display_style()
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
    
    def restore_chat_history(self, history: list):
        """Restore chat history from saved data."""
        self.chat_display.clear()
        for msg in history:
            if msg["role"] == "user":
                self.add_user_message(msg["content"])
            elif msg["role"] == "assistant":
                self.add_ai_message_start()
                self.current_message = msg["content"]
                self.add_ai_message_end()
    
    def set_font_size(self, size: int):
        """Set the chat font size."""
        self.chat_font_size = size
        self.font_size_spin.blockSignals(True)
        self.font_size_spin.setValue(size)
        self.font_size_spin.blockSignals(False)
        self.update_chat_display_style()
    
    def change_font_size(self, size: int):
        """Handle font size change."""
        self.chat_font_size = size
        self.update_chat_display_style()
    
    def update_chat_display_style(self):
        """Update chat display stylesheet with current font size."""
        self.chat_display.setStyleSheet(f"""
            QTextEdit {{
                background-color: #1e1e1e;
                color: #e0e0e0;
                border: 1px solid #333;
                border-radius: 8px;
                padding: 12px;
                font-size: {self.chat_font_size}px;
            }}
        """)


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
        self.current_pdf_hash = None  # Track current PDF for notes
        
        # Load user configuration and notes
        self.config = load_config()
        self.selected_model = self.config.get("preferred_model", MODEL)
        self.zoom = self.config.get("default_zoom", 1.5)  # Load default zoom from config
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
                self.chat_panel.chat_display.clear()
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
            self.selected_model,  # Use selected model
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
