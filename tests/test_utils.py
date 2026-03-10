"""Tests for utility functions."""

import tempfile

from utils import get_file_hash, markdown_to_html


class TestMarkdownToHtml:
    def test_bold(self):
        result = markdown_to_html("**hello**")
        assert "<b>hello</b>" in result

    def test_italic(self):
        result = markdown_to_html("*hello*")
        assert "<i>hello</i>" in result

    def test_inline_code(self):
        result = markdown_to_html("`code`")
        assert "<code" in result and "code" in result

    def test_headers(self):
        result = markdown_to_html("# Title")
        assert "<h1" in result and "Title" in result

    def test_bullet_list(self):
        result = markdown_to_html("- item one\n- item two")
        assert "<ul" in result
        assert "<li>item one</li>" in result
        assert "<li>item two</li>" in result

    def test_numbered_list(self):
        result = markdown_to_html("1. first\n2. second")
        assert "1." in result and "first" in result

    def test_inline_math_preserved(self):
        result = markdown_to_html("The formula $x^2$ is simple")
        assert "katex-inline" in result

    def test_display_math_preserved(self):
        result = markdown_to_html("$$E = mc^2$$")
        assert "katex-display" in result

    def test_plain_text(self):
        result = markdown_to_html("plain text")
        assert "plain text" in result

    def test_table(self):
        md = "| A | B |\n|---|---|\n| 1 | 2 |"
        result = markdown_to_html(md)
        assert "<table" in result
        assert "<th" in result


class TestGetFileHash:
    def test_hash_deterministic(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            f.write(b"test content")
            f.flush()
            h1 = get_file_hash(f.name)
            h2 = get_file_hash(f.name)
        assert h1 == h2

    def test_different_content_different_hash(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f1:
            f1.write(b"content a")
            f1.flush()
            with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f2:
                f2.write(b"content b")
                f2.flush()
                assert get_file_hash(f1.name) != get_file_hash(f2.name)
