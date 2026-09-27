#!/usr/bin/env python3
"""
test_adversarial_branding_m1_dark.py
====================================
Comprehensive Adversarial Stress-Test Suite for Milestone 1 Dark Palette Branding Assets.
Authored by: teamwork_preview_challenger_m1_dark_1 (Empirical Challenger)

Tiers:
  Tier 1: Magic Byte Signatures, Chunk CRCs & Header Structure (PNG, ICO, ICNS, BMP, SVG)
  Tier 2: Frame Unpacking & Payload Decoding (Multi-Frame ICO 7 frames & ICNS 10 chunks)
  Tier 3: Alpha Channel Transparency, Depths & Anti-Aliasing Stress Test across all 55 assets
  Tier 4: Microsoft Store & Standard Asset Exact Dimension Verification (40 Store assets + 15 core)
  Tier 5: Dark Palette Aesthetic & Color Token Verification (absence of old bright colors)
  Tier 6: Vector SVG Semantic, XML & Multi-Scale Rasterization Stress Test (8px to 4096px)
  Tier 7: Packaging & Resource Cross-Reference Invariance Audit
"""

import io
import math
import os
import struct
import sys
import zlib
import xml.etree.ElementTree as ET
import unittest
from PIL import Image
import pymupdf

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Magic bytes definitions
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
ICO_MAGIC = b"\x00\x00\x01\x00"
ICNS_MAGIC = b"icns"
BMP_MAGIC = b"BM"

CORE_ASSETS = [
    ("icons/shotcut-logo-16.png", (16, 16), "PNG", "RGBA"),
    ("icons/shotcut-logo-24.png", (24, 24), "PNG", "RGBA"),
    ("icons/shotcut-logo-32.png", (32, 32), "PNG", "RGBA"),
    ("icons/shotcut-logo-48.png", (48, 48), "PNG", "RGBA"),
    ("icons/shotcut-logo-64.png", (64, 64), "PNG", "RGBA"),
    ("icons/shotcut-logo-320x320.png", (320, 320), "PNG", "RGBA"),
    ("icons/shotcut-logo-large.png", (1024, 1024), "PNG", "RGBA"),
    ("packaging/linux/icons/64x64/org.shotcut.Shotcut.png", (64, 64), "PNG", "RGBA"),
    ("packaging/linux/icons/128x128/org.shotcut.Shotcut.png", (128, 128), "PNG", "RGBA"),
    ("packaging/macos/dmg-background.png", (600, 400), "PNG", "RGB"),
    ("packaging/windows/shotcut-logo-64.bmp", (64, 64), "BMP", "RGB"),
]

STORE_ASSETS = [
    ("Square150x150Logo.scale-100.png", (150, 150)),
    ("Square150x150Logo.scale-125.png", (188, 188)),
    ("Square150x150Logo.scale-150.png", (225, 225)),
    ("Square150x150Logo.scale-200.png", (300, 300)),
    ("Square150x150Logo.scale-400.png", (600, 600)),
    ("Square310x310Logo.scale-100.png", (310, 310)),
    ("Square310x310Logo.scale-125.png", (388, 388)),
    ("Square310x310Logo.scale-150.png", (465, 465)),
    ("Square310x310Logo.scale-200.png", (620, 620)),
    ("Square310x310Logo.scale-400.png", (1240, 1240)),
    ("Square44x44Logo.scale-100.png", (44, 44)),
    ("Square44x44Logo.scale-125.png", (55, 55)),
    ("Square44x44Logo.scale-150.png", (66, 66)),
    ("Square44x44Logo.scale-200.png", (88, 88)),
    ("Square44x44Logo.scale-400.png", (176, 176)),
    ("Square44x44Logo.targetsize-16.png", (16, 16)),
    ("Square44x44Logo.targetsize-16_altform-unplated.png", (16, 16)),
    ("Square44x44Logo.targetsize-24.png", (24, 24)),
    ("Square44x44Logo.targetsize-24_altform-unplated.png", (24, 24)),
    ("Square44x44Logo.targetsize-32.png", (32, 32)),
    ("Square44x44Logo.targetsize-32_altform-unplated.png", (32, 32)),
    ("Square44x44Logo.targetsize-48.png", (48, 48)),
    ("Square44x44Logo.targetsize-48_altform-unplated.png", (48, 48)),
    ("Square44x44Logo.targetsize-256.png", (256, 256)),
    ("Square44x44Logo.targetsize-256_altform-unplated.png", (256, 256)),
    ("Square71x71Logo.scale-100.png", (71, 71)),
    ("Square71x71Logo.scale-125.png", (89, 89)),
    ("Square71x71Logo.scale-150.png", (107, 107)),
    ("Square71x71Logo.scale-200.png", (142, 142)),
    ("Square71x71Logo.scale-400.png", (284, 284)),
    ("StoreLogo.scale-100.png", (50, 50)),
    ("StoreLogo.scale-125.png", (63, 63)),
    ("StoreLogo.scale-150.png", (75, 75)),
    ("StoreLogo.scale-200.png", (100, 100)),
    ("StoreLogo.scale-400.png", (200, 200)),
    ("Wide310x150Logo.scale-100.png", (310, 150)),
    ("Wide310x150Logo.scale-125.png", (388, 188)),
    ("Wide310x150Logo.scale-150.png", (465, 225)),
    ("Wide310x150Logo.scale-200.png", (620, 300)),
    ("Wide310x150Logo.scale-400.png", (1240, 600)),
]

