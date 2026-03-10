"""
UI panels for notes and chat functionality.
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSpinBox, QSplitter, QTextEdit, QVBoxLayout, QWidget

from utils import markdown_to_html


class NotesPanel(QWidget):
    """Notes panel for taking PDF-specific notes."""

    notes_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # Header
        header = QLabel("📝 Document Notes")
        header.setStyleSheet("font-size: 16px; font-weight: bold; padding: 8px;")
        layout.addWidget(header)

        # Info text
        info = QLabel("Your notes are automatically saved per PDF")
        info.setStyleSheet("color: #888; font-size: 12px; padding: 0 8px 8px 8px;")
        layout.addWidget(info)

        # Notes editor
        self.notes_editor = QTextEdit()
        self.notes_editor.setPlaceholderText("Take notes about this document...")
        self.notes_editor.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #e0e0e0;
                border: 1px solid #333;
                border-radius: 8px;
                padding: 12px;
                font-size: 14px;
            }
        """)
        self.notes_editor.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.notes_editor)

        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #888; font-size: 11px; padding: 4px 8px;")
        layout.addWidget(self.status_label)

    def _on_text_changed(self):
        """Handle text changes."""
        self.status_label.setText("✓ Saved")
        self.notes_changed.emit(self.notes_editor.toPlainText())

    def set_notes(self, notes: str):
        """Set the notes content."""
        self.notes_editor.blockSignals(True)
        self.notes_editor.setPlainText(notes)
        self.notes_editor.blockSignals(False)
        if notes:
            self.status_label.setText("✓ Notes loaded")
        else:
            self.status_label.setText("")

    def get_notes(self) -> str:
        """Get the current notes content."""
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

        # Vertical splitter between chat display and input area
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setHandleWidth(6)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #444;
            }
            QSplitter::handle:hover {
                background-color: #4a9eff;
            }
        """)

        # Chat display using QWebEngineView for KaTeX support
        self.chat_display = QWebEngineView()
        self.chat_display.setStyleSheet("""
            QWebEngineView {
                background-color: #1e1e1e;
                border: 1px solid #333;
                border-radius: 8px;
            }
        """)
        self.chat_messages = []  # Store messages as list
        self._initialize_chat_html()
        splitter.addWidget(self.chat_display)

        # Bottom section: buttons + input + status
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(0, 0, 0, 0)

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

        bottom_layout.addLayout(actions_layout)

        # Input area with image preview
        input_container = QVBoxLayout()

        # Image preview (hidden by default)
        self.image_preview = QLabel()
        self.image_preview.setStyleSheet("""
            QLabel {
                background-color: #2d2d2d;
                border: 2px solid #4a9eff;
                border-radius: 4px;
                padding: 4px;
            }
        """)
        self.image_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_preview.setMaximumHeight(100)
        self.image_preview.hide()

        # Close button for image preview
        preview_container = QHBoxLayout()
        preview_container.addWidget(self.image_preview)

        self.clear_image_btn = QPushButton("✕")
        self.clear_image_btn.setFixedSize(24, 24)
        self.clear_image_btn.setStyleSheet("""
            QPushButton {
                background-color: #d9534f;
                color: white;
                border: none;
                border-radius: 12px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #c9302c; }
        """)
        self.clear_image_btn.clicked.connect(self.clear_image)
        self.clear_image_btn.hide()
        preview_container.addWidget(self.clear_image_btn, alignment=Qt.AlignmentFlag.AlignTop)

        input_container.addLayout(preview_container)

        # Text input
        input_layout = QHBoxLayout()

        self.input_field = QTextEdit()
        self.input_field.setPlaceholderText("Ask a question about what you're reading...")
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

        self.attached_image = None  # Store image bytes

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

        input_container.addLayout(input_layout)
        bottom_layout.addLayout(input_container)

        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #888; font-size: 12px;")
        bottom_layout.addWidget(self.status_label)

        splitter.addWidget(bottom_widget)
        splitter.setSizes([500, 150])
        layout.addWidget(splitter)

    def _initialize_chat_html(self):
        """Initialize the chat display with KaTeX support."""
        html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">
    <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>
    <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js"></script>
    <style>
        body {
            background-color: #1e1e1e;
            color: #e0e0e0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            font-size: FONT_SIZEpx;
            padding: 12px;
            margin: 0;
        }
        .message {
            margin-bottom: 16px;
        }
        .user-label {
            color: #4a9eff;
            font-weight: bold;
            margin: 8px 0;
        }
        .ai-label {
            color: #28a745;
            font-weight: bold;
            margin: 8px 0;
        }
        .message-content {
            margin-left: 12px;
        }
        .katex-display, .katex {
            color: #e0e0e0 !important;
        }
        pre {
            background-color: #2a2a2a;
            padding: 8px;
            border-radius: 4px;
            overflow-x: auto;
        }
        code {
            background-color: #2a2a2a;
            padding: 2px 4px;
            border-radius: 3px;
        }
    </style>
</head>
<body>
    <div id="chat-content"></div>
    <script>
        function renderMath() {
            renderMathInElement(document.body, {
                delimiters: [
                    {left: "\\\\[", right: "\\\\]", display: true},
                    {left: "\\\\(", right: "\\\\)", display: false}
                ],
                throwOnError: false
            });
        }
        // Initial render
        setTimeout(renderMath, 100);
    </script>
</body>
</html>
        """.replace("FONT_SIZE", str(self.chat_font_size))
        self.chat_display.setHtml(html)

    def _update_chat_display(self):
        """Update the entire chat display."""
        messages_html = ""
        for msg in self.chat_messages:
            if msg["type"] == "user":
                messages_html += f'<div class="message"><div class="user-label">You:</div><div class="message-content">{msg["content"]}</div></div>'
            elif msg["type"] == "ai":
                html_content = markdown_to_html(msg["content"])
                messages_html += f'<div class="message"><div class="ai-label">AI Assistant:</div><div class="message-content">{html_content}</div></div>'

        # Escape backticks and handle special characters in messages_html
        messages_html_escaped = messages_html.replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")

        # Inject content and render math - wait for DOM to be ready
        script = f"""
            (function() {{
                var chatContent = document.getElementById('chat-content');
                if (chatContent) {{
                    chatContent.innerHTML = `{messages_html_escaped}`;
                    if (typeof renderMath === 'function') {{
                        renderMath();
                    }}
                    window.scrollTo(0, document.body.scrollHeight);
                }}
            }})();
        """
        self.chat_display.page().runJavaScript(script)

    def clear(self):
        """Clear all chat messages."""
        self.chat_messages = []
        self._update_chat_display()

    def add_user_message(self, text: str):
        self.chat_messages.append({"type": "user", "content": text})
        self._update_chat_display()

    def add_ai_message_start(self):
        self.current_message = ""  # Accumulate chunks
        self.current_message_index = len(self.chat_messages)
        self.chat_messages.append({"type": "ai", "content": ""})

    def add_ai_chunk(self, text: str):
        # Accumulate the chunk
        self.current_message += text
        self.chat_messages[self.current_message_index]["content"] = self.current_message
        self._update_chat_display()

    def add_ai_message_end(self):
        # Final update
        self._update_chat_display()
        self.current_message = ""

    def set_status(self, text: str):
        self.status_label.setText(text)

    def set_buttons_enabled(self, enabled: bool):
        self.send_btn.setEnabled(enabled)
        self.simplify_btn.setEnabled(enabled)
        self.example_btn.setEnabled(enabled)
        self.why_btn.setEnabled(enabled)

    def restore_chat_history(self, history: list):
        """Restore chat history from saved data."""
        self.chat_messages = []
        for msg in history:
            if msg["role"] == "user":
                self.chat_messages.append({"type": "user", "content": msg["content"]})
            elif msg["role"] == "assistant":
                self.chat_messages.append({"type": "ai", "content": msg["content"]})
        self._update_chat_display()

    def set_font_size(self, size: int):
        """Set the chat font size."""
        self.chat_font_size = size
        self.font_size_spin.blockSignals(True)
        self.font_size_spin.setValue(size)
        self.font_size_spin.blockSignals(False)
        self._initialize_chat_html()
        self._update_chat_display()

    def change_font_size(self, size: int):
        """Handle font size change."""
        self.chat_font_size = size
        self._initialize_chat_html()
        self._update_chat_display()

    def set_image_attachment(self, image_bytes: bytes, prompt_text: str = ""):
        """Set an image attachment with optional prompt text."""
        self.attached_image = image_bytes

        # Show image preview
        pixmap = QPixmap()
        pixmap.loadFromData(image_bytes)
        scaled_pixmap = pixmap.scaled(
            150, 100, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        )
        self.image_preview.setPixmap(scaled_pixmap)
        self.image_preview.show()
        self.clear_image_btn.show()

        # Set prompt text if provided
        if prompt_text:
            self.input_field.setPlainText(prompt_text)

        # Focus on input field
        self.input_field.setFocus()

    def clear_image(self):
        """Clear the image attachment."""
        self.attached_image = None
        self.image_preview.clear()
        self.image_preview.hide()
        self.clear_image_btn.hide()

    def get_image_attachment(self):
        """Get the current image attachment."""
        return self.attached_image
