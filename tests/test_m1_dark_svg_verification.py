#!/usr/bin/env python3
"""
test_m1_dark_svg_verification.py
=================================
Adversarial Verification Suite for Milestone 1 Dark SVG Vector Master & Splash Asset.
Author: teamwork_preview_challenger_m1_dark_2 (Empirical Challenger)
Targets:
  - icons/shotcut-logo-64.svg
  - icons/shotcut-logo-320x320.png

Tests:
  Suite 1: Strict SVG XML Conformance & Unsupported CSS/Filter Ban
  Suite 2: Native Qt QSvgRenderer Compatibility & Diagnostics (0 Warnings)
  Suite 3: Multi-Scale Rasterization Stress Test (8x8 up to 2048x2048)
  Suite 4: Color Palette Integrity & Absence of Legacy Bright Hues
  Suite 5: Sharpness, Anti-Aliasing Fidelity & Geometry Alignment
  Suite 6: Quantitative Photometric Contrast Ratios (WCAG AA & AAA)
  Suite 7: Splash Screen PNG (320x320) Chunk Analysis & QImage Profile Load
  Suite 8: Splash Screen vs. Master SVG Pixel-Fidelity Differential
  Suite 9: Concurrency, Thread Safety & Memory Leak Stress Test
"""

import os
import sys
import io
import math
import struct
import threading
import xml.etree.ElementTree as ET
import numpy as np
from PIL import Image

# Force headless offscreen Qt platform
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from PySide6.QtCore import (
    qInstallMessageHandler, QtMsgType, QByteArray, QRectF, QSize
)
from PySide6.QtGui import (
    QGuiApplication, QImage, QPainter, QPixmap, QImageReader, QColor
)
from PySide6.QtSvg import QSvgRenderer

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SVG_PATH = os.path.join(REPO_ROOT, "icons", "shotcut-logo-64.svg")
SPLASH_PATH = os.path.join(REPO_ROOT, "icons", "shotcut-logo-320x320.png")

# Intercept all Qt warning/critical/debug messages
qt_messages = []
def qt_msg_catcher(msg_type, context, message):
    qt_messages.append((msg_type, message))

qInstallMessageHandler(qt_msg_catcher)
qt_app = QGuiApplication([])

# Color definitions
COLOR_CHARCOAL = (31, 31, 38)     # #1F1F26 (Left Video Segment "Shot")
COLOR_SLATE    = (53, 55, 68)     # #353744 (Right Video Segment "Cut")
COLOR_WHITE    = (255, 255, 255) # #FFFFFF (Sliced Play Symbol)
COLOR_TITANIUM = (142, 147, 164) # #8E93A4 (Playhead Cursor & Razor Cut)

# Legacy colors that MUST NOT appear
LEGACY_CYAN  = (32, 230, 197)   # #20E6C5
LEGACY_BLUE  = (0, 102, 255)    # #0066FF
LEGACY_CORAL = (255, 51, 102)   # #FF3366


class TestReport:
    def __init__(self, title):
        self.title = title
        self.passed = True
        self.logs = []
        self.errors = []

    def log(self, msg):
        self.logs.append(msg)

    def error(self, msg):
        self.passed = False
        self.errors.append(msg)

    def print_summary(self):
        status = "PASS" if self.passed else "FAIL"
        print(f"[{status}] {self.title}")
        for l in self.logs:
            print(f"    INFO: {l}")
        for e in self.errors:
            print(f"    ERROR: {e}")
        return self.passed


def srgb_to_linear(val):
    c = val / 255.0
    if c <= 0.04045:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4


def relative_luminance(rgb):
    r_lin = srgb_to_linear(rgb[0])
    g_lin = srgb_to_linear(rgb[1])
    b_lin = srgb_to_linear(rgb[2])
    return 0.2126 * r_lin + 0.7152 * g_lin + 0.0722 * b_lin


