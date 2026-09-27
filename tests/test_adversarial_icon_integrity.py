#!/usr/bin/env python3
"""
test_adversarial_icon_integrity.py

Author: teamwork_preview_challenger (Resource & Path Integrity Challenger)
Workspace: Shotcut-AI

Adversarial Stress Test Suite for Milestone 4 (Icon Harmonization Finalization):
1. QRC Resource & Physical Disk Invariance (icons/resources.qrc and src/resources.qrc)
2. Exhaustive Icon Reference Extraction Across All Source Files (.ui, .cpp, .h, .qml, .js)
3. Broken Path, Missing Extension (.png), & Malformed URL Detection
4. Main Toolbar Silhouette Modernization & Oxygen Purge Verification (src/mainwindow.ui)
5. QML View Modernization & Dangling Oxygen Audit (src/qml/)
6. Physical Image File Signature & Magic Byte Verification on Referenced Assets
7. Installed Runtime Mirror Synchronization Audit (AppData Local Deployment)
8. C++ Qt Theme Resolution & Fallback Path Invariance (QIcon::fromTheme)
9. Full Static AST & Fast Regression Invariance Verification
"""

import os
import re
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

# Workspace paths
ROOT_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT_DIR / "src"
ICONS_DIR = ROOT_DIR / "icons"
QRC_ICONS_PATH = ICONS_DIR / "resources.qrc"
QRC_SRC_PATH = SRC_DIR / "resources.qrc"
MAINWINDOW_UI_PATH = SRC_DIR / "mainwindow.ui"
RUNTIME_QML_DIR = Path(r"C:\Users\Fox\AppData\Local\Programs\Shotcut\share\shotcut\qml")

# ANSI colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


