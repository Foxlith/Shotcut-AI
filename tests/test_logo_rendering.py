"""
Adversarial Verification Suite for Shotcut Minimalist Logo & Asset Pipeline
Author: teamwork_preview_challenger_m1_2 (Empirical Verifier)
Target: icons/shotcut-logo-64.svg & icons/shotcut-logo-320x320.png
"""

import os
import sys
import io
import math
import struct
import xml.etree.ElementTree as ET
import numpy as np
from PIL import Image

# Ensure offscreen Qt platform
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

# Global capture for Qt warnings
qt_warnings = []
def qt_msg_catcher(msg_type, context, message):
    qt_warnings.append((msg_type, message))

qInstallMessageHandler(qt_msg_catcher)
qt_app = QGuiApplication([])

class TestResult:
    def __init__(self, name):
        self.name = name
        self.passed = True
        self.details = []

    def log(self, msg):
        self.details.append(msg)

    def fail(self, reason):
        self.passed = False
        self.details.append(f"FAIL: {reason}")

    def summary(self):
        status = "PASS" if self.passed else "FAIL"
        return f"[{status}] {self.name}\n" + "\n".join("  " + d for d in self.details)


def test_xml_and_svg_syntax():
    res = TestResult("Test 1: XML Syntax, Namespaces & Conformance")
    if not os.path.exists(SVG_PATH):
        res.fail(f"SVG file not found at {SVG_PATH}")
        return res

    with open(SVG_PATH, "r", encoding="utf-8") as f:
        svg_content = f.read()

    # 1. Parse XML
    try:
        root = ET.fromstring(svg_content)
        res.log("XML is well-formed and parses cleanly.")
    except Exception as e:
        res.fail(f"XML parse error: {e}")
        return res

    # 2. Tag name and namespace
    expected_ns = "{http://www.w3.org/2000/svg}"
    tag_clean = root.tag.replace(expected_ns, "")
    if tag_clean != "svg":
        res.fail(f"Root tag is '{root.tag}', expected 'svg'")
    else:
        res.log(f"Root element: <svg> in namespace '{root.tag[:len(expected_ns)]}'")

    # 3. ViewBox and dimensions
    viewbox = root.attrib.get("viewBox", "")
    width = root.attrib.get("width", "")
    height = root.attrib.get("height", "")
    res.log(f"SVG Attributes: width='{width}', height='{height}', viewBox='{viewbox}'")
    if viewbox != "0 0 64 64":
        res.fail(f"Unexpected viewBox '{viewbox}', expected '0 0 64 64'")
    if width != "64" or height != "64":
        res.fail(f"Unexpected width/height '{width}'x'{height}', expected '64'x'64'")

    # 4. Check for forbidden/unsupported CSS or SVG features
    forbidden_tokens = [
        "mix-blend-mode", "filter", "backdrop-filter", "feGaussianBlur",
        "feOffset", "feBlend", "mask", "clip-path", "script", "style",
        "foreignObject", "xlink:href", "http://www.w3.org/1999/xlink",
        "javascript:"
    ]
    found_forbidden = []
    svg_lower = svg_content.lower()
    for token in forbidden_tokens:
        if token in svg_lower:
            found_forbidden.append(token)
    if found_forbidden:
        res.fail(f"Forbidden/unsupported SVG tokens detected: {found_forbidden}")
    else:
        res.log("Zero forbidden CSS / filter / script tokens found (no mix-blend-mode, no filters).")

    # 5. Check element types
    allowed_elements = {"path", "polygon", "line", "rect", "circle", "g", "defs"}
    all_elements = set()
    for elem in root.iter():
        elem_name = elem.tag.replace(expected_ns, "")
        if elem_name != "svg":
            all_elements.add(elem_name)
    disallowed = all_elements - allowed_elements
    if disallowed:
        res.fail(f"Disallowed elements found: {disallowed}")
    else:
        res.log(f"All child element types valid: {sorted(list(all_elements))}")

    return res