CONTAINER_ASSETS = [
    ("packaging/windows/shotcut-logo-64.ico", "ICO"),
    ("packaging/macos/shotcut.icns", "ICNS"),
]

SVG_ASSETS = [
    ("icons/shotcut-logo-64.svg", (64, 64)),
    ("packaging/macos/dmg-background.svg", (600, 400)),
]


def test_tier1_magic_bytes_and_headers(failures):
    print("\n--- [TIER 1] Magic Byte Signatures, Chunk CRCs & Header Structure ---")
    all_pngs = [f[0] for f in CORE_ASSETS if f[2] == "PNG"] + [
        os.path.join("packaging/windows/Microsoft Store/PackageFiles/Assets", f[0])
        for f in STORE_ASSETS
    ]

    png_checked = 0
    for rel_path in all_pngs:
        full_path = os.path.join(ROOT, rel_path)
        if not os.path.exists(full_path):
            failures.append(f"TIER 1: File not found: {rel_path}")
            continue

        with open(full_path, "rb") as f:
            data = f.read()

        if len(data) < 8 or data[:8] != PNG_MAGIC:
            failures.append(f"TIER 1: Corrupted PNG magic signature in {rel_path}")
            continue

        # Adversarially parse PNG chunk structure and verify CRCs
        pos = 8
        found_ihdr = False
        found_iend = False
        while pos < len(data):
            if pos + 8 > len(data):
                failures.append(f"TIER 1: Truncated PNG chunk header in {rel_path} at {pos}")
                break
            chunk_len, = struct.unpack(">I", data[pos:pos+4])
            chunk_type = data[pos+4:pos+8]
            pos += 8

            if pos + chunk_len + 4 > len(data):
                failures.append(f"TIER 1: Truncated chunk data {chunk_type} in {rel_path}")
                break

            chunk_data = data[pos:pos+chunk_len]
            pos += chunk_len

            chunk_crc, = struct.unpack(">I", data[pos:pos+4])
            pos += 4

            # Verify chunk CRC32
            computed_crc = zlib.crc32(chunk_type + chunk_data) & 0xffffffff
            if computed_crc != chunk_crc:
                failures.append(f"TIER 1: CRC mismatch in chunk {chunk_type} of {rel_path}: {computed_crc} != {chunk_crc}")

            if chunk_type == b"IHDR":
                found_ihdr = True
            elif chunk_type == b"IEND":
                found_iend = True
                if pos != len(data):
                    failures.append(f"TIER 1: Trailing orphan bytes ({len(data) - pos} bytes) after IEND in {rel_path}")
                break

        if not found_ihdr:
            failures.append(f"TIER 1: Missing IHDR chunk in {rel_path}")
        if not found_iend:
            failures.append(f"TIER 1: Missing IEND chunk in {rel_path}")

        png_checked += 1

    print(f"  [OK] Validated PNG magic, chunk sequences, and CRC32 across all {png_checked} PNG assets")

    # BMP magic & header structure
    bmp_path = os.path.join(ROOT, "packaging/windows/shotcut-logo-64.bmp")
    with open(bmp_path, "rb") as f:
        bmp_data = f.read()
    if len(bmp_data) < 54 or bmp_data[:2] != BMP_MAGIC:
        failures.append(f"TIER 1: Corrupted BMP magic in {bmp_path}")
    else:
        file_size, res1, res2, offset = struct.unpack("<IHHI", bmp_data[2:14])
        actual_size = os.path.getsize(bmp_path)
        if file_size != actual_size:
            failures.append(f"TIER 1: BMP header size ({file_size}) != actual ({actual_size})")
        header_size, w, h, planes, bpp, comp = struct.unpack("<IIIHHH", bmp_data[14:32])
        if header_size != 40 or w != 64 or h != 64 or planes != 1 or bpp != 24 or comp != 0:
            failures.append(f"TIER 1: BMP invalid header parameters: {header_size}, {w}x{h}, bpp={bpp}")
        else:
            print(f"  [OK] BMP magic, headers, and 24-bit uncompressed RGB layout valid: {bmp_path} ({file_size} B)")

    # ICO magic
    ico_path = os.path.join(ROOT, "packaging/windows/shotcut-logo-64.ico")
    with open(ico_path, "rb") as f:
        ico_hdr = f.read(4)
    if ico_hdr != ICO_MAGIC:
        failures.append(f"TIER 1: Corrupted ICO magic: {ico_hdr!r}")
    else:
        print(f"  [OK] ICO magic valid: {ico_path}")

    # ICNS magic
    icns_path = os.path.join(ROOT, "packaging/macos/shotcut.icns")
    with open(icns_path, "rb") as f:
        icns_hdr = f.read(8)
    magic, length = struct.unpack(">4sI", icns_hdr)
    if magic != ICNS_MAGIC:
        failures.append(f"TIER 1: Corrupted ICNS magic: {magic!r}")
    else:
        actual_size = os.path.getsize(icns_path)
        if length != actual_size:
            failures.append(f"TIER 1: ICNS container length ({length}) != actual ({actual_size})")
        else:
            print(f"  [OK] ICNS magic & container length valid: {icns_path} ({length} B)")

    # SVG XML verification
    for rel_path, _ in SVG_ASSETS:
        full_path = os.path.join(ROOT, rel_path)
        try:
            tree = ET.parse(full_path)
            root = tree.getroot()
            if not root.tag.endswith("svg"):
                failures.append(f"TIER 1: SVG root tag is not svg in {rel_path}: {root.tag}")
            print(f"  [OK] SVG valid XML & root element: {rel_path}")
        except Exception as e:
            failures.append(f"TIER 1: SVG parse error in {rel_path}: {e}")