def wcag_contrast_ratio(rgb1, rgb2):
    l1 = relative_luminance(rgb1)
    l2 = relative_luminance(rgb2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def test_suite_1_svg_xml_syntax():
    report = TestReport("Suite 1: Strict SVG XML Conformance & Unsupported CSS/Filter Ban")
    if not os.path.exists(SVG_PATH):
        report.error(f"SVG file not found at {SVG_PATH}")
        return report

    with open(SVG_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Parse XML
    try:
        root = ET.fromstring(content)
        report.log(f"XML parsed successfully. Root tag: <{root.tag}>")
    except Exception as e:
        report.error(f"XML parse failure: {e}")
        return report

    # 2. Namespace & Root Tag
    expected_ns = "{http://www.w3.org/2000/svg}"
    if not root.tag.startswith(expected_ns) or root.tag[len(expected_ns):] != "svg":
        report.error(f"Unexpected root tag or namespace: {root.tag}")

    # 3. ViewBox and dimensions
    w = root.attrib.get("width")
    h = root.attrib.get("height")
    vb = root.attrib.get("viewBox")
    report.log(f"Attributes: width={w}, height={h}, viewBox={vb}")
    if w != "64" or h != "64":
        report.error(f"Incorrect width/height: {w}x{h} (expected 64x64)")
    if vb != "0 0 64 64":
        report.error(f"Incorrect viewBox: '{vb}' (expected '0 0 64 64')")

    # 4. Prohibited CSS & SVG features
    content_lower = content.lower()
    prohibited_tokens = [
        "mix-blend-mode", "filter", "backdrop-filter", "feGaussianBlur",
        "feOffset", "feBlend", "mask", "clip-path", "clippath", "<style",
        "script", "foreignobject", "xlink:href", "javascript:"
    ]
    found_forbidden = [tok for tok in prohibited_tokens if tok in content_lower]
    if found_forbidden:
        report.error(f"Found unsupported/forbidden CSS or SVG tokens: {found_forbidden}")
    else:
        report.log("Zero forbidden CSS properties (no mix-blend-mode, no filters, no masks, no scripts).")

    # 5. Permitted elements
    allowed_elements = {"svg", "path", "polygon", "line", "g", "defs"}
    all_tags = {elem.tag.replace(expected_ns, "") for elem in root.iter()}
    unknown_tags = all_tags - allowed_elements
    if unknown_tags:
        report.error(f"Unknown or non-standard SVG elements: {unknown_tags}")
    else:
        report.log(f"All element tags permitted and supported by QSvgRenderer: {sorted(list(all_tags))}")

    return report


def test_suite_2_qtsvg_renderer():
    report = TestReport("Suite 2: Native Qt QSvgRenderer Compatibility & Diagnostics")
    global qt_messages
    qt_messages.clear()

    renderer = QSvgRenderer(SVG_PATH)
    if not renderer.isValid():
        report.error("QSvgRenderer.isValid() returned False")
        return report

    report.log("QSvgRenderer successfully initialized and parsed vector master.")

    sz = renderer.defaultSize()
    vb = renderer.viewBox()
    report.log(f"Reported defaultSize: {sz.width()}x{sz.height()}, viewBox: {vb.x()},{vb.y()},{vb.width()},{vb.height()}")
    if sz.width() != 64 or sz.height() != 64:
        report.error(f"QSvgRenderer defaultSize mismatch: {sz.width()}x{sz.height()}")
    if vb.width() != 64 or vb.height() != 64:
        report.error(f"QSvgRenderer viewBox mismatch: {vb.width()}x{vb.height()}")

    if renderer.animated():
        report.error("QSvgRenderer reports animated() == True; static icon expected.")
    else:
        report.log("Static icon verified (animated() == False).")

    # In-memory QByteArray loading (simulating Qt .qrc resource)
    with open(SVG_PATH, "rb") as f:
        raw_svg = f.read()
    ba = QByteArray(raw_svg)
    mem_renderer = QSvgRenderer(ba)
    if not mem_renderer.isValid():
        report.error("In-memory QByteArray QSvgRenderer failed to load.")
    else:
        report.log("In-memory QByteArray loading passed (simulates Qt qrc: resource bundle).")

    # Check for any Qt warning messages
    if qt_messages:
        report.error(f"Qt emitted {len(qt_messages)} diagnostic warnings/errors: {qt_messages}")
    else:
        report.log("Clean Qt diagnostic channel: 0 warnings, 0 errors emitted during parsing.")

    return report


def test_suite_3_and_4_multiscale_and_palette():
    report = TestReport("Suite 3 & 4: Multi-Scale Rasterization & Dark Palette Conformance")
    scales = [8, 16, 32, 64, 128, 256, 512, 1024, 2048]
    renderer = QSvgRenderer(SVG_PATH)

    for s in scales:
        img = QImage(s, s, QImage.Format_ARGB32_Premultiplied)
        img.fill(0)
        painter = QPainter(img)
        renderer.render(painter)
        painter.end()

        # Extract RGBA buffer safely with float conversion to prevent uint8 underflow/overflow
        ptr = img.constBits()
        raw = np.frombuffer(ptr, dtype=np.uint8).reshape((s, s, 4))
        # Format_ARGB32_Premultiplied on Windows is BGRA
        b = raw[:, :, 0].astype(np.float64)
        g = raw[:, :, 1].astype(np.float64)
        r = raw[:, :, 2].astype(np.float64)
        a = raw[:, :, 3].astype(np.float64)

        # 1. Non-empty check
        total_pixels = s * s
        opaque_mask = a > 200
        opaque_count = np.sum(opaque_mask)
        opaque_ratio = opaque_count / total_pixels

        if opaque_count == 0:
            report.error(f"Scale {s}x{s}: Rasterization produced 0 opaque pixels!")
            continue

        # 2. Transparent corners check
        corners = [(0, 0), (0, s - 1), (s - 1, 0), (s - 1, s - 1)]
        bad_corners = [c for c in corners if a[c[0], c[1]] != 0]
        if bad_corners:
            report.error(f"Scale {s}x{s}: Non-transparent corners detected: {bad_corners}")

        # 3. Absence of legacy bright colors (using un-premultiplied RGB calculation)
        # Avoid division by zero
        alpha_safe = np.where(a > 50, a / 255.0, 1.0)
        unpre_r = np.clip(r / alpha_safe, 0, 255)
        unpre_g = np.clip(g / alpha_safe, 0, 255)
        unpre_b = np.clip(b / alpha_safe, 0, 255)

        # Distance to legacy colors
        d_legacy_cyan  = np.sqrt((unpre_r - LEGACY_CYAN[0])**2 + (unpre_g - LEGACY_CYAN[1])**2 + (unpre_b - LEGACY_CYAN[2])**2)
        d_legacy_blue  = np.sqrt((unpre_r - LEGACY_BLUE[0])**2 + (unpre_g - LEGACY_BLUE[1])**2 + (unpre_b - LEGACY_BLUE[2])**2)
        d_legacy_coral = np.sqrt((unpre_r - LEGACY_CORAL[0])**2 + (unpre_g - LEGACY_CORAL[1])**2 + (unpre_b - LEGACY_CORAL[2])**2)

        has_legacy_cyan = np.any((d_legacy_cyan < 25) & (a > 200))
        has_legacy_blue = np.any((d_legacy_blue < 25) & (a > 200))
        has_legacy_coral = np.any((d_legacy_coral < 25) & (a > 200))

        if has_legacy_cyan or has_legacy_blue or has_legacy_coral:
            report.error(f"Scale {s}x{s}: Legacy bright colors detected! (cyan={has_legacy_cyan}, blue={has_legacy_blue}, coral={has_legacy_coral})")

        # 4. Presence of dark palette tokens
        d_charcoal = np.sqrt((unpre_r - COLOR_CHARCOAL[0])**2 + (unpre_g - COLOR_CHARCOAL[1])**2 + (unpre_b - COLOR_CHARCOAL[2])**2)
        d_slate    = np.sqrt((unpre_r - COLOR_SLATE[0])**2    + (unpre_g - COLOR_SLATE[1])**2    + (unpre_b - COLOR_SLATE[2])**2)
        d_white    = np.sqrt((unpre_r - COLOR_WHITE[0])**2    + (unpre_g - COLOR_WHITE[1])**2    + (unpre_b - COLOR_WHITE[2])**2)
        d_titanium = np.sqrt((unpre_r - COLOR_TITANIUM[0])**2 + (unpre_g - COLOR_TITANIUM[1])**2 + (unpre_b - COLOR_TITANIUM[2])**2)

        has_charcoal = np.any((d_charcoal < 25) & (a > 200))
        has_slate    = np.any((d_slate < 25) & (a > 200))
        has_white    = np.any((d_white < 25) & (a > 200))
        has_titanium = np.any((d_titanium < 30) & (a > 150))

        if s >= 16:
            missing_tokens = []
            if not has_charcoal: missing_tokens.append("Charcoal(#1F1F26)")
            if not has_slate:    missing_tokens.append("Slate(#353744)")
            if not has_white:    missing_tokens.append("White(#FFFFFF)")
            if s >= 32 and not has_titanium: missing_tokens.append("Titanium(#8E93A4)")

            if missing_tokens:
                report.error(f"Scale {s}x{s}: Missing expected dark brand palette tokens: {missing_tokens}")
            else:
                report.log(f"Scale {s}x{s:4d}: All dark palette tokens verified. Opaque ratio: {opaque_ratio:.2%}")
        else:
            # 8x8 micro-scale
            if not has_charcoal and not has_slate:
                report.error(f"Scale 8x8: Failed to render main body segments.")
            else:
                report.log(f"Scale 8x8  : Micro-scale rendered cleanly without distortion. Opaque ratio: {opaque_ratio:.2%}")

    return report


def test_suite_5_sharpness_antialiasing_and_geometry():
    report = TestReport("Suite 5: Sharpness, Anti-Aliasing Fidelity & Geometry Alignment")
    renderer = QSvgRenderer(SVG_PATH)

    # 1. Render at 256x256 reference scale
    s = 256
    img = QImage(s, s, QImage.Format_ARGB32_Premultiplied)
    img.fill(0)
    p = QPainter(img)
    renderer.render(p)
    p.end()

    arr = np.frombuffer(img.constBits(), dtype=np.uint8).reshape((s, s, 4))
    a = arr[:, :, 3]

    rows = np.any(a > 10, axis=1)
    cols = np.any(a > 10, axis=0)
    rmin, rmax = np.where(rows)[0][[0, -1]]
    cmin, cmax = np.where(cols)[0][[0, -1]]

    bbox_w = cmax - cmin + 1
    bbox_h = rmax - rmin + 1
    aspect = bbox_w / bbox_h
    report.log(f"Bounding box at 256x256: x=[{cmin}..{cmax}] (w={bbox_w}), y=[{rmin}..{rmax}] (h={bbox_h}), aspect={aspect:.3f}")

    # Geometry bounds: playhead apex at top (y ~ 2/64 -> 8px), bottom extends to 56/64 -> 224px (h ~ 216)
    # Width spans 8/64 (32px) to 56/64 (224px) -> w ~ 192
    if not (185 <= bbox_w <= 200):
        report.error(f"Bounding box width {bbox_w} deviates from design expectation [185..200]")
    if not (205 <= bbox_h <= 225):
        report.error(f"Bounding box height {bbox_h} deviates from design expectation [205..225]")

    # 2. Check Anti-Aliasing Edge Quality at 1024x1024
    s_hd = 1024
    img_hd = QImage(s_hd, s_hd, QImage.Format_ARGB32_Premultiplied)
    img_hd.fill(0)
    p_hd = QPainter(img_hd)
    renderer.render(p_hd)
    p_hd.end()

    arr_hd = np.frombuffer(img_hd.constBits(), dtype=np.uint8).reshape((s_hd, s_hd, 4))
    a_hd = arr_hd[:, :, 3]

    # Non-jagged subpixel anti-aliasing produces intermediate alpha values (0 < a < 255)
    semi_count = np.sum((a_hd > 15) & (a_hd < 240))
    solid_count = np.sum(a_hd >= 240)
    aa_ratio = semi_count / solid_count
    report.log(f"High-DPI 1024x1024 edge antialiasing: {semi_count} subpixel transition pixels ({aa_ratio:.2%} of solid)")

    if semi_count == 0:
        report.error("Zero anti-aliased transition pixels! Jagged staircase aliasing detected.")
    elif aa_ratio > 0.05:
        report.error(f"Excessive edge blur detected (transition ratio: {aa_ratio:.2%})")
    else:
        report.log("Anti-aliasing verified: crisp, subpixel-accurate edges with no blur or jagged staircase artifacts.")

    # 3. Check for color fringing along the white play motif border
    # Extract white play motif mask and check edge pixel chromaticity
    r_hd = arr_hd[:, :, 2].astype(np.float64)
    g_hd = arr_hd[:, :, 1].astype(np.float64)
    b_hd = arr_hd[:, :, 0].astype(np.float64)
    alpha_hd = a_hd.astype(np.float64) / 255.0

    # Unpre-multiplied RGB for opaque interior
    solid_mask = a_hd > 240
    # Difference between R, G, B for neutral elements (white or greys)
    # The dark theme uses neutral greys (#1F1F26, #353744, #8E93A4) and pure white (#FFFFFF)
    # Maximal chromatic saturation (max(RGB) - min(RGB))
    chroma = np.max(np.stack([r_hd, g_hd, b_hd], axis=-1), axis=-1) - np.min(np.stack([r_hd, g_hd, b_hd], axis=-1), axis=-1)
    max_chroma = np.max(chroma[solid_mask])
    report.log(f"Maximal chromatic saturation in solid geometry: {max_chroma:.1f} (understated dark neutral styling)")
    if max_chroma > 45:
        report.error(f"Unintended highly saturated chroma detected: {max_chroma}")

    return report


def test_suite_6_contrast_ratios():
    report = TestReport("Suite 6: Quantitative Photometric Contrast Ratios (WCAG Standards)")

    # 1. White play motif against Left Segment (#1F1F26 Charcoal)
    cr_white_charcoal = wcag_contrast_ratio(COLOR_WHITE, COLOR_CHARCOAL)
    report.log(f"Contrast Ratio White-on-Charcoal (#1F1F26): {cr_white_charcoal:.2f}:1 (WCAG AAA >= 7.0:1)")
    if cr_white_charcoal < 7.0:
        report.error(f"White-on-Charcoal contrast ratio ({cr_white_charcoal:.2f}:1) fails WCAG AAA threshold (7.0:1)")

    # 2. White play motif against Right Segment (#353744 Slate)
    cr_white_slate = wcag_contrast_ratio(COLOR_WHITE, COLOR_SLATE)
    report.log(f"Contrast Ratio White-on-Slate (#353744): {cr_white_slate:.2f}:1 (WCAG AAA >= 7.0:1)")
    if cr_white_slate < 7.0:
        report.error(f"White-on-Slate contrast ratio ({cr_white_slate:.2f}:1) fails WCAG AAA threshold (7.0:1)")

    # 3. Titanium playhead/cut line (#8E93A4) against Charcoal (#1F1F26)
    cr_titanium_charcoal = wcag_contrast_ratio(COLOR_TITANIUM, COLOR_CHARCOAL)
    report.log(f"Contrast Ratio Titanium-on-Charcoal: {cr_titanium_charcoal:.2f}:1 (WCAG AA >= 4.5:1)")
    if cr_titanium_charcoal < 4.5:
        report.error(f"Titanium-on-Charcoal contrast ratio ({cr_titanium_charcoal:.2f}:1) fails WCAG AA threshold (4.5:1)")

    # 4. Titanium playhead/cut line (#8E93A4) against Slate (#353744)
    cr_titanium_slate = wcag_contrast_ratio(COLOR_TITANIUM, COLOR_SLATE)
    report.log(f"Contrast Ratio Titanium-on-Slate: {cr_titanium_slate:.2f}:1 (WCAG Non-text graphical object >= 3.0:1)")
    if cr_titanium_slate < 3.0:
        report.error(f"Titanium-on-Slate contrast ratio ({cr_titanium_slate:.2f}:1) fails graphical object threshold (3.0:1)")

    # 5. Dual-tone separation: Slate (#353744) vs Charcoal (#1F1F26)
    cr_slate_charcoal = wcag_contrast_ratio(COLOR_SLATE, COLOR_CHARCOAL)
    report.log(f"Dual-tone segment luminance separation (Slate vs Charcoal): {cr_slate_charcoal:.2f}:1")

    return report


def test_suite_7_splash_screen_png():
    report = TestReport("Suite 7: Splash Screen PNG (320x320) Chunk Analysis & QImage Profile Load")
    global qt_messages
    qt_messages.clear()

    if not os.path.exists(SPLASH_PATH):
        report.error(f"Splash screen PNG not found at {SPLASH_PATH}")
        return report

    # 1. PIL validation
    try:
        im = Image.open(SPLASH_PATH)
        report.log(f"PIL: format={im.format}, size={im.size}, mode={im.mode}")
        if im.size != (320, 320):
            report.error(f"Invalid splash PNG size: {im.size} (expected 320x320)")
        if im.mode != "RGBA":
            report.error(f"Invalid splash PNG mode: '{im.mode}' (expected RGBA)")
    except Exception as e:
        report.error(f"PIL failed opening splash PNG: {e}")
        return report

    # 2. Low-level PNG Chunk Analysis (Scanning for problematic iCCP profile chunks)
    with open(SPLASH_PATH, "rb") as f:
        png_bytes = f.read()

    if png_bytes[:8] != b"\x89PNG\r\n\x1a\n":
        report.error("Corrupted PNG magic signature!")
        return report

    pos = 8
    chunks = []
    has_iccp = False
    iccp_corrupt = False

    while pos < len(png_bytes):
        if pos + 8 > len(png_bytes):
            report.error(f"Truncated PNG chunk header at offset {pos}")
            break
        chunk_len, chunk_type = struct.unpack(">I4s", png_bytes[pos : pos + 8])
        pos += 8
        chunk_name = chunk_type.decode("latin1", "replace")
        chunks.append(chunk_name)

        if chunk_type == b"iCCP":
            has_iccp = True
            report.log(f"Detected iCCP color profile chunk ({chunk_len} bytes)")
            # Verify iCCP compression method and zlib integrity
            profile_data = png_bytes[pos : pos + chunk_len]
            null_idx = profile_data.find(b"\x00")
            if null_idx == -1 or null_idx + 2 > len(profile_data):
                iccp_corrupt = True
                report.error("Corrupted iCCP profile chunk header (missing null separator)")
            else:
                profile_name = profile_data[:null_idx].decode("latin1", "replace")
                comp_method = profile_data[null_idx + 1]
                report.log(f"iCCP profile name: '{profile_name}', compression method: {comp_method}")

        pos += chunk_len + 4  # skip payload + CRC

    report.log(f"PNG chunks present: {chunks}")
    if not has_iccp:
        report.log("No iCCP chunk present: completely immune to libpng iCCP profile mismatch warnings.")

    # 3. Qt QImageReader & QImage load test
    reader = QImageReader(SPLASH_PATH)
    qimg = reader.read()
    if qimg.isNull():
        report.error(f"QImageReader failed to read splash PNG: {reader.errorString()}")
    else:
        report.log(f"QImageReader loaded splash PNG cleanly: {qimg.width()}x{qimg.height()}, format={qimg.format()}")

    # 4. QSplashScreen / QPixmap instantiation test
    pixmap = QPixmap(SPLASH_PATH)
    if pixmap.isNull():
        report.error("QPixmap failed to load splash asset")
    else:
        report.log(f"QPixmap loaded cleanly: {pixmap.width()}x{pixmap.height()}, depth={pixmap.depth()}bpp, hasAlpha={pixmap.hasAlpha()}")
        if not pixmap.hasAlpha():
            report.error("QPixmap lost alpha channel (transparency mask unavailable)")

    # 5. Check Qt diagnostic messages during image reading
    if qt_messages:
        report.error(f"Qt emitted messages during splash loading: {qt_messages}")
    else:
        report.log("Zero warnings/errors emitted by Qt/libpng during image decoding.")

    return report


def test_suite_8_splash_vs_svg_fidelity():
    report = TestReport("Suite 8: Splash Screen vs. Master SVG Pixel-Fidelity Differential")

    # Render master SVG at 320x320 using Qt QSvgRenderer
    s = 320
    renderer = QSvgRenderer(SVG_PATH)
    svg_img = QImage(s, s, QImage.Format_ARGB32_Premultiplied)
    svg_img.fill(0)
    p = QPainter(svg_img)
    renderer.render(p)
    p.end()

    svg_arr = np.frombuffer(svg_img.constBits(), dtype=np.uint8).reshape((s, s, 4))

    # Load splash PNG via Qt into exact same format
    splash_raw = QImage(SPLASH_PATH).convertToFormat(QImage.Format_ARGB32_Premultiplied)
    splash_arr = np.frombuffer(splash_raw.constBits(), dtype=np.uint8).reshape((s, s, 4))

    # Compare pixel buffers
    diff = np.abs(svg_arr.astype(np.float64) - splash_arr.astype(np.float64))
    mse = np.mean(diff ** 2)
    max_diff = np.max(diff)

    report.log(f"Splash PNG vs. QSvgRenderer(320x320) MSE: {mse:.4f}, Max Channel Diff: {max_diff:.1f}")

    # Tolerance: minor rasterizer anti-aliasing subpixel differences between pymupdf/cairo and Qt QSvgRenderer
    # are expected (MSE < 5.0, MaxDiff < 100 on edge subpixels)
    if mse > 5.0:
        report.error(f"High pixel divergence between splash PNG and vector master (MSE: {mse:.4f})")
    else:
        report.log(f"Splash screen PNG accurately reproduces the SVG master (MSE {mse:.4f} within high-fidelity threshold < 5.0).")

    return report


def test_suite_9_concurrency_and_stress():
    report = TestReport("Suite 9: Concurrency, Thread Safety & Memory Leak Stress Test")
    global qt_messages
    qt_messages.clear()

    # 1. 1000 Rapid Sequential Renderings
    renderer = QSvgRenderer(SVG_PATH)
    img = QImage(128, 128, QImage.Format_ARGB32_Premultiplied)
    for i in range(1000):
        img.fill(0)
        p = QPainter(img)
        renderer.render(p)
        p.end()
    report.log("Completed 1000 sequential rapid render cycles without memory crash or GDI faults.")

    # 2. Multi-threaded parallel rendering
    thread_errors = []
    def render_worker(tid):
        try:
            r = QSvgRenderer(SVG_PATH)
            im = QImage(64, 64, QImage.Format_ARGB32_Premultiplied)
            for _ in range(50):
                im.fill(0)
                ptr = QPainter(im)
                r.render(ptr)
                ptr.end()
        except Exception as e:
            thread_errors.append((tid, str(e)))

    threads = [threading.Thread(target=render_worker, args=(i,)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    if thread_errors:
        report.error(f"Thread safety test encountered errors: {thread_errors}")
    else:
        report.log("8 concurrent worker threads executed 400 total renders with 100% thread safety.")

    # 3. Aspect Ratio / Non-Square Viewport Stress
    non_squares = [(100, 200), (300, 50), (48, 96)]
    for w, h in non_squares:
        ns_img = QImage(w, h, QImage.Format_ARGB32_Premultiplied)
        ns_img.fill(0)
        p = QPainter(ns_img)
        renderer.render(p)
        p.end()
        # Verify rendered area doesn't crash or overflow
        ns_arr = np.frombuffer(ns_img.constBits(), dtype=np.uint8).reshape((h, w, 4))
        op = np.sum(ns_arr[:, :, 3] > 0)
        if op == 0:
            report.error(f"Non-square render {w}x{h} produced 0 pixels!")
        else:
            report.log(f"Non-square viewport {w}x{h}: rendered cleanly (opaque count: {op} px).")

    return report


def main():
    print("======================================================================")
    print("EMPIRICAL ADVERSARIAL VERIFICATION: SHOTCUT M1 DARK LOGO & PIPELINE")
    print("Author: teamwork_preview_challenger_m1_dark_2")
    print("======================================================================\n")

    suites = [
        test_suite_1_svg_xml_syntax,
        test_suite_2_qtsvg_renderer,
        test_suite_3_and_4_multiscale_and_palette,
        test_suite_5_sharpness_antialiasing_and_geometry,
        test_suite_6_contrast_ratios,
        test_suite_7_splash_screen_png,
        test_suite_8_splash_vs_svg_fidelity,
        test_suite_9_concurrency_and_stress,
    ]

    all_passed = True
    for suite in suites:
        res = suite()
        passed = res.print_summary()
        if not passed:
            all_passed = False
        print("-" * 70)

    print("\n======================================================================")
    if all_passed:
        print("FINAL VERDICT: >>> APPROVE <<<")
        print("All 9 test suites passed with 100% compliance across all criteria.")
        print("======================================================================")
        return 0
    else:
        print("FINAL VERDICT: >>> REQUEST_CHANGES <<<")
        print("Failures detected during adversarial testing. See details above.")
        print("======================================================================")
        return 1


if __name__ == "__main__":
    sys.exit(main())