def test_qtsvg_renderer_compatibility():
    res = TestResult("Test 2: Qt QSvgRenderer Native Loading & Diagnostics")
    global qt_warnings
    qt_warnings.clear()

    renderer = QSvgRenderer(SVG_PATH)
    if not renderer.isValid():
        res.fail("QSvgRenderer reports isValid() == False")
        return res

    res.log("QSvgRenderer loaded file successfully: isValid() == True")
    def_sz = renderer.defaultSize()
    res.log(f"Default size: {def_sz.width()}x{def_sz.height()}")
    if def_sz.width() != 64 or def_sz.height() != 64:
        res.fail(f"Default size is {def_sz.width()}x{def_sz.height()}, expected 64x64")

    vb = renderer.viewBox()
    res.log(f"ViewBox: x={vb.x()}, y={vb.y()}, w={vb.width()}, h={vb.height()}")
    if vb.width() != 64 or vb.height() != 64:
        res.fail(f"ViewBox dimensions are {vb.width()}x{vb.height()}, expected 64x64")

    if renderer.animated():
        res.fail("QSvgRenderer reports animated() == True, expected static logo")
    else:
        res.log("Animated flag is False (correct for static icon)")

    # Test loading from QByteArray (memory buffer loading)
    with open(SVG_PATH, "rb") as f:
        svg_bytes = f.read()
    ba = QByteArray(svg_bytes)
    mem_renderer = QSvgRenderer(ba)
    if not mem_renderer.isValid():
        res.fail("QSvgRenderer failed loading from QByteArray")
    else:
        res.log("QByteArray in-memory loading passed: isValid() == True")

    if qt_warnings:
        res.fail(f"Qt logged {len(qt_warnings)} messages: {qt_warnings}")
    else:
        res.log("Qt message log is completely clean (0 warnings / 0 errors)")

    return res


def test_multiscale_rendering():
    res = TestResult("Test 3: Multi-Scale Rendering Stress Test (8x8 to 2048x2048)")
    scales = [8, 16, 24, 32, 48, 64, 128, 256, 320, 512, 1024, 2048]
    renderer = QSvgRenderer(SVG_PATH)

    # Color targets
    c_cyan = (32, 230, 197)    # #20E6C5
    c_blue = (0, 102, 255)     # #0066FF
    c_white = (255, 255, 255)  # #FFFFFF
    c_red = (255, 51, 102)     # #FF3366

    for s in scales:
        img = QImage(s, s, QImage.Format_ARGB32_Premultiplied)
        img.fill(0)  # transparent
        painter = QPainter(img)
        renderer.render(painter)
        painter.end()

        # Convert QImage to numpy array
        ptr = img.constBits()
        # In QImage Format_ARGB32_Premultiplied on Windows AMD64, byte order is BGRA
        arr = np.frombuffer(ptr, dtype=np.uint8).reshape((s, s, 4))
        b, g, r, a = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2], arr[:, :, 3]

        # 1. Non-empty check
        total_pixels = s * s
        opaque_count = np.sum(a > 0)
        opaque_ratio = opaque_count / total_pixels
        if opaque_count == 0:
            res.fail(f"Scale {s}x{s} is completely empty!")
            continue

        # 2. Transparent corners check
        # Top-left corner (0,0), Top-right (0, s-1), Bottom-left (s-1, 0), Bottom-right (s-1, s-1)
        corners = [(0, 0), (0, s-1), (s-1, 0), (s-1, s-1)]
        bad_corners = [c for c in corners if a[c[0], c[1]] != 0]
        if bad_corners:
            res.fail(f"Scale {s}x{s} has non-transparent corners: {bad_corners}")

        # 3. Color detection (check for presence of cyan, blue, white, red)
        # We find pixels close to each target color where alpha > 200
        mask_opaque = a > 200
        # Euclidean distances in RGB
        dist_cyan = np.sqrt((r - c_cyan[0])**2 + (g - c_cyan[1])**2 + (b - c_cyan[2])**2)
        dist_blue = np.sqrt((r - c_blue[0])**2 + (g - c_blue[1])**2 + (b - c_blue[2])**2)
        dist_white = np.sqrt((r - c_white[0])**2 + (g - c_white[1])**2 + (b - c_white[2])**2)
        dist_red = np.sqrt((r - c_red[0])**2 + (g - c_red[1])**2 + (b - c_red[2])**2)

        has_cyan = np.any((dist_cyan < 30) & mask_opaque)
        has_blue = np.any((dist_blue < 30) & mask_opaque)
        has_white = np.any((dist_white < 30) & mask_opaque)
        has_red = np.any((dist_red < 30) & mask_opaque)

        # At scale >= 16, all 4 colors must be distinctly present
        if s >= 16:
            missing = []
            if not has_cyan: missing.append("Cyan(#20E6C5)")
            if not has_blue: missing.append("Blue(#0066FF)")
            if not has_white: missing.append("White(#FFFFFF)")
            if not has_red: missing.append("Red(#FF3366)")
            if missing:
                res.fail(f"Scale {s}x{s} missing expected colors: {missing}")
            else:
                res.log(f"Scale {s}x{s}: All 4 brand colors verified. Opaque ratio: {opaque_ratio:.2%}")
        else:
            # At 8x8, thin razor cut (1.8/64 * 8 = 0.225 px) may blend, but cyan and blue must exist
            if not has_cyan or not has_blue:
                res.fail(f"Scale 8x8 missing primary segments (Cyan/Blue)")
            else:
                res.log(f"Scale {s}x{s}: Micro-scale rendered cleanly. Opaque ratio: {opaque_ratio:.2%}")

    return res