def test_tier2_frame_unpacking_and_decoding(failures):
    print("\n--- [TIER 2] Frame Unpacking & Payload Decoding ---")

    # 1. Unpack Windows ICO frames (7 frames)
    ico_path = os.path.join(ROOT, "packaging/windows/shotcut-logo-64.ico")
    with open(ico_path, "rb") as f:
        ico_bytes = f.read()

    reserved, ico_type, count = struct.unpack("<HHH", ico_bytes[:6])
    print(f"  ICO Directory contains {count} entries")
    if reserved != 0 or ico_type != 1 or count != 7:
        failures.append(f"TIER 2: Corrupted ICO header: reserved={reserved}, type={ico_type}, count={count} (expected 7)")

    expected_ico_sizes = {(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)}
    extracted_ico_sizes = set()

    pos = 6
    for i in range(count):
        w, h, color_count, res_byte, planes, bit_count, bytes_in_res, image_offset = struct.unpack(
            "<BBBBHHII", ico_bytes[pos : pos + 16]
        )
        pos += 16
        actual_w = 256 if w == 0 else w
        actual_h = 256 if h == 0 else h

        if image_offset + bytes_in_res > len(ico_bytes):
            failures.append(f"TIER 2: ICO Frame {i} offset+len exceeds file size!")
            continue
        if bytes_in_res == 0:
            failures.append(f"TIER 2: ICO Frame {i} zero length data!")
            continue

        frame_data = ico_bytes[image_offset : image_offset + bytes_in_res]
        try:
            im = Image.open(io.BytesIO(frame_data))
            im.load()  # Force full decompress
            extracted_ico_sizes.add(im.size)
            print(f"    Frame {i}: declared=({actual_w}, {actual_h}), decoded={im.size}, format={im.format}, mode={im.mode}, payload={bytes_in_res} B")
            if im.size != (actual_w, actual_h):
                failures.append(f"TIER 2: ICO Frame {i} decoded size {im.size} != declared ({actual_w}, {actual_h})")
            # Verify frame is non-empty
            if im.getbbox() is None:
                failures.append(f"TIER 2: ICO Frame {i} is completely empty/blank!")
        except Exception as e:
            failures.append(f"TIER 2: Failed to decode ICO Frame {i}: {e}")

    missing_ico_frames = expected_ico_sizes - extracted_ico_sizes
    if missing_ico_frames:
        failures.append(f"TIER 2: ICO missing expected frames: {missing_ico_frames}")
    else:
        print(f"  [OK] ICO all 7 frames cleanly extracted and pixel buffers decoded: {sorted(extracted_ico_sizes)}")

    # 2. Unpack macOS ICNS chunks (10 chunks)
    icns_path = os.path.join(ROOT, "packaging/macos/shotcut.icns")
    with open(icns_path, "rb") as f:
        icns_bytes = f.read()

    magic, total_len = struct.unpack(">4sI", icns_bytes[:8])
    pos = 8
    expected_chunks = {
        b"ic04": (16, 16),
        b"ic11": (32, 32),
        b"ic05": (32, 32),
        b"ic12": (64, 64),
        b"ic07": (128, 128),
        b"ic13": (256, 256),
        b"ic08": (256, 256),
        b"ic14": (512, 512),
        b"ic09": (512, 512),
        b"ic10": (1024, 1024),
    }
    extracted_icns_chunks = set()

    while pos < len(icns_bytes):
        if pos + 8 > len(icns_bytes):
            failures.append(f"TIER 2: ICNS chunk header truncated at pos {pos}")
            break
        tag, chunk_size = struct.unpack(">4sI", icns_bytes[pos : pos + 8])
        if chunk_size < 8 or pos + chunk_size > len(icns_bytes):
            failures.append(f"TIER 2: ICNS chunk {tag} invalid size {chunk_size} at pos {pos}")
            break

        payload = icns_bytes[pos + 8 : pos + chunk_size]
        pos += chunk_size
        extracted_icns_chunks.add(tag)

        try:
            im = Image.open(io.BytesIO(payload))
            im.load()
            expected_sz = expected_chunks.get(tag)
            print(f"    ICNS Chunk {tag.decode('latin1', 'ignore')}: size={len(payload)} B, decoded={im.size}, format={im.format}, mode={im.mode}")
            if expected_sz and im.size != expected_sz:
                failures.append(f"TIER 2: ICNS chunk {tag} decoded size {im.size} != expected {expected_sz}")
            if im.getbbox() is None:
                failures.append(f"TIER 2: ICNS chunk {tag} is completely empty/blank!")
        except Exception as e:
            failures.append(f"TIER 2: Failed to decode ICNS chunk {tag}: {e}")

    if pos != len(icns_bytes):
        failures.append(f"TIER 2: ICNS trailing orphan bytes: pos={pos}, total={len(icns_bytes)}")

    missing_icns = set(expected_chunks.keys()) - extracted_icns_chunks
    if missing_icns:
        failures.append(f"TIER 2: ICNS missing expected chunks: {missing_icns}")
    else:
        print(f"  [OK] ICNS all 10 standard & retina chunks cleanly unpacked and verified")


