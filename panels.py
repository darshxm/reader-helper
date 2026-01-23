"""
UI panels for notes and chat functionality.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTextEdit, QSpinBox, QFrame
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QPixmap
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
        layout.addLayout(input_container)
        
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
    
    def set_image_attachment(self, image_bytes: bytes, prompt_text: str = ""):
        """Set an image attachment with optional prompt text."""
        self.attached_image = image_bytes
        
        # Show image preview
        pixmap = QPixmap()
        pixmap.loadFromData(image_bytes)
        scaled_pixmap = pixmap.scaled(150, 100, Qt.AspectRatioMode.KeepAspectRatio, 
                                      Qt.TransformationMode.SmoothTransformation)
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