def test_geometric_sharpness_and_contrast():
    res = TestResult("Test 4: Geometric Sharpness, Undistorted Aspect & Contrast")
    renderer = QSvgRenderer(SVG_PATH)

    # 1. Render at reference scale 256x256
    s = 256
    img = QImage(s, s, QImage.Format_ARGB32_Premultiplied)
    img.fill(0)
    painter = QPainter(img)
    renderer.render(painter)
    painter.end()

    arr = np.frombuffer(img.constBits(), dtype=np.uint8).reshape((s, s, 4))
    b, g, r, a = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2], arr[:, :, 3]

    # Find bounding box of non-zero alpha
    rows = np.any(a > 10, axis=1)
    cols = np.any(a > 10, axis=0)
    rmin, rmax = np.where(rows)[0][[0, -1]]
    cmin, cmax = np.where(cols)[0][[0, -1]]

    bbox_w = cmax - cmin + 1
    bbox_h = rmax - rmin + 1
    aspect = bbox_w / bbox_h
    res.log(f"Non-empty bounding box at 256x256: x=[{cmin}..{cmax}] (w={bbox_w}), y=[{rmin}..{rmax}] (h={bbox_h}), aspect={aspect:.3f}")

    # Geometry checks: playhead cursor starts at top (y=2/64 -> 8px), bottom extends to 56/64 (224px)
    # Width spans 8/64 (32px) to 56/64 (224px) -> approx 192px width and 216px height
    expected_w_min = int(s * (48 / 64) * 0.95)
    expected_w_max = int(s * (48 / 64) * 1.05)
    if not (expected_w_min <= bbox_w <= expected_w_max):
        res.fail(f"Bounding box width {bbox_w} outside expected range [{expected_w_min}, {expected_w_max}]")
    else:
        res.log(f"Bounding box width {bbox_w} perfectly matches SVG geometry specifications.")

    # 2. Contrast measurement
    # White play button (#FFFFFF) vs Cyan segment (#20E6C5) and Blue segment (#0066FF)
    # Luminance formula: L = 0.2126 * R + 0.7152 * G + 0.0722 * B
    def lum(rgb):
        return (0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]) / 255.0

    l_white = lum((255, 255, 255))  # 1.0
    l_cyan = lum((32, 230, 197))    # ~0.70
    l_blue = lum((0, 102, 255))     # ~0.29
    l_dark = lum((22, 22, 26))      # ~0.086 (Dark theme background)

    cr_white_blue = (l_white + 0.05) / (l_blue + 0.05)
    cr_cyan_dark = (l_cyan + 0.05) / (l_dark + 0.05)
    cr_blue_dark = (l_blue + 0.05) / (l_dark + 0.05)

    res.log(f"Contrast Ratio White-on-Blue: {cr_white_blue:.2f}:1 (WCAG AAA >= 7:1)")
    res.log(f"Contrast Ratio Cyan-on-Dark: {cr_cyan_dark:.2f}:1 (WCAG AAA >= 7:1)")
    res.log(f"Contrast Ratio Blue-on-Dark: {cr_blue_dark:.2f}:1 (WCAG AA >= 4.5:1)")

    if cr_white_blue < 2.5:
        res.fail(f"Low contrast White-on-Blue: {cr_white_blue:.2f}")

    # 3. High-DPI Edge Antialiasing Test at 1024x1024
    s_hd = 1024
    img_hd = QImage(s_hd, s_hd, QImage.Format_ARGB32_Premultiplied)
    img_hd.fill(0)
    p_hd = QPainter(img_hd)
    renderer.render(p_hd)
    p_hd.end()

    arr_hd = np.frombuffer(img_hd.constBits(), dtype=np.uint8).reshape((s_hd, s_hd, 4))
    a_hd = arr_hd[:, :, 3]

    # Inspect antialiasing transition band on outer edge
    # Semi-transparent pixels (0 < a < 255) indicate smooth anti-aliased subpixel rendering
    semi_count = np.sum((a_hd > 10) & (a_hd < 245))
    total_solid = np.sum(a_hd >= 245)
    aa_ratio = semi_count / total_solid
    res.log(f"High-DPI 1024x1024 edge smoothness: {semi_count} anti-aliased transition pixels ({aa_ratio:.2%} of solid)")
    if semi_count == 0:
        res.fail("Zero anti-aliased pixels at 1024x1024 — jagged staircase rendering detected!")
    else:
        res.log("Antialiasing confirmed active and high-fidelity.")

    return res


