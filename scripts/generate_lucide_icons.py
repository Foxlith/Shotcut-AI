#!/usr/bin/env python3
"""
generate_lucide_icons.py

Generates modern Lucide-style stroke icon assets for Shotcut AI Phase 2.
- Grid: 24x24 viewBox
- Stroke: 1.75 width, round linecap, round linejoin
- Palette: #9AA1AD (Grafito Muted idle state)
- Outputs:
  1. icons/dark/32x32/<name>.svg (Vector master)
  2. icons/dark/32x32/<name>.png (High-fidelity 32x32 raster with alpha anti-aliasing)
  3. Updates icons/resources.qrc to register all .svg files alongside .png files
"""

import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtGui import QPainter, QImage
from PySide6.QtCore import QByteArray, Qt

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DARK_ICONS_DIR = PROJECT_ROOT / "icons" / "dark" / "32x32"
RESOURCES_QRC = PROJECT_ROOT / "icons" / "resources.qrc"

STROKE_COLOR = "#9AA1AD"
STROKE_WIDTH = "1.75"

SVG_ICONS = {
    # ---------------------------------------------------------
    # 1. Player Transport Controls (8)
    # ---------------------------------------------------------
    "media-playback-start": """
        <polygon points="6 4 20 12 6 20 6 4" />
    """,
    "media-playback-pause": """
        <rect x="6" y="4" width="4" height="16" rx="1" />
        <rect x="14" y="4" width="4" height="16" rx="1" />
    """,
    "media-seek-backward": """
        <polygon points="11 19 2 12 11 5 11 19" />
        <polygon points="22 19 13 12 22 5 22 19" />
    """,
    "media-seek-forward": """
        <polygon points="13 19 22 12 13 5 13 19" />
        <polygon points="2 19 11 12 2 5 2 19" />
    """,
    "media-skip-backward": """
        <polygon points="19 20 9 12 19 4 19 20" />
        <line x1="5" y1="19" x2="5" y2="5" />
    """,
    "media-skip-forward": """
        <polygon points="5 4 15 12 5 20 5 4" />
        <line x1="19" y1="5" x2="19" y2="19" />
    """,
    "media-playback-loop": """
        <path d="m17 2 4 4-4 4" />
        <path d="M3 11v-1a4 4 0 0 1 4-4h14" />
        <path d="m7 22-4-4 4-4" />
        <path d="M21 13v1a4 4 0 0 1-4 4H3" />
    """,
    "media-playback-stop": """
        <rect width="14" height="14" x="5" y="5" rx="2" />
    """,
    "player-volume": """
        <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
        <path d="M15.54 8.46a5 5 0 0 1 0 7.07" />
        <path d="M19.07 4.93a10 10 0 0 1 0 14.14" />
    """,

    # ---------------------------------------------------------
    # 2. Timeline Editing Tools (10)
    # ---------------------------------------------------------
    "edit-cut": """
        <circle cx="6" cy="6" r="3" />
        <path d="M8.12 8.12 12 12" />
        <path d="M20 4 8.12 15.88" />
        <circle cx="6" cy="18" r="3" />
        <path d="M14.8 14.8 20 20" />
    """,
    "edit-copy": """
        <rect width="13" height="13" x="9" y="9" rx="2" ry="2" />
        <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
    """,
    "edit-paste": """
        <rect width="8" height="4" x="8" y="2" rx="1" ry="1" />
        <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2" />
        <path d="M12 11v6" />
        <path d="m9 14 3-3 3 3" />
    """,
    "edit-delete": """
        <path d="M3 6h18" />
        <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6" />
        <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2" />
        <line x1="10" x2="10" y1="11" y2="17" />
        <line x1="14" x2="14" y1="11" y2="17" />
    """,
    "split": """
        <line x1="12" y1="3" x2="12" y2="21" stroke-dasharray="2 2" />
        <path d="M8 8H3v8h5" />
        <path d="M16 8h5v8h-5" />
        <polyline points="6 10 4 12 6 14" />
        <polyline points="18 10 20 12 18 14" />
    """,
    "slice": """
        <rect x="3" y="6" width="7" height="12" rx="1.5" />
        <rect x="14" y="6" width="7" height="12" rx="1.5" />
        <line x1="12" y1="3" x2="12" y2="21" />
    """,
    "lift": """
        <polyline points="7 10 12 5 17 10" />
        <line x1="12" y1="5" x2="12" y2="15" />
        <path d="M4 19h16" />
        <path d="M4 15v4" />
        <path d="M20 15v4" />
    """,
    "overwrite": """
        <polyline points="7 10 12 15 17 10" />
        <line x1="12" y1="5" x2="12" y2="15" />
        <rect x="4" y="17" width="16" height="4" rx="1" />
    """,
    "list-add": """
        <line x1="12" y1="5" x2="12" y2="19" />
        <line x1="5" y1="12" x2="19" y2="12" />
    """,
    "list-remove": """
        <line x1="5" y1="12" x2="19" y2="12" />
    """,
    "marker": """
        <path d="M5 3h14v10l-7 8-7-8V3z" />
        <circle cx="12" cy="8" r="2" />
    """,

    # ---------------------------------------------------------
    # 3. Timeline Mode Toggles (4)
    # ---------------------------------------------------------
    "snap": """
        <path d="M5 14V8a7 7 0 0 1 14 0v6" />
        <path d="M9 14V8a3 3 0 0 1 6 0v6" />
        <line x1="5" y1="11" x2="9" y2="11" />
        <line x1="15" y1="11" x2="19" y2="11" />
    """,
    "ripple-all": """
        <path d="M3 6h12" /><path d="m12 3 3 3-3 3" />
        <path d="M3 12h15" /><path d="m15 9 3 3-3 3" />
        <path d="M3 18h12" /><path d="m12 15 3 3-3 3" />
        <line x1="2" y1="3" x2="2" y2="21" />
    """,
    "ripple-marker": """
        <path d="M6 3h8v8l-4 5-4-5V3z" />
        <circle cx="10" cy="7" r="1.5" />
        <path d="M17 7a5 5 0 0 1 0 8" />
        <path d="M20 5a8 8 0 0 1 0 12" />
    """,
    "scrub_drag": """
        <path d="M18 11V6a2 2 0 0 0-4 0v4" />
        <path d="M14 10V4a2 2 0 0 0-4 0v6" />
        <path d="M10 10V6a2 2 0 0 0-4 0v8" />
        <path d="M6 14v-1a2 2 0 0 0-4 0v4a8 8 0 0 0 8 8h3a8 8 0 0 0 8-8v-6a2 2 0 0 0-3-1.7" />
    """,

    # ---------------------------------------------------------
    # 4. Track Header Actions (6)
    # ---------------------------------------------------------
    "layer-visible-on": """
        <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z" />
        <circle cx="12" cy="12" r="3" />
    """,
    "layer-visible-off": """
        <path d="M9.88 9.88a3 3 0 1 0 4.24 4.24" />
        <path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68" />
        <path d="M6.61 6.61A13.526 13.526 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61" />
        <line x1="2" x2="22" y1="2" y2="22" />
    """,
    "object-locked": """
        <rect width="18" height="11" x="3" y="11" rx="2" ry="2" />
        <path d="M7 11V7a5 5 0 0 1 10 0v4" />
    """,
    "object-unlocked": """
        <rect width="18" height="11" x="3" y="11" rx="2" ry="2" />
        <path d="M7 11V7a5 5 0 0 1 9.9-1" />
    """,
    "audio-volume-high": """
        <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
        <path d="M15.54 8.46a5 5 0 0 1 0 7.07" />
        <path d="M19.07 4.93a10 10 0 0 1 0 14.14" />
    """,
    "audio-volume-muted": """
        <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
        <line x1="22" x2="16" y1="9" y2="15" />
        <line x1="16" x2="22" y1="9" y2="15" />
    """,

    # ---------------------------------------------------------
    # 5. Global Navigation & Header (8)
    # ---------------------------------------------------------
    "document-new": """
        <path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z" />
        <path d="M14 2v4a2 2 0 0 0 2 2h4" />
        <path d="M12 18v-6" />
        <path d="M9 15h6" />
    """,
    "document-open": """
        <path d="m6 14 1.45-2.9A2 2 0 0 1 9.24 10H20a2 2 0 0 1 1.94 2.5l-1.55 6a2 2 0 0 1-1.94 1.5H4a2 2 0 0 1-2-2V5c0-1.1.9-2 2-2h3.93a2 2 0 0 1 1.66.9l.82 1.2a2 2 0 0 0 1.66.9H18a2 2 0 0 1 2 2v2" />
    """,
    "document-save": """
        <path d="M15.2 3a2 2 0 0 1 1.4.6l3.8 3.8a2 2 0 0 1 .6 1.4V19a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z" />
        <path d="M17 21v-7a1 1 0 0 0-1-1H8a1 1 0 0 0-1 1v7" />
        <path d="M7 3v4a1 1 0 0 0 1 1h7" />
    """,
    "edit-undo": """
        <path d="M9 14 4 9l5-5" />
        <path d="M4 9h10.5a5.5 5.5 0 0 1 5.5 5.5v0a5.5 5.5 0 0 1-5.5 5.5H11" />
    """,
    "edit-redo": """
        <path d="m15 14 5-5-5-5" />
        <path d="M20 9H9.5A5.5 5.5 0 0 0 4 14.5v0A5.5 5.5 0 0 0 9.5 20H13" />
    """,
    "view-filter": """
        <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3" />
    """,
    "help-contextual": """
        <circle cx="12" cy="12" r="10" />
        <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
        <line x1="12" y1="17" x2="12.01" y2="17" />
    """,
    "audio-meter": """
        <line x1="5" y1="20" x2="5" y2="12" />
        <line x1="9.67" y1="20" x2="9.67" y2="6" />
        <line x1="14.33" y1="20" x2="14.33" y2="9" />
        <line x1="19" y1="20" x2="19" y2="15" />
        <line x1="2" y1="21" x2="22" y2="21" />
    """,

    # ---------------------------------------------------------
    # 6. Additional Main Toolbar & Dock Icons
    # ---------------------------------------------------------
    "window-close": """
        <line x1="18" y1="6" x2="6" y2="18" />
        <line x1="6" y1="6" x2="18" y2="18" />
    """,
    "media-record": """
        <circle cx="12" cy="12" r="9" />
        <circle cx="12" cy="12" r="4" fill="#9AA1AD" />
    """,
    "view-fullscreen": """
        <path d="M8 3H5a2 2 0 0 0-2 2v3" />
        <path d="M21 8V5a2 2 0 0 0-2-2h-3" />
        <path d="M3 16v3a2 2 0 0 0 2 2h3" />
        <path d="M16 21h3a2 2 0 0 0 2-2v-3" />
    """,
    "system-file-manager": """
        <path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z" />
        <path d="M2 10h20" />
    """,
    "view-history": """
        <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
        <path d="M3 3v5h5" />
        <path d="M12 7v5l4 2" />
    """,
    "run-build": """
        <path d="m15 12-8.5 8.5a2.12 2.12 0 0 1-3-3L12 9" />
        <path d="M17.64 15 22 10.64" />
        <path d="m20.91 3.26-6.6 6.6" />
        <path d="M13.5 4.5 19.5 10.5" />
    """,
    "chronometer": """
        <line x1="10" x2="14" y1="2" y2="2" />
        <line x1="12" x2="12" y1="14" y2="8" />
        <circle cx="12" cy="14" r="8" />
    """,
    "document-edit": """
        <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
        <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
    """,
    "view-media-playlist": """
        <path d="M21 6H3" />
        <path d="M15 12H3" />
        <path d="M17 18H3" />
        <polygon points="17 9 22 12 17 15 17 9" />
    """,
    "dialog-information": """
        <circle cx="12" cy="12" r="10" />
        <line x1="12" y1="16" x2="12" y2="12" />
        <line x1="12" y1="8" x2="12.01" y2="8" />
    """,
    "document-open-recent": """
        <circle cx="12" cy="12" r="10" />
        <polyline points="12 6 12 12 16 14" />
    """,
    "subtitle": """
        <rect width="18" height="14" x="3" y="5" rx="2" ry="2" />
        <path d="M7 15h4M15 15h2M7 11h2M13 11h4" />
    """,
    "view-time-schedule": """
        <rect width="18" height="18" x="3" y="4" rx="2" ry="2" />
        <line x1="16" y1="2" x2="16" y2="6" />
        <line x1="8" y1="2" x2="8" y2="6" />
        <line x1="3" y1="10" x2="21" y2="10" />
    """,
    "edit-clear": """
        <circle cx="12" cy="12" r="10" />
        <line x1="15" y1="9" x2="9" y2="15" />
        <line x1="9" y1="9" x2="15" y2="15" />
    """,
    "zoom-fit-best": """
        <path d="M3 7V5a2 2 0 0 1 2-2h2" />
        <path d="M17 3h2a2 2 0 0 1 2 2v2" />
        <path d="M21 17v2a2 2 0 0 1-2 2h-2" />
        <path d="M7 21H5a2 2 0 0 1-2-2v-2" />
        <rect width="8" height="8" x="8" y="8" rx="1" />
    """,
    "zoom-in": """
        <circle cx="11" cy="11" r="8" />
        <line x1="21" y1="21" x2="16.65" y2="16.65" />
        <line x1="11" y1="8" x2="11" y2="14" />
        <line x1="8" y1="11" x2="14" y2="11" />
    """,
    "zoom-out": """
        <circle cx="11" cy="11" r="8" />
        <line x1="21" y1="21" x2="16.65" y2="16.65" />
        <line x1="8" y1="11" x2="14" y2="11" />
    """,
    "zoom-original": """
        <circle cx="11" cy="11" r="8" />
        <line x1="21" y1="21" x2="16.65" y2="16.65" />
        <line x1="11" y1="8" x2="11" y2="14" />
    """,
    "target": """
        <circle cx="12" cy="12" r="10" />
        <circle cx="12" cy="12" r="6" />
        <circle cx="12" cy="12" r="2" />
    """,
    "show-menu": """
        <line x1="4" x2="20" y1="12" y2="12" />
        <line x1="4" x2="20" y1="6" y2="6" />
        <line x1="4" x2="20" y1="18" y2="18" />
    """,
    "format-indent-less": """
        <polyline points="7 8 3 12 7 16" />
        <line x1="21" x2="11" y1="12" y2="12" />
        <line x1="21" x2="11" y1="6" y2="6" />
        <line x1="21" x2="11" y1="18" y2="18" />
    """,
    "format-indent-more": """
        <polyline points="3 8 7 12 3 16" />
        <line x1="21" x2="11" y1="12" y2="12" />
        <line x1="21" x2="11" y1="6" y2="6" />
        <line x1="21" x2="11" y1="18" y2="18" />
    """,
    "view-grid": """
        <rect width="7" height="7" x="3" y="3" rx="1" />
        <rect width="7" height="7" x="14" y="3" rx="1" />
        <rect width="7" height="7" x="14" y="14" rx="1" />
        <rect width="7" height="7" x="3" y="14" rx="1" />
    """,
    # Reviewer R2 dock & toolbar coherence additions:
    "audio-input-microphone": """
        <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
        <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
        <line x1="12" x2="12" y1="19" y2="22" />
    """,
    "folder-new": """
        <path d="M12 10v6" />
        <path d="M9 13h6" />
        <path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z" />
    """,
    "list-add-files": """
        <path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z" />
        <path d="M14 2v4a2 2 0 0 0 2 2h4" />
        <line x1="12" x2="12" y1="11" y2="17" />
        <line x1="9" x2="15" y1="14" y2="14" />
    """,
    "dialog-ok": """
        <polyline points="20 6 9 17 4 12" />
    """,
    "view-list-details": """
        <rect width="18" height="7" x="3" y="3" rx="1" />
        <rect width="18" height="7" x="3" y="14" rx="1" />
    """,
    "view-list-icons": """
        <rect width="6" height="6" x="4" y="4" rx="1" />
        <rect width="6" height="6" x="14" y="4" rx="1" />
        <rect width="6" height="6" x="4" y="14" rx="1" />
        <rect width="6" height="6" x="14" y="14" rx="1" />
    """,
    "view-list-text": """
        <line x1="8" x2="21" y1="6" y2="6" />
        <line x1="8" x2="21" y1="12" y2="12" />
        <line x1="8" x2="21" y1="18" y2="18" />
        <line x1="3" x2="3.01" y1="6" y2="6" />
        <line x1="3" x2="3.01" y1="12" y2="12" />
        <line x1="3" x2="3.01" y1="18" y2="18" />
    """,
    "server-database": """
        <ellipse cx="12" cy="5" rx="9" ry="3" />
        <path d="M3 5v14a9 3 0 0 0 18 0V5" />
        <path d="M3 12a9 3 0 0 0 18 0" />
    """,
    "view-refresh": """
        <path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8" />
        <path d="M21 3v5h-5" />
        <path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16" />
        <path d="M3 21v-5h5" />
    """,
    "document-import": """
        <path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z" />
        <path d="M14 2v4a2 2 0 0 0 2 2h4" />
        <path d="M12 18v-6" />
        <path d="m9 15 3-3 3 3" />
    """,
    "document-export": """
        <path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z" />
        <path d="M14 2v4a2 2 0 0 0 2 2h4" />
        <path d="M12 12v6" />
        <path d="m9 15 3 3 3-3" />
    """,
    # Reviewer R3 comprehensive dock & secondary toolbar additions:
    "view-choose": """
        <rect width="18" height="18" x="3" y="3" rx="2" />
        <path d="M9 3v18" />
    """,
    "quickopen": """
        <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
    """,
    "keyframes-filter-in": """
        <line x1="4" y1="4" x2="4" y2="20" />
        <path d="M4 12h14" />
        <polyline points="12 7 17 12 12 17" />
    """,
    "keyframes-filter-out": """
        <line x1="20" y1="4" x2="20" y2="20" />
        <path d="M20 12H6" />
        <polyline points="12 7 7 12 12 17" />
    """,
    "keyframes-simple-in": """
        <polyline points="4 20 20 4" />
        <line x1="4" y1="20" x2="20" y2="20" />
        <line x1="20" y1="20" x2="20" y2="4" />
    """,
    "keyframes-simple-out": """
        <polyline points="4 4 20 20" />
        <line x1="4" y1="20" x2="20" y2="20" />
        <line x1="4" y1="4" x2="4" y2="20" />
    """,
    "4-direction": """
        <polyline points="5 9 2 12 5 15" />
        <polyline points="9 5 12 2 15 5" />
        <polyline points="15 19 12 22 9 19" />
        <polyline points="19 9 22 12 19 15" />
        <line x1="2" y1="12" x2="22" y2="12" />
        <line x1="12" y1="2" x2="12" y2="22" />
    """,
    "speech-to-text": """
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
        <path d="M8 9h8" />
        <path d="M8 13h5" />
    """,
    "text-speak": """
        <polygon points="10 5 6 9 2 9 2 15 6 15 10 19 10 5" />
        <path d="M14 9a4 4 0 0 1 0 6" />
        <path d="M17 6a8 8 0 0 1 0 12" />
    """,
    "font": """
        <polyline points="4 7 4 4 20 4 20 7" />
        <line x1="12" y1="4" x2="12" y2="20" />
        <line x1="9" y1="20" x2="15" y2="20" />
    """,
    "zoom-select": """
        <path d="M3 7V5a2 2 0 0 1 2-2h2" />
        <path d="M17 3h2a2 2 0 0 1 2 2v2" />
        <path d="M21 17v2a2 2 0 0 1-2 2h-2" />
        <path d="M7 21H5a2 2 0 0 1-2-2v-2" />
        <circle cx="12" cy="12" r="3" />
    """,
    "folder": """
        <path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z" />
    """,
    "download": """
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
        <polyline points="7 10 12 15 17 10" />
        <line x1="12" y1="15" x2="12" y2="3" />
    """,
    "fire": """
        <path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z" />
    """,
    "keyframe-linear": """
        <line x1="4" y1="20" x2="20" y2="4" />
        <polygon points="4 17 7 20 4 23 1 20" />
        <polygon points="20 1 23 4 20 7 17 4" />
    """,
}

