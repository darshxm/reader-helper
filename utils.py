"""
Utility functions for PDF Reader Helper.
Handles file operations, configuration, and markdown conversion.
"""

import json
import hashlib
import re
from pathlib import Path
from typing import Optional

# File paths
CACHE_FILE = Path(__file__).parent / ".file_cache.json"
CONFIG_FILE = Path(__file__).parent / ".config.json"
NOTES_FILE = Path(__file__).parent / ".notes.json"
CHAT_HISTORY_FILE = Path(__file__).parent / ".chat_history.json"

# Constants
CACHE_EXPIRY_HOURS = 47  # Files API keeps files for 48 hours, we use 47 to be safe
MODEL = "gemini-3-flash-preview"  # Default model
AVAILABLE_MODELS = [
    "gemini-3-flash-preview",
    "gemini-3-pro-preview",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.5-pro"
]


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
    
    # Tables - parse markdown tables into HTML
    lines = text.split('\n')
    in_table = False
    table_lines = []
    result = []
    
    for line in lines:
        # Check if line is a table row (contains |)
        if '|' in line and line.strip():
            # Skip separator lines (|---|---|)
            if re.match(r'^\s*\|[\s\-:]+\|\s*$', line):
                continue
            
            if not in_table:
                in_table = True
                table_lines = []
            
            table_lines.append(line)
        else:
            # End of table
            if in_table:
                result.append(_convert_table_to_html(table_lines))
                in_table = False
                table_lines = []
            result.append(line)
    
    # Handle table at end of text
    if in_table:
        result.append(_convert_table_to_html(table_lines))
    
    text = '\n'.join(result)
    
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


def _convert_table_to_html(table_lines: list) -> str:
    """Convert markdown table lines to HTML table."""
    if not table_lines:
        return ""
    
    html = ['<table style="border-collapse: collapse; margin: 12px 0; width: 100%; background-color: #2a2a2a; border-radius: 4px; overflow: hidden;">']
    
    # First row is header
    header_row = table_lines[0]
    cells = [cell.strip() for cell in header_row.split('|') if cell.strip()]
    
    html.append('<thead>')
    html.append('<tr style="background-color: #3a3a3a;">')
    for cell in cells:
        html.append(f'<th style="padding: 10px; text-align: left; border-bottom: 2px solid #4a9eff; color: #4a9eff; font-weight: bold;">{cell}</th>')
    html.append('</tr>')
    html.append('</thead>')
    
    # Data rows
    if len(table_lines) > 1:
        html.append('<tbody>')
        for row_line in table_lines[1:]:
            cells = [cell.strip() for cell in row_line.split('|') if cell.strip()]
            html.append('<tr style="border-bottom: 1px solid #3a3a3a;">')
            for cell in cells:
                html.append(f'<td style="padding: 10px; color: #e0e0e0;">{cell}</td>')
            html.append('</tr>')
        html.append('</tbody>')
    
    html.append('</table>')
    return ''.join(html)