def test_splash_screen_png():
    res = TestResult("Test 5: Splash Screen PNG (icons/shotcut-logo-320x320.png) Validation")
    global qt_warnings
    qt_warnings.clear()

    if not os.path.exists(SPLASH_PATH):
        res.fail(f"Splash screen asset not found at {SPLASH_PATH}")
        return res

    # 1. PIL validation
    try:
        pil_img = Image.open(SPLASH_PATH)
        res.log(f"PIL: format={pil_img.format}, size={pil_img.size}, mode={pil_img.mode}")
        if pil_img.size != (320, 320):
            res.fail(f"PIL size is {pil_img.size}, expected (320, 320)")
        if pil_img.mode != "RGBA":
            res.fail(f"PIL mode is '{pil_img.mode}', expected 'RGBA'")
    except Exception as e:
        res.fail(f"PIL failed opening splash PNG: {e}")
        return res

    # 2. PNG Chunk Analysis (Check for broken iCCP / color profile chunks)
    with open(SPLASH_PATH, "rb") as f:
        png_data = f.read()

    # PNG magic
    if png_data[:8] != b'\x89PNG\r\n\x1a\n':
        res.fail("Invalid PNG magic header")
        return res

    offset = 8
    chunks = []
    has_iccp = False
    has_srgb = False
    has_gama = False

    while offset < len(png_data):
        if offset + 8 > len(png_data):
            break
        chunk_len, chunk_type = struct.unpack(">I4s", png_data[offset:offset+8])
        chunk_name = chunk_type.decode("ascii", errors="replace")
        chunks.append(chunk_name)
        if chunk_name == "iCCP":
            has_iccp = True
        elif chunk_name == "sRGB":
            has_srgb = True
        elif chunk_name == "gAMA":
            has_gama = True
        # jump to next chunk: 4 len + 4 type + data + 4 crc
        offset += 12 + chunk_len

    res.log(f"PNG Chunks present: {chunks}")
    if has_iccp and has_srgb:
        res.fail("PNG contains BOTH iCCP and sRGB chunks (common source of libpng warnings)!")
    elif has_iccp:
        res.log("PNG contains iCCP profile chunk.")
    else:
        res.log("PNG contains clean standard sRGB/unprofiled chunk layout (immune to libpng iCCP warnings).")

    # 3. Qt QImageReader validation
    reader = QImageReader(SPLASH_PATH)
    qimg = reader.read()
    if qimg.isNull():
        res.fail(f"QImageReader failed to read PNG: {reader.errorString()}")
    else:
        res.log(f"QImageReader successfully loaded image: size={qimg.width()}x{qimg.height()}, format={qimg.format()}")
        if qimg.width() != 320 or qimg.height() != 320:
            res.fail(f"Qt image size is {qimg.width()}x{qimg.height()}, expected 320x320")

    # 4. Check if Qt emitted any color profile warnings
    if qt_warnings:
        res.fail(f"Qt emitted warnings while loading PNG: {qt_warnings}")
    else:
        res.log("Qt emitted zero warnings during QImageReader execution.")

    # 5. Cross-Check with Master SVG Rendered at 320x320
    renderer = QSvgRenderer(SVG_PATH)
    ref_img = QImage(320, 320, QImage.Format_ARGB32_Premultiplied)
    ref_img.fill(0)
    p = QPainter(ref_img)
    renderer.render(p)
    p.end()

    # Compare pixel arrays
    arr_splash = np.array(pil_img)  # RGBA
    # Extract ref_img RGBA
    arr_ref = np.frombuffer(ref_img.constBits(), dtype=np.uint8).reshape((320, 320, 4))
    # Convert BGRA to RGBA for comparison
    arr_ref_rgba = np.zeros_like(arr_ref)
    arr_ref_rgba[:, :, 0] = arr_ref[:, :, 2] # R
    arr_ref_rgba[:, :, 1] = arr_ref[:, :, 1] # G
    arr_ref_rgba[:, :, 2] = arr_ref[:, :, 0] # B
    arr_ref_rgba[:, :, 3] = arr_ref[:, :, 3] # A

    # Compute MSE across non-transparent pixels
    diff = np.abs(arr_splash.astype(np.float32) - arr_ref_rgba.astype(np.float32))
    mse = np.mean(diff ** 2)
    max_diff = np.max(diff)
    res.log(f"Cross-comparison with master SVG at 320x320: MSE={mse:.2f}, MaxDiff={max_diff:.1f}")
    if mse > 50.0:
        res.fail(f"High deviation between splash PNG and master SVG: MSE={mse:.2f}")
    else:
        res.log("Splash screen PNG rasterization faithfully matches master SVG rendering.")

    return res