def test_tier3_alpha_and_depths(failures):
    print("\n--- [TIER 3] Alpha Channel Transparency, Depths & Anti-Aliasing Stress Test ---")

    all_png_specs = [(f[0], f[3]) for f in CORE_ASSETS if f[2] == "PNG"] + [
        (os.path.join("packaging/windows/Microsoft Store/PackageFiles/Assets", f[0]), "RGBA")
        for f in STORE_ASSETS
    ]

    for rel_path, expected_mode in all_png_specs:
        full_path = os.path.join(ROOT, rel_path)
        im = Image.open(full_path)
        im.load()

        if im.mode != expected_mode:
            failures.append(f"TIER 3: {rel_path} mode {im.mode} != expected {expected_mode}")
            continue

        if expected_mode == "RGBA":
            r, g, b, a = im.split()
            min_alpha, max_alpha = a.getextrema()

            if min_alpha != 0:
                failures.append(f"TIER 3: {rel_path} has NO fully transparent pixels (min alpha = {min_alpha})")
            if max_alpha != 255:
                failures.append(f"TIER 3: {rel_path} has NO fully opaque pixels (max alpha = {max_alpha})")

            # Check for anti-aliasing gradient
            alpha_hist = a.histogram()
            anti_aliased_count = sum(alpha_hist[1:255])
            if anti_aliased_count == 0 and im.size[0] > 16:
                failures.append(f"TIER 3: {rel_path} lacks smooth anti-aliased alpha boundary!")

            # Check that top-left corner is transparent for floating icons
            corner_pixel = a.getpixel((0, 0))
            if corner_pixel != 0:
                failures.append(f"TIER 3: {rel_path} top-left corner (0,0) is NOT transparent (alpha={corner_pixel})")

    print(f"  [OK] All {len(all_png_specs)} PNG assets tested: 100% valid alpha channels & anti-aliased boundaries")

    # Inno Setup BMP test
    bmp_path = os.path.join(ROOT, "packaging/windows/shotcut-logo-64.bmp")
    im_bmp = Image.open(bmp_path)
    im_bmp.load()
    if im_bmp.mode != "RGB" or im_bmp.size != (64, 64):
        failures.append(f"TIER 3: Inno Setup BMP format/size mismatch: {im_bmp.mode}, {im_bmp.size}")
    else:
        print(f"  [OK] Inno Setup BMP is standard 24-bit RGB (64x64)")