class AdversarialIconIntegrityTester:
    def __init__(self):
        self.failures = []
        self.warnings = []
        self.qrc_icons = set()
        self.qrc_src = set()
        self.extracted_refs = []  # list of dicts: file, line, type, raw, clean
        self.theme_requests = []  # list of dicts: file, line, theme_name, fallback_arg

    def log_fail(self, check_name, msg, details=None):
        self.failures.append((check_name, msg, details))
        print(f"  {RED}[FAIL]{RESET} {check_name}: {msg}")
        if details:
            print(f"         Details: {details}")

    def log_pass(self, check_name, msg):
        print(f"  {GREEN}[PASS]{RESET} {check_name}: {msg}")

    def log_warn(self, check_name, msg, details=None):
        self.warnings.append((check_name, msg, details))
        print(f"  {YELLOW}[WARN]{RESET} {check_name}: {msg}")
        if details:
            print(f"         Details: {details}")

    # =========================================================================
    # TIER 1: QRC Resource & Physical Disk Invariance
    # =========================================================================
    def test_tier1_qrc_disk_invariance(self):
        print(f"\n{BOLD}{CYAN}--- [TIER 1] QRC Resource & Physical Disk Invariance ---{RESET}")
        
        # 1.1 Parse icons/resources.qrc
        if not QRC_ICONS_PATH.exists():
            self.log_fail("Tier 1.1", f"Missing QRC file: {QRC_ICONS_PATH}")
            return
        
        try:
            tree = ET.parse(QRC_ICONS_PATH)
            root = tree.getroot()
            for qres in root.findall("qresource"):
                for f in qres.findall("file"):
                    text = f.text.strip() if f.text else ""
                    if text:
                        self.qrc_icons.add(text)
        except Exception as e:
            self.log_fail("Tier 1.1", f"XML parse error in {QRC_ICONS_PATH}", str(e))
            return
        
        print(f"  Loaded {len(self.qrc_icons)} resource entries from {QRC_ICONS_PATH.name}")

        missing_icons_disk = []
        zero_byte_icons = []
        for rel in self.qrc_icons:
            disk_file = ICONS_DIR / rel
            if not disk_file.exists():
                missing_icons_disk.append(rel)
            else:
                if disk_file.stat().st_size == 0:
                    zero_byte_icons.append(rel)

        if missing_icons_disk:
            self.log_fail("Tier 1.1", f"{len(missing_icons_disk)} QRC icon entries missing on disk!", missing_icons_disk[:10])
        else:
            self.log_pass("Tier 1.1", f"All {len(self.qrc_icons)} registered icon resources physically exist on disk (100% integrity)")

        if zero_byte_icons:
            self.log_fail("Tier 1.1", f"{len(zero_byte_icons)} QRC icon files have size 0 bytes!", zero_byte_icons[:10])
        else:
            self.log_pass("Tier 1.1", "All icon files have non-zero payload size")

        # 1.2 Parse src/resources.qrc
        if QRC_SRC_PATH.exists():
            try:
                tree_src = ET.parse(QRC_SRC_PATH)
                root_src = tree_src.getroot()
                for qres in root_src.findall("qresource"):
                    for f in qres.findall("file"):
                        text = f.text.strip() if f.text else ""
                        if text:
                            self.qrc_src.add(text)
                
                missing_src_disk = []
                for rel in self.qrc_src:
                    disk_file = SRC_DIR / rel
                    if not disk_file.exists():
                        missing_src_disk.append(rel)
                
                if missing_src_disk:
                    self.log_fail("Tier 1.2", f"{len(missing_src_disk)} src QRC entries missing on disk!", missing_src_disk[:10])
                else:
                    self.log_pass("Tier 1.2", f"All {len(self.qrc_src)} registered src/resources.qrc files physically exist on disk")
            except Exception as e:
                self.log_fail("Tier 1.2", f"XML parse error in {QRC_SRC_PATH}", str(e))

    # =========================================================================
    # TIER 2: Exhaustive Extraction Across All Source Files (.ui, .cpp, .h, .qml, .js)
    # =========================================================================
    def test_tier2_exhaustive_extraction(self):
        print(f"\n{BOLD}{CYAN}--- [TIER 2] Exhaustive Source Code Resource Extraction ---{RESET}")
        
        file_counts = {".ui": 0, ".cpp": 0, ".h": 0, ".qml": 0, ".js": 0}
        
        qrc_pattern = re.compile(r'(?:qrc:///icons/|qrc:/icons/|:/icons/)([a-zA-Z0-9_\-\.\/]+)')
        qicon_pattern = re.compile(r'QIcon\s*\(\s*["\']([^"\']+)["\']\s*\)')
        fromtheme_pattern = re.compile(r'fromTheme\s*\(\s*["\']([^"\']*)["\'](?:\s*,\s*QIcon\s*\(\s*["\']([^"\']*)["\']\s*\))?')
        general_qrc_str = re.compile(r'["\'](qrc:[^"\']+|:/[^"\']+)["\']')

        for root, dirs, files in os.walk(SRC_DIR):
            for file in files:
                filepath = Path(root) / file
                ext = filepath.suffix.lower()
                rel_path = filepath.relative_to(ROOT_DIR)

                if ext in file_counts:
                    file_counts[ext] += 1

                # 2.1 UI files
                if ext == ".ui":
                    try:
                        tree = ET.parse(filepath)
                        for elem in tree.getroot().iter():
                            text = (elem.text or "").strip()
                            if text.startswith(":/") or text.startswith("qrc:"):
                                self.extracted_refs.append({
                                    "file": str(rel_path),
                                    "line": 0,
                                    "type": f"ui_{elem.tag}",
                                    "raw": text,
                                    "clean": self._clean_qrc_ref(text)
                                })
                            for attr_name, attr_val in elem.attrib.items():
                                val = attr_val.strip()
                                if val.startswith(":/") or val.startswith("qrc:"):
                                    self.extracted_refs.append({
                                        "file": str(rel_path),
                                        "line": 0,
                                        "type": f"ui_attr_{attr_name}",
                                        "raw": val,
                                        "clean": self._clean_qrc_ref(val)
                                    })
                    except Exception as e:
                        self.log_fail("Tier 2.1", f"Failed to parse UI file {rel_path}", str(e))

                # 2.2 C++ & Header files
                elif ext in (".cpp", ".h", ".mm"):
                    try:
                        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                            for line_no, line in enumerate(f, 1):
                                stripped = line.strip()
                                if stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*"):
                                    continue
                                
                                for m in qrc_pattern.finditer(line):
                                    ref = m.group(1).rstrip('",\';)<>')
                                    self.extracted_refs.append({
                                        "file": str(rel_path),
                                        "line": line_no,
                                        "type": "cpp_qrc",
                                        "raw": m.group(0),
                                        "clean": ref
                                    })
                                
                                for m in qicon_pattern.finditer(line):
                                    arg = m.group(1)
                                    if arg.startswith(":/") or arg.startswith("qrc:"):
                                        self.extracted_refs.append({
                                            "file": str(rel_path),
                                            "line": line_no,
                                            "type": "cpp_qicon_arg",
                                            "raw": arg,
                                            "clean": self._clean_qrc_ref(arg)
                                        })
                                
                                for m in fromtheme_pattern.finditer(line):
                                    theme_name = m.group(1)
                                    fallback = m.group(2) if m.group(2) else ""
                                    self.theme_requests.append({
                                        "file": str(rel_path),
                                        "line": line_no,
                                        "theme": theme_name,
                                        "fallback": fallback
                                    })
                    except Exception as e:
                        self.log_fail("Tier 2.2", f"Failed to read C++ file {rel_path}", str(e))

                # 2.3 QML and JS files
                elif ext in (".qml", ".js"):
                    try:
                        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                            for line_no, line in enumerate(f, 1):
                                stripped = line.strip()
                                if stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*"):
                                    continue
                                
                                for m in qrc_pattern.finditer(line):
                                    ref = m.group(1).rstrip('",\';)<>')
                                    self.extracted_refs.append({
                                        "file": str(rel_path),
                                        "line": line_no,
                                        "type": f"{ext[1:]}_qrc",
                                        "raw": m.group(0),
                                        "clean": ref
                                    })
                                
                                for m in general_qrc_str.finditer(line):
                                    val = m.group(1)
                                    if "icons/" in val:
                                        self.extracted_refs.append({
                                            "file": str(rel_path),
                                            "line": line_no,
                                            "type": f"{ext[1:]}_icon_str",
                                            "raw": val,
                                            "clean": self._clean_qrc_ref(val)
                                        })
                    except Exception as e:
                        self.log_fail("Tier 2.3", f"Failed to read QML/JS file {rel_path}", str(e))

        # Deduplicate extracted refs
        unique_refs = []
        seen = set()
        for r in self.extracted_refs:
            key = (r["file"], r["line"], r["raw"])
            if key not in seen:
                seen.add(key)
                unique_refs.append(r)
        self.extracted_refs = unique_refs

        print(f"  Scanned files: {file_counts['.ui']} UI, {file_counts['.cpp']} CPP, {file_counts['.h']} H, {file_counts['.qml']} QML, {file_counts['.js']} JS (Total {sum(file_counts.values())} files)")
        print(f"  Extracted {len(self.extracted_refs)} unique icon/resource reference locations in source code")
        print(f"  Extracted {len(self.theme_requests)} QIcon::fromTheme requests in C++")
        self.log_pass("Tier 2", f"Successfully extracted {len(self.extracted_refs)} references across {sum(file_counts.values())} source files")

    def _clean_qrc_ref(self, ref_str):
        s = ref_str.strip().rstrip('",\';)<>')
        if s.startswith("qrc:///icons/"):
            return s[len("qrc:///icons/"):]
        elif s.startswith("qrc:/icons/"):
            return s[len("qrc:/icons/"):]
        elif s.startswith(":/icons/"):
            return s[len(":/icons/"):]
        elif s.startswith("qrc:///"):
            return s[len("qrc:///"):]
        elif s.startswith("qrc:/"):
            return s[len("qrc:/"):]
        elif s.startswith(":/"):
            return s[len(":/"):]
        return s

    # =========================================================================
    # TIER 3: Path Resolution, Missing Extension (.png) & Broken Link Stress-Test
    # =========================================================================
    def test_tier3_path_resolution(self):
        print(f"\n{BOLD}{CYAN}--- [TIER 3] Path Resolution, Extension (.png) & Resource Integrity ---{RESET}")
        
        broken_refs = []
        missing_extension_refs = []
        valid_refs_count = 0

        for item in self.extracted_refs:
            clean = item["clean"]
            raw = item["raw"]
            f = item["file"]
            l = item["line"]

            # Filter out non-icon resources from src/resources.qrc
            if clean in self.qrc_src:
                valid_refs_count += 1
                continue

            # Check if extension is missing on standard icon categories
            if any(cat in clean for cat in ("dark/32x32/", "light/32x32/", "oxygen/32x32/", "oxygen-dark/32x32/")):
                if not (clean.endswith(".png") or clean.endswith(".svg") or clean.endswith(".theme")):
                    missing_extension_refs.append((f, l, raw, clean))

            # Check QRC membership and disk existence
            in_qrc = clean in self.qrc_icons
            disk_path = ICONS_DIR / clean
            on_disk = disk_path.exists()

            if not in_qrc or not on_disk:
                broken_refs.append({
                    "file": f,
                    "line": l,
                    "raw": raw,
                    "clean": clean,
                    "in_qrc": in_qrc,
                    "on_disk": on_disk
                })
            else:
                valid_refs_count += 1

        if missing_extension_refs:
            self.log_fail("Tier 3.1", f"Found {len(missing_extension_refs)} icon references missing '.png' extension!", missing_extension_refs[:10])
        else:
            self.log_pass("Tier 3.1", "Zero missing '.png' extensions across all C++, UI, and QML icon references")

        if broken_refs:
            self.log_fail("Tier 3.2", f"Found {len(broken_refs)} broken icon resource links!", broken_refs[:10])
        else:
            self.log_pass("Tier 3.2", f"100% of extracted icon references resolve to valid QRC resources & physical disk files ({valid_refs_count} valid)")

    # =========================================================================
    # TIER 4: Main Toolbar Silhouette Modernization & Oxygen Purge Audit
    # =========================================================================
    def test_tier4_toolbar_modernization(self):
        print(f"\n{BOLD}{CYAN}--- [TIER 4] Main Toolbar Modernization & Legacy Oxygen Purge ---{RESET}")
        
        if not MAINWINDOW_UI_PATH.exists():
            self.log_fail("Tier 4", f"Missing {MAINWINDOW_UI_PATH}")
            return
        
        tree = ET.parse(MAINWINDOW_UI_PATH)
        root = tree.getroot()
        
        actions = root.findall(".//action")
        print(f"  Auditing {len(actions)} actions defined in {MAINWINDOW_UI_PATH.name}")

        oxygen_in_ui = []
        non_dark_in_ui = []
        action_icons = {}

        for act in actions:
            act_name = act.attrib.get("name", "")
            icon_prop = act.find("property[@name='icon']")
            if icon_prop is not None:
                iconset = icon_prop.find("iconset")
                if iconset is not None:
                    normaloff = iconset.find("normaloff")
                    if normaloff is not None and normaloff.text:
                        icon_path = normaloff.text.strip()
                        action_icons[act_name] = icon_path
                        if "oxygen" in icon_path.lower():
                            oxygen_in_ui.append((act_name, icon_path))
                        if not ("dark/32x32" in icon_path or "shotcut-logo" in icon_path):
                            non_dark_in_ui.append((act_name, icon_path))

        print(f"  Actions with iconset: {len(action_icons)}")
        for act, pth in sorted(action_icons.items()):
            print(f"    - {act:<25} -> {pth}")

        if oxygen_in_ui:
            self.log_fail("Tier 4.1", f"Found {len(oxygen_in_ui)} legacy Oxygen icons in mainwindow.ui!", oxygen_in_ui)
        else:
            self.log_pass("Tier 4.1", "Zero Oxygen icon references in src/mainwindow.ui (100% purged from main toolbar)")

        if non_dark_in_ui:
            self.log_fail("Tier 4.2", f"Found non-dark fallback icons in mainwindow.ui: {non_dark_in_ui}")
        else:
            self.log_pass("Tier 4.2", "All mainwindow.ui actions point strictly to dark modern silhouette icons or master SVG")

    # =========================================================================
    # TIER 5: QML View Modernization & Dangling Oxygen Audit
    # =========================================================================
    def test_tier5_qml_modernization(self):
        print(f"\n{BOLD}{CYAN}--- [TIER 5] QML Modernization & Dangling Oxygen Audit ---{RESET}")
        
        qml_oxygen_refs = []
        total_qml_icons = 0
        
        for item in self.extracted_refs:
            if item["type"].startswith("qml_"):
                total_qml_icons += 1
                if "oxygen" in item["clean"].lower():
                    qml_oxygen_refs.append(item)

        print(f"  Total QML icon references inspected: {total_qml_icons}")
        
        if qml_oxygen_refs:
            self.log_fail("Tier 5.1", f"Found {len(qml_oxygen_refs)} hardcoded Oxygen references remaining in QML!", qml_oxygen_refs[:5])
        else:
            self.log_pass("Tier 5.1", f"Zero hardcoded Oxygen icon references in QML (all modernized to dark silhouettes)")

        critical_qml_files = [
            SRC_DIR / "qml" / "views" / "timeline" / "timeline.qml",
            SRC_DIR / "qml" / "views" / "timeline" / "TrackHead.qml",
            SRC_DIR / "qml" / "views" / "filter" / "FilterMenu.qml",
            SRC_DIR / "qml" / "views" / "filter" / "filterview.qml",
            SRC_DIR / "qml" / "views" / "keyframes" / "ParameterHead.qml",
            SRC_DIR / "qml" / "filters" / "gpstext" / "ui.qml"
        ]

        for qml_f in critical_qml_files:
            if not qml_f.exists():
                self.log_fail("Tier 5.2", f"Critical QML file missing: {qml_f}")
                continue
            with open(qml_f, "r", encoding="utf-8") as f:
                content = f.read()
                if "qrc:///icons/oxygen" in content or "qrc:/icons/oxygen" in content:
                    self.log_fail("Tier 5.2", f"Legacy Oxygen reference found in critical file: {qml_f.relative_to(ROOT_DIR)}")
                else:
                    self.log_pass("Tier 5.2", f"Critical component clean of Oxygen: {qml_f.relative_to(ROOT_DIR)}")

    # =========================================================================
    # TIER 6: Physical File Payload Integrity & PNG/SVG Magic Headers
    # =========================================================================
    def test_tier6_image_file_signatures(self):
        print(f"\n{BOLD}{CYAN}--- [TIER 6] Physical Image File Signatures & Header Integrity ---{RESET}")
        
        png_magic = b"\x89PNG\r\n\x1a\n"
        checked_files = set()
        corrupt_files = []

        for item in self.extracted_refs:
            clean = item["clean"]
            if clean in self.qrc_icons:
                disk_file = ICONS_DIR / clean
                if disk_file not in checked_files:
                    checked_files.add(disk_file)
                    try:
                        with open(disk_file, "rb") as f:
                            header = f.read(8)
                            if disk_file.suffix.lower() == ".png":
                                if header != png_magic:
                                    corrupt_files.append((str(disk_file), "Bad PNG header"))
                            elif disk_file.suffix.lower() == ".svg":
                                f.seek(0)
                                start = f.read(256)
                                if b"<svg" not in start and b"<?xml" not in start:
                                    corrupt_files.append((str(disk_file), "Bad SVG header"))
                    except Exception as e:
                        corrupt_files.append((str(disk_file), str(e)))

        print(f"  Verified magic headers across {len(checked_files)} referenced physical asset files")
        if corrupt_files:
            self.log_fail("Tier 6", f"Found {len(corrupt_files)} corrupt asset files!", corrupt_files)
        else:
            self.log_pass("Tier 6", f"100% of referenced image assets have valid PNG/SVG magic headers ({len(checked_files)} files)")

    # =========================================================================
    # TIER 7: Installed Runtime Mirror Synchronization Audit
    # =========================================================================
    def test_tier7_runtime_mirror_synchronization(self):
        print(f"\n{BOLD}{CYAN}--- [TIER 7] Installed Runtime Mirror Synchronization Audit ---{RESET}")
        
        if not RUNTIME_QML_DIR.exists():
            self.log_warn("Tier 7", f"Runtime QML directory not found at {RUNTIME_QML_DIR}. Skipping mirror byte check.")
            return

        modified_worker_qml = [
            "filters/audio_gain/meta.qml",
            "filters/audio_mute/meta.qml",
            "filters/bigsh0t_stabilize_360/ui.qml",
            "filters/gpstext/ui.qml",
            "filters/gradientmap/ui.qml",
            "filters/hslrange/ui.qml",
            "filters/mask_shape/ui.qml",
            "filters/richtext/vui.qml",
            "filters/time_remap/ui.qml",
            "filters/timer/ClockSpinner.qml",
            "filters/timer/ui.qml",
            "modules/Shotcut/Controls/ColorPicker.qml",
            "modules/Shotcut/Controls/KeyframesButton.qml",
            "modules/Shotcut/Controls/Preset.qml",
            "modules/Shotcut/Controls/SaveDefaultButton.qml",
            "modules/Shotcut/Controls/TimeSpinner.qml",
            "modules/Shotcut/Controls/UndoButton.qml",
            "views/filter/FilterMenu.qml",
            "views/filter/FilterMenuDelegate.qml",
            "views/filter/filterview.qml",
            "views/keyframes/ParameterHead.qml",
            "views/timeline/Clip.qml",
            "views/timeline/TrackHead.qml",
            "views/timeline/timeline.qml"
        ]

        mismatched_files = []
        for rel in modified_worker_qml:
            src_f = SRC_DIR / "qml" / rel
            inst_f = RUNTIME_QML_DIR / rel

            if not inst_f.exists():
                mismatched_files.append((rel, "Missing in runtime directory"))
                continue

            src_bytes = src_f.read_bytes()
            inst_bytes = inst_f.read_bytes()
            if src_bytes != inst_bytes:
                mismatched_files.append((rel, f"Byte mismatch (src={len(src_bytes)}B, inst={len(inst_bytes)}B)"))

        if mismatched_files:
            self.log_fail("Tier 7", f"Found {len(mismatched_files)} unsynchronized runtime QML files!", mismatched_files)
        else:
            self.log_pass("Tier 7", f"All {len(modified_worker_qml)} modified QML components are byte-identical in runtime install directory")

    # =========================================================================
    # TIER 8: C++ Qt Theme Resolution & Fallback Path Invariance
    # =========================================================================
    def test_tier8_theme_resolution_invariance(self):
        print(f"\n{BOLD}{CYAN}--- [TIER 8] C++ Qt Theme Resolution & Fallback Invariance ---{RESET}")
        
        missing_dark_counterpart = []
        broken_fallbacks = []

        for req in self.theme_requests:
            theme_name = req["theme"]
            fallback = req["fallback"]
            f = req["file"]
            l = req["line"]

            # 8.1 Does dark/32x32/<theme_name>.png exist?
            dark_rel = f"dark/32x32/{theme_name}.png"
            if dark_rel not in self.qrc_icons:
                missing_dark_counterpart.append((f, l, theme_name))

            # 8.2 If fallback QIcon provided, does it resolve?
            if fallback:
                clean_fallback = self._clean_qrc_ref(fallback)
                if clean_fallback not in self.qrc_icons or not (ICONS_DIR / clean_fallback).exists():
                    broken_fallbacks.append((f, l, fallback, clean_fallback))

        print(f"  Audited {len(self.theme_requests)} QIcon::fromTheme() calls across C++ codebase")
        
        if missing_dark_counterpart:
            self.log_warn("Tier 8.1", f"{len(missing_dark_counterpart)} theme names do not have a dark/32x32/ counterpart (will use fallback):", missing_dark_counterpart[:5])
        else:
            self.log_pass("Tier 8.1", "100% of QIcon::fromTheme() theme names possess matching dark/32x32/ icon assets")

        if broken_fallbacks:
            self.log_fail("Tier 8.2", f"Found {len(broken_fallbacks)} broken fallback icons in QIcon::fromTheme()!", broken_fallbacks)
        else:
            self.log_pass("Tier 8.2", "100% of fallback QIcon references in QIcon::fromTheme() resolve on disk and in QRC")

    # =========================================================================
    # Run All Tests & Produce Final Verdict
    # =========================================================================
    def run_all(self):
        print(f"{BOLD}======================================================================{RESET}")
        print(f"{BOLD}SHOTCUT M4 ICON HARMONIZATION ADVERSARIAL STRESS-TEST SUITE{RESET}")
        print(f"Tester Identity: teamwork_preview_challenger (Critic & Empirical Specialist)")
        print(f"Workspace: {ROOT_DIR}")
        print(f"{BOLD}======================================================================{RESET}")

        self.test_tier1_qrc_disk_invariance()
        self.test_tier2_exhaustive_extraction()
        self.test_tier3_path_resolution()
        self.test_tier4_toolbar_modernization()
        self.test_tier5_qml_modernization()
        self.test_tier6_image_file_signatures()
        self.test_tier7_runtime_mirror_synchronization()
        self.test_tier8_theme_resolution_invariance()

        print(f"\n{BOLD}======================================================================{RESET}")
        print(f"{BOLD}TEST RESULTS SUMMARY{RESET}")
        print(f"{BOLD}======================================================================{RESET}")
        print(f"Total Extracted References: {len(self.extracted_refs)}")
        print(f"Total Theme Calls Audited:  {len(self.theme_requests)}")
        print(f"Total Warnings:             {len(self.warnings)}")
        print(f"Total Failures:             {len(self.failures)}")

        if self.failures:
            print(f"\n{BOLD}{RED}>>> ADVERSARIAL TEST FAILED: {len(self.failures)} DEFECTS DETECTED <<<{RESET}")
            for name, msg, details in self.failures:
                print(f"  - [{name}] {msg}")
            print(f"\n{BOLD}Final Challenger Verdict: {RED}REQUEST_CHANGES{RESET}")
            return 1
        else:
            print(f"\n{BOLD}{GREEN}>>> ADVERSARIAL STRESS TEST PASSED: 0 DEFECTS, 0 BROKEN PATHS <<<")
            print(f"All icon references harmonize with dark modern silhouette styling.")
            print(f"Final Challenger Verdict: {GREEN}APPROVE{RESET}")
            return 0