def create_svg_doc(inner_content: str) -> str:
    cleaned = inner_content.strip()
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="{STROKE_COLOR}" stroke-width="{STROKE_WIDTH}" stroke-linecap="round" stroke-linejoin="round">
  {cleaned}
</svg>"""

def render_svg_to_png(svg_text: str, output_png_path: Path, size: int = 32):
    renderer = QSvgRenderer(QByteArray(svg_text.encode("utf-8")))
    img = QImage(size, size, QImage.Format_ARGB32_Premultiplied)
    img.fill(Qt.transparent)

    painter = QPainter(img)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
    renderer.render(painter)
    painter.end()

    # Save PNG
    saved = img.save(str(output_png_path), "PNG")
    if not saved or output_png_path.stat().st_size == 0:
        raise RuntimeError(f"Failed to save PNG at {output_png_path}")

def update_resources_qrc(svg_names):
    """Ensure all svg files are registered in resources.qrc alongside png files."""
    tree = ET.parse(RESOURCES_QRC)
    root = tree.getroot()
    qresource = root.find("qresource")
    
    existing_files = {f.text.strip() for f in qresource.findall("file") if f.text}
    
    added_count = 0
    for name in sorted(svg_names):
        rel = f"dark/32x32/{name}.svg"
        if rel not in existing_files:
            elem = ET.Element("file")
            elem.text = rel
            qresource.append(elem)
            existing_files.add(rel)
            added_count += 1
            
    # Pretty format QRC
    ET.indent(tree, space="    ", level=0)
    tree.write(RESOURCES_QRC, encoding="utf-8", xml_declaration=False)
    print(f"resources.qrc updated: added {added_count} SVG entries (total files: {len(existing_files)})")

def main():
    print(f"Generating {len(SVG_ICONS)} Lucide-style stroke icons...")
    DARK_ICONS_DIR.mkdir(parents=True, exist_ok=True)
    
    svg_generated = []
    
    for name, content in SVG_ICONS.items():
        svg_text = create_svg_doc(content)
        
        # 1. Save SVG
        svg_path = DARK_ICONS_DIR / f"{name}.svg"
        with open(svg_path, "w", encoding="utf-8") as f:
            f.write(svg_text)
            
        # 2. Render 32x32 PNG
        png_path = DARK_ICONS_DIR / f"{name}.png"
        render_svg_to_png(svg_text, png_path, size=32)
        
        svg_generated.append(name)
        print(f"  [OK] Generated {name}.svg ({svg_path.stat().st_size} B) & {name}.png ({png_path.stat().st_size} B)")
        
    # 3. Update resources.qrc
    update_resources_qrc(svg_generated)
    print(f"\nSuccessfully generated and synchronized {len(svg_generated)} Lucide icons!")

if __name__ == "__main__":
    main()