def test_tier4_dimensions(failures):
    print("\n--- [TIER 4] Microsoft Store & Standard Asset Exact Dimension Verification ---")
    store_dir = os.path.join(ROOT, "packaging/windows/Microsoft Store/PackageFiles/Assets")

    for fname, expected_dims in STORE_ASSETS:
        full_path = os.path.join(store_dir, fname)
        if not os.path.exists(full_path):
            failures.append(f"TIER 4: Missing Store asset: {fname}")
            continue

        im = Image.open(full_path)
        im.load()
        if im.size != expected_dims:
            failures.append(f"TIER 4: Store asset {fname} dimension mismatch: {im.size} != {expected_dims}")
        else:
            if "Wide" in fname:
                expected_ratio = 310 / 150
                actual_ratio = im.width / im.height
                if abs(actual_ratio - expected_ratio) > 0.01:
                    failures.append(f"TIER 4: Wide logo {fname} aspect ratio off: {actual_ratio} vs {expected_ratio}")

    print(f"  [OK] All 40 Microsoft Store assets verified against exact dimension specifications")

    for rel_path, expected_dims, fmt, _ in CORE_ASSETS:
        full_path = os.path.join(ROOT, rel_path)
        im = Image.open(full_path)
        im.load()
        if im.size != expected_dims:
            failures.append(f"TIER 4: Core asset {rel_path} size {im.size} != {expected_dims}")

    print(f"  [OK] All core raster and packaging assets verified against exact dimension specifications")