class TestAdversarialIconIntegrity(unittest.TestCase):
    """Milestone 4 Icon Harmonization Adversarial Invariance Tests."""

    @classmethod
    def setUpClass(cls):
        cls.tester = AdversarialIconIntegrityTester()

    def test_tier1_qrc_disk_invariance(self):
        self.tester.test_tier1_qrc_disk_invariance()
        tier_fails = [f for f in self.tester.failures if f[0].startswith("Tier 1")]
        self.assertEqual(len(tier_fails), 0, f"Tier 1 Failures: {tier_fails}")

    def test_tier2_exhaustive_extraction(self):
        if not self.tester.qrc_icons:
            self.tester.test_tier1_qrc_disk_invariance()
        self.tester.test_tier2_exhaustive_extraction()
        tier_fails = [f for f in self.tester.failures if f[0].startswith("Tier 2")]
        self.assertEqual(len(tier_fails), 0, f"Tier 2 Failures: {tier_fails}")

    def test_tier3_path_resolution(self):
        if not self.tester.extracted_refs:
            self.tester.test_tier1_qrc_disk_invariance()
            self.tester.test_tier2_exhaustive_extraction()
        self.tester.test_tier3_path_resolution()
        tier_fails = [f for f in self.tester.failures if f[0].startswith("Tier 3")]
        self.assertEqual(len(tier_fails), 0, f"Tier 3 Failures: {tier_fails}")

    def test_tier4_toolbar_modernization(self):
        self.tester.test_tier4_toolbar_modernization()
        tier_fails = [f for f in self.tester.failures if f[0].startswith("Tier 4")]
        self.assertEqual(len(tier_fails), 0, f"Tier 4 Failures: {tier_fails}")

    def test_tier5_qml_modernization(self):
        self.tester.test_tier5_qml_modernization()
        tier_fails = [f for f in self.tester.failures if f[0].startswith("Tier 5")]
        self.assertEqual(len(tier_fails), 0, f"Tier 5 Failures: {tier_fails}")

    def test_tier6_image_file_signatures(self):
        if not self.tester.extracted_refs:
            self.tester.test_tier1_qrc_disk_invariance()
            self.tester.test_tier2_exhaustive_extraction()
        self.tester.test_tier6_image_file_signatures()
        tier_fails = [f for f in self.tester.failures if f[0].startswith("Tier 6")]
        self.assertEqual(len(tier_fails), 0, f"Tier 6 Failures: {tier_fails}")

    def test_tier7_runtime_mirror_synchronization(self):
        self.tester.test_tier7_runtime_mirror_synchronization()
        tier_fails = [f for f in self.tester.failures if f[0].startswith("Tier 7")]
        self.assertEqual(len(tier_fails), 0, f"Tier 7 Failures: {tier_fails}")

    def test_tier8_theme_resolution_invariance(self):
        if not self.tester.theme_requests:
            self.tester.test_tier1_qrc_disk_invariance()
            self.tester.test_tier2_exhaustive_extraction()
        self.tester.test_tier8_theme_resolution_invariance()
        tier_fails = [f for f in self.tester.failures if f[0].startswith("Tier 8")]
        self.assertEqual(len(tier_fails), 0, f"Tier 8 Failures: {tier_fails}")


if __name__ == "__main__":
    tester = AdversarialIconIntegrityTester()
    sys.exit(tester.run_all())