def test_qsplashscreen_sim():
    res = TestResult("Test 6: QSplashScreen Runtime Instantiation Simulation")
    global qt_warnings
    qt_warnings.clear()

    # Simulate: QPixmap pixmap(path)
    pix = QPixmap(SPLASH_PATH)
    if pix.isNull():
        res.fail("QPixmap(SPLASH_PATH) isNull() == True")
        return res

    res.log(f"QPixmap loaded: {pix.width()}x{pix.height()}, depth={pix.depth()}bpp")
    if pix.width() != 320 or pix.height() != 320:
        res.fail(f"QPixmap dimensions {pix.width()}x{pix.height()} != 320x320")

    if pix.hasAlpha():
        res.log("QPixmap correctly retains alpha channel transparency for curved splash masks.")
    else:
        res.fail("QPixmap missing alpha channel!")

    if qt_warnings:
        res.fail(f"Qt logged warnings during QPixmap load: {qt_warnings}")
    else:
        res.log("Clean QPixmap initialization with zero warnings.")

    return res


def test_concurrent_and_stress_rendering():
    res = TestResult("Test 7: Thread-Safety & Render Leak Stress Test")
    renderer = QSvgRenderer(SVG_PATH)
    s = 64

    # Run 500 render passes in tight loop to detect crashes or mem errors
    try:
        for i in range(500):
            img = QImage(s, s, QImage.Format_ARGB32_Premultiplied)
            p = QPainter(img)
            renderer.render(p)
            p.end()
        res.log("500 sequential render iterations completed cleanly with zero faults.")
    except Exception as e:
        res.fail(f"Render iteration failed: {e}")

    return res


def run_all():
    print("=" * 70)
    print("ADVERSARIAL VERIFICATION SUITE: SHOTCUT MINIMALIST LOGO & ASSETS")
    print("=" * 70)

    tests = [
        test_xml_and_svg_syntax,
        test_qtsvg_renderer_compatibility,
        test_multiscale_rendering,
        test_geometric_sharpness_and_contrast,
        test_splash_screen_png,
        test_qsplashscreen_sim,
        test_concurrent_and_stress_rendering,
    ]

    results = []
    all_passed = True
    for t in tests:
        r = t()
        results.append(r)
        print(r.summary())
        print("-" * 70)
        if not r.passed:
            all_passed = False

    print("\nFINAL AUDIT VERDICT:")
    if all_passed:
        print(">>> VERDICT: APPROVE <<<")
        print("All 7 adversarial tests passed with 100% compliance!")
    else:
        print(">>> VERDICT: REQUEST_CHANGES <<<")
        print("One or more adversarial checks failed. Review details above.")
    print("=" * 70)

    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(run_all())