def test_tier5_dark_palette_aesthetic(failures):
    print("\n--- [TIER 5] Dark Palette Aesthetic & Color Conformance ---")

    svg_master_path = os.path.join(ROOT, "icons/shotcut-logo-64.svg")
    with open(svg_master_path, "r", encoding="utf-8") as f:
        svg_content = f.read()

    # Required dark tokens
    dark_tokens = {
        "#1F1F26": "Deep Charcoal (Left Segment)",
        "#353744": "Dark Slate/Graphite (Right Segment)",
        "#FFFFFF": "Crisp White (Playhead Motif)",
        "#8E93A4": "Stealth Titanium (Cut/Playhead Line)",
    }
    for tok, desc in dark_tokens.items():
        if tok not in svg_content:
            failures.append(f"TIER 5: Master SVG missing dark palette token {tok} ({desc})")
        else:
            print(f"  [OK] Dark palette token present: {tok} ({desc})")

    # Forbidden bright colors from old version
    forbidden_bright_colors = ["#20E6C5", "#20e6c5", "#0066FF", "#0066ff", "#FF3366", "#ff3366"]
    for fcol in forbidden_bright_colors:
        if fcol in svg_content:
            failures.append(f"TIER 5: Master SVG still contains rejected bright color: {fcol}")
        else:
            print(f"  [OK] Rejected bright color strictly absent: {fcol}")

    # Check DMG background SVG for titanium accent
    dmg_svg_path = os.path.join(ROOT, "packaging/macos/dmg-background.svg")
    with open(dmg_svg_path, "r", encoding="utf-8") as f:
        dmg_content = f.read()
    if "#8E93A4" not in dmg_content:
        failures.append(f"TIER 5: packaging/macos/dmg-background.svg missing titanium accent (#8E93A4)")
    for fcol in ["#20E6C5", "#20e6c5"]:
        if fcol in dmg_content:
            failures.append(f"TIER 5: packaging/macos/dmg-background.svg contains old bright cyan: {fcol}")

    # Inspect rendered raster icon pixel luminance (empirical raster check)
    splash_path = os.path.join(ROOT, "icons/shotcut-logo-320x320.png")
    im_splash = Image.open(splash_path).convert("RGBA")
    # Sample non-transparent pixels
    pixels = [im_splash.getpixel((x, y)) for x in range(320) for y in range(320) if im_splash.getpixel((x, y))[3] > 128]
    # Verify we have dark pixels (luminance < 80)
    dark_pixels = [p for p in pixels if (0.299 * p[0] + 0.587 * p[1] + 0.114 * p[2]) < 80]
    # Verify we have white pixels (luminance > 240)
    white_pixels = [p for p in pixels if (0.299 * p[0] + 0.587 * p[1] + 0.114 * p[2]) > 240]
    # Verify NO bright electric cyan pixels (high green & blue, low red)
    electric_cyan_pixels = [p for p in pixels if p[0] < 50 and p[1] > 200 and p[2] > 180]

    print(f"  Raster pixel analysis on 320x320 splash: {len(pixels)} opaque pixels sampled")
    print(f"    Dark tone pixels: {len(dark_pixels)} ({len(dark_pixels)*100.0/len(pixels):.1f}%)")
    print(f"    White motif pixels: {len(white_pixels)} ({len(white_pixels)*100.0/len(pixels):.1f}%)")
    print(f"    Electric cyan pixels: {len(electric_cyan_pixels)}")

    if len(dark_pixels) == 0:
        failures.append("TIER 5: Rendered splash icon contains no dark tone pixels!")
    if len(white_pixels) == 0:
        failures.append("TIER 5: Rendered splash icon contains no white motif pixels!")
    if len(electric_cyan_pixels) > 0:
        failures.append(f"TIER 5: Rendered splash icon contains {len(electric_cyan_pixels)} bright electric cyan pixels!")


