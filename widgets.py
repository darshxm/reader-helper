"""
Custom Qt widgets for PDF display and text selection.
"""

import fitz  # PyMuPDF
from PyQt6.QtCore import QPoint, QRect, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QImage, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton


class PDFPageWidget(QLabel):
    """Widget to display a single PDF page with text selection support."""

    text_selected = pyqtSignal(str, QPoint)  # Selected text and position
    selection_made = pyqtSignal(str, object, QPoint)  # text, image_bytes, position

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

            # Get text and image in selection area
            x0 = min(self.selection_start.x(), self.selection_end.x()) / self.zoom
            y0 = min(self.selection_start.y(), self.selection_end.y()) / self.zoom
            x1 = max(self.selection_start.x(), self.selection_end.x()) / self.zoom
            y1 = max(self.selection_start.y(), self.selection_end.y()) / self.zoom

            rect = fitz.Rect(x0, y0, x1, y1)
            text = self.page.get_text("text", clip=rect).strip()

            # Extract image from selection area
            image_bytes = None
            try:
                # Capture the selected region as an image
                mat = fitz.Matrix(2.0, 2.0)  # Higher resolution for image extraction
                pix = self.page.get_pixmap(matrix=mat, clip=rect)
                if pix.width > 20 and pix.height > 20:  # Only consider if meaningful size
                    image_bytes = pix.tobytes("png")
            except Exception as e:
                print(f"Failed to extract image: {e}")

            if text or image_bytes:
                # Convert position to screen coordinates
                global_pos = self.mapToGlobal(self.selection_end)
                self.selection_made.emit(text, image_bytes, global_pos)
                # Keep backward compatibility
                if text:
                    self.text_selected.emit(text, global_pos)

            self.selection_start = None
            self.selection_end = None
            self.update()

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
    """Popup button that appears when text/image is selected."""

    explain_clicked = pyqtSignal(str, object)  # text, image_bytes

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
        self.selected_image = None

    def show_at(self, text: str, image_bytes: object, pos: QPoint):
        self.selected_text = text
        self.selected_image = image_bytes

        # Update button text based on content
        if text and image_bytes:
            self.explain_btn.setText("🤖 Explain Text & Image")
        elif image_bytes:
            self.explain_btn.setText("🖼️ Explain This Image")
        else:
            self.explain_btn.setText("🤖 Explain This")

        self.move(pos.x() - self.width() // 2, pos.y() + 10)
        self.show()

    def _on_explain(self):
        self.hide()
        self.explain_clicked.emit(self.selected_text, self.selected_image)