def test_tier6_svg_multi_scale_stress(failures):
    print("\n--- [TIER 6] Vector SVG Semantic, XML & Multi-Scale Rasterization Stress Test ---")

    svg_master_path = os.path.join(ROOT, "icons/shotcut-logo-64.svg")
    with open(svg_master_path, "r", encoding="utf-8") as f:
        svg_content = f.read()

    # Check for forbidden skeuomorphic or blend mode styles
    forbidden = ["mix-blend-mode", "filter=\"url", "<filter", "<feGaussianBlur", "<feDropShadow"]
    for fb in forbidden:
        if fb in svg_content:
            failures.append(f"TIER 6: Master SVG contains legacy/problematic construct: {fb}")

    # Multi-scale stress test: from extreme 8px thumbnail to extreme 4096px 8K billboard
    test_scales = [8, 16, 24, 32, 48, 64, 128, 256, 320, 512, 1024, 2048, 4096]
    for s in test_scales:
        try:
            doc = pymupdf.open("svg", svg_content.encode("utf-8"))
            page = doc[0]
            scale_fac = s / 64.0
            pix = page.get_pixmap(matrix=pymupdf.Matrix(scale_fac, scale_fac), alpha=True)
            if pix.width != s or pix.height != s:
                failures.append(f"TIER 6: PyMuPDF rasterization size mismatch at {s}px: ({pix.width}, {pix.height})")
            if len(pix.samples) != s * s * 4:
                failures.append(f"TIER 6: PyMuPDF sample buffer length mismatch at {s}px")
            doc.close()
            print(f"  [OK] Render scale {s:4}x{s:<4} -> ({pix.width}x{pix.height}, {len(pix.samples)} B)")
        except Exception as e:
            failures.append(f"TIER 6: PyMuPDF rasterization crashed at {s}px: {e}")


def test_tier7_cross_reference_invariance(failures):
    print("\n--- [TIER 7] Packaging & Resource Cross-Reference Invariance Audit ---")

    # 1. icons/resources.qrc
    qrc_path = os.path.join(ROOT, "icons/resources.qrc")
    try:
        tree = ET.parse(qrc_path)
        root = tree.getroot()
        files_in_qrc = [elem.text.strip() for elem in root.iter("file") if elem.text]
        print(f"  resources.qrc parsed successfully ({len(files_in_qrc)} registered resources)")

        if "shotcut-logo-64.svg" not in files_in_qrc:
            failures.append("TIER 7: shotcut-logo-64.svg not registered in icons/resources.qrc")
        if "shotcut-logo-320x320.png" not in files_in_qrc:
            failures.append("TIER 7: shotcut-logo-320x320.png not registered in icons/resources.qrc")

        missing_qrc_files = []
        for qf in files_in_qrc:
            full_qf = os.path.join(ROOT, "icons", qf)
            if not os.path.exists(full_qf):
                missing_qrc_files.append(qf)
        if missing_qrc_files:
            failures.append(f"TIER 7: resources.qrc references missing files on disk: {missing_qrc_files[:5]}")
        else:
            print(f"  [OK] All {len(files_in_qrc)} resources in resources.qrc exist on disk")
    except Exception as e:
        failures.append(f"TIER 7: Failed to parse resources.qrc: {e}")

    # 2. Windows Inno Setup script reference
    iss_path = os.path.join(ROOT, "packaging/windows/shotcut.iss")
    if os.path.exists(iss_path):
        with open(iss_path, "r", encoding="utf-8", errors="ignore") as f:
            iss_text = f.read()
        if 'WizardSmallImageFile="shotcut-logo-64.bmp"' in iss_text:
            bmp_path = os.path.join(ROOT, "packaging/windows/shotcut-logo-64.bmp")
            if not os.path.exists(bmp_path):
                failures.append("TIER 7: packaging/windows/shotcut.iss references missing shotcut-logo-64.bmp!")
            else:
                print("  [OK] packaging/windows/shotcut.iss WizardSmallImageFile target verified")

    # 3. Windows RC template
    rc_path = os.path.join(ROOT, "packaging/windows/shotcut.rc.in")
    if os.path.exists(rc_path):
        with open(rc_path, "r", encoding="utf-8", errors="ignore") as f:
            rc_text = f.read()
        if "shotcut-logo-64.ico" in rc_text:
            ico_path = os.path.join(ROOT, "packaging/windows/shotcut-logo-64.ico")
            if not os.path.exists(ico_path):
                failures.append("TIER 7: packaging/windows/shotcut.rc.in references missing shotcut-logo-64.ico!")
            else:
                print("  [OK] packaging/windows/shotcut.rc.in IDI_ICON1 target verified")

    # 4. macOS Info.plist template
    plist_path = os.path.join(ROOT, "packaging/macos/Info.plist.in")
    if os.path.exists(plist_path):
        with open(plist_path, "r", encoding="utf-8", errors="ignore") as f:
            plist_text = f.read()
        if "shotcut.icns" in plist_text:
            icns_path = os.path.join(ROOT, "packaging/macos/shotcut.icns")
            if not os.path.exists(icns_path):
                failures.append("TIER 7: packaging/macos/Info.plist.in references missing shotcut.icns!")
            else:
                print("  [OK] packaging/macos/Info.plist.in CFBundleIconFile target verified")

    # 5. Linux desktop entry
    desktop_path = os.path.join(ROOT, "packaging/linux/org.shotcut.Shotcut.desktop")
    if os.path.exists(desktop_path):
        with open(desktop_path, "r", encoding="utf-8", errors="ignore") as f:
            desktop_text = f.read()
        if "Icon=org.shotcut.Shotcut" in desktop_text:
            print("  [OK] packaging/linux/org.shotcut.Shotcut.desktop Icon entry verified")


class TestAdversarialBrandingM1Dark(unittest.TestCase):
    """Milestone 1 Dark Palette Branding Assets Adversarial Invariance Tests."""

    def test_tier1_magic_bytes_and_headers(self):
        failures = []
        test_tier1_magic_bytes_and_headers(failures)
        self.assertEqual(len(failures), 0, f"Defects: {failures}")

    def test_tier2_frame_unpacking_and_decoding(self):
        failures = []
        test_tier2_frame_unpacking_and_decoding(failures)
        self.assertEqual(len(failures), 0, f"Defects: {failures}")

    def test_tier3_alpha_and_depths(self):
        failures = []
        test_tier3_alpha_and_depths(failures)
        self.assertEqual(len(failures), 0, f"Defects: {failures}")

    def test_tier4_dimensions(self):
        failures = []
        test_tier4_dimensions(failures)
        self.assertEqual(len(failures), 0, f"Defects: {failures}")

    def test_tier5_dark_palette_aesthetic(self):
        failures = []
        test_tier5_dark_palette_aesthetic(failures)
        self.assertEqual(len(failures), 0, f"Defects: {failures}")

    def test_tier6_svg_multi_scale_stress(self):
        failures = []
        test_tier6_svg_multi_scale_stress(failures)
        self.assertEqual(len(failures), 0, f"Defects: {failures}")

    def test_tier7_cross_reference_invariance(self):
        failures = []
        test_tier7_cross_reference_invariance(failures)
        self.assertEqual(len(failures), 0, f"Defects: {failures}")


def main():
    print("======================================================================")
    print("SHOTCUT MILESTONE 1 DARK PALETTE ADVERSARIAL STRESS-TEST SUITE")
    print("Author: teamwork_preview_challenger_m1_dark_1 (Empirical Challenger)")
    print(f"Target Repository: {ROOT}")
    print("======================================================================")

    failures = []

    test_tier1_magic_bytes_and_headers(failures)
    test_tier2_frame_unpacking_and_decoding(failures)
    test_tier3_alpha_and_depths(failures)
    test_tier4_dimensions(failures)
    test_tier5_dark_palette_aesthetic(failures)
    test_tier6_svg_multi_scale_stress(failures)
    test_tier7_cross_reference_invariance(failures)

    print("\n======================================================================")
    if failures:
        print(f"ADVERSARIAL STRESS TEST FAILED with {len(failures)} defects/corruptions:")
        for idx, f in enumerate(failures, 1):
            print(f"  {idx}. {f}")
        print("Verdict: REQUEST_CHANGES")
        sys.exit(1)
    else:
        print("ADVERSARIAL STRESS TEST PASSED: 0 defects, 0 corruptions, 0 regressions!")
        print("Verdict: APPROVE")
        sys.exit(0)


if __name__ == "__main__":
    main()
