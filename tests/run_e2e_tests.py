#!/usr/bin/env python3
"""
Shotcut Modernization: Master Automated End-to-End Test Runner
Orchestrates multi-tiered verification across all tiers:
- Static QML/JS Syntax Validation (436 files)
- Tier 1: Feature Coverage (70 tests across F1-F14)
- Tier 2: Boundary & Corner Cases (70 tests across F1-F14)
- Tier 3: Cross-Feature Pairwise Interactions (16 tests)
- Tier 4: Real-World Application Workloads & GUI Lifecycle (8 scenarios)
- Tier 5: Adversarial Coverage Hardening (24 tests across M1/M4 adversarial suites)

Prints aggregated statistics and exits with code 0 on complete pass.
"""

import os
import sys
import time
import argparse
import unittest
from datetime import datetime, timezone

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from tests.validate_qml import scan_directory


class TestTierResult:
    def __init__(self, name):
        self.name = name
        self.total = 0
        self.passed = 0
        self.failed = 0
        self.errors = 0
        self.skipped = 0
        self.duration = 0.0
        self.success = False
        self.details = []


def run_static_validation(verbose=False):
    """Run static analysis on QML and JS files."""
    res = TestTierResult("Static QML/JS Syntax Validator")
    start = time.time()
    qml_dir = os.path.join(PROJECT_ROOT, "src", "qml")

    print("\n" + "=" * 78)
    print(" [STATIC] Scanning QML AST and Node.js V8 Syntax across all files...")
    print("=" * 78)

    qml_c, js_c, errs = scan_directory(qml_dir, verbose=verbose)
    res.duration = time.time() - start
    res.total = qml_c + js_c

    if errs:
        res.failed = len(errs)
        res.passed = res.total - res.failed
        res.success = False
        res.details = errs
        print(f" [STATIC FAIL] Found {len(errs)} syntax errors across {res.total} files.")
    else:
        res.passed = res.total
        res.success = True
        print(f" [STATIC PASS] {res.total} files verified ({qml_c} QML, {js_c} JS) in {res.duration:.2f}s - 0 errors.")

    return res


def run_unittest_suite(suite_name, test_module_name, verbose=False):
    """Run a unittest test suite and return TestTierResult."""
    res = TestTierResult(suite_name)
    start = time.time()

    print("\n" + "=" * 78)
    print(f" [{suite_name.upper()}] Executing test cases from {test_module_name}...")
    print("=" * 78)

    loader = unittest.TestLoader()
    try:
        suite = loader.loadTestsFromName(test_module_name)
    except Exception as e:
        print(f" [ERROR] Could not load {test_module_name}: {e}")
        res.errors = 1
        res.success = False
        return res

    verbosity = 2 if verbose else 1
    stream = io_stream = io_capture = None
    runner = unittest.TextTestRunner(verbosity=verbosity)
    test_result = runner.run(suite)

    res.duration = time.time() - start
    res.total = test_result.testsRun
    res.failed = len(test_result.failures)
    res.errors = len(test_result.errors)
    res.skipped = len(test_result.skipped)
    res.passed = res.total - (res.failed + res.errors + res.skipped)
    res.success = test_result.wasSuccessful()

    for f in test_result.failures:
        res.details.append(f"{f[0].id()}: FAIL: {str(f[1]).strip().splitlines()[-1]}")
    for e in test_result.errors:
        res.details.append(f"{e[0].id()}: ERROR: {str(e[1]).strip().splitlines()[-1]}")

    status = "PASS" if res.success else "FAIL"
    print(f" [{suite_name} {status}] {res.passed}/{res.total} passed ({res.failed} fails, {res.errors} errors, {res.skipped} skipped) in {res.duration:.2f}s.")

    return res


def run_tier5_adversarial(verbose=False, no_gui=False):
    """Run Tier 5: Adversarial Coverage Hardening test suites."""
    suite_name = "Tier 5: Adversarial Coverage Hardening"
    res = TestTierResult(suite_name)
    start = time.time()

    mode_str = " (Unit/Invariance Fast Mode)" if no_gui else " (Full Stress & GUI Mode)"
    print("\n" + "=" * 78)
    print(f" [{suite_name.upper()}]{mode_str}")
    print(" Executing white-box adversarial suites:")
    print("   1. tests.test_adversarial_branding_m1_dark (Branding & packaging invariance)")
    print("   2. tests.test_adversarial_icon_integrity (Code-wide resource & path integrity)")
    print(f"   3. tests.test_adversarial_m4_icons (Runtime UI & stress recovery{' - fast unit only' if no_gui else ''})")
    print("   4. tests.test_phase2_icon_and_theme_verification (Phase 2 Lucide iconography & Grafito theme)")
    print("   5. tests.test_phase3_layout_verification (Phase 3 Grafito docks, top bar & sidebar)")
    print("   6. tests.test_phase4_viewer_verification (Phase 4 Grafito viewer & transport)")
    print("   7. tests.test_phase5_timeline_verification (Phase 5 Grafito multitrack timeline)")
    print("=" * 78)

    import tests.test_adversarial_branding_m1_dark
    import tests.test_adversarial_icon_integrity
    import tests.test_adversarial_m4_icons
    import tests.test_phase2_icon_and_theme_verification
    import tests.test_phase3_layout_verification
    import tests.test_phase4_viewer_verification
    import tests.test_phase5_timeline_verification

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 1. Branding & packaging invariance (7 tests)
    suite.addTests(loader.loadTestsFromModule(tests.test_adversarial_branding_m1_dark))

    # 2. Resource & path integrity (8 tests)
    suite.addTests(loader.loadTestsFromModule(tests.test_adversarial_icon_integrity))

    # 3. Phase 2 Lucide iconography & Grafito theme verification (6 tests)
    suite.addTests(loader.loadTestsFromModule(tests.test_phase2_icon_and_theme_verification))

    # 4. Phase 3 Grafito dock structure & top bar verification (23 tests)
    suite.addTests(loader.loadTestsFromModule(tests.test_phase3_layout_verification))

    # 5. Phase 4 Grafito viewer & transport verification (23 tests)
    suite.addTests(loader.loadTestsFromModule(tests.test_phase4_viewer_verification))

    # 6. Phase 5 Grafito multitrack timeline verification (15 tests)
    suite.addTests(loader.loadTestsFromModule(tests.test_phase5_timeline_verification))

    # 3. Runtime UI & stress recovery
    if no_gui:
        fast_test_names = getattr(tests.test_adversarial_m4_icons, "FAST_TESTS", [
            "test_dimension1_qrc_resource_integrity_and_duplicates",
            "test_dimension1_dark_silhouette_assets_on_disk",
            "test_dimension1_mainwindow_ui_action_fallbacks",
            "test_dimension2_qml_source_installed_sync",
            "test_dimension2_zero_oxygen_urls_in_modernized_qml",
            "test_dimension3_toolbar_separator_clusters",
        ])
        for tname in fast_test_names:
            suite.addTest(tests.test_adversarial_m4_icons.TestAdversarialM4Icons(tname))
    else:
        suite.addTests(loader.loadTestsFromModule(tests.test_adversarial_m4_icons))

    verbosity = 2 if verbose else 1
    runner = unittest.TextTestRunner(verbosity=verbosity)
    test_result = runner.run(suite)

    res.duration = time.time() - start
    res.total = test_result.testsRun
    res.failed = len(test_result.failures)
    res.errors = len(test_result.errors)
    res.skipped = len(test_result.skipped)
    res.passed = res.total - (res.failed + res.errors + res.skipped)
    res.success = test_result.wasSuccessful()

    for f in test_result.failures:
        res.details.append(f"{f[0].id()}: FAIL: {str(f[1]).strip().splitlines()[-1]}")
    for e in test_result.errors:
        res.details.append(f"{e[0].id()}: ERROR: {str(e[1]).strip().splitlines()[-1]}")

    status = "PASS" if res.success else "FAIL"
    print(f" [{suite_name} {status}] {res.passed}/{res.total} passed ({res.failed} fails, {res.errors} errors, {res.skipped} skipped) in {res.duration:.2f}s.")

    return res


def print_summary_table(results):
    """Prints a structured summary table of all test tiers."""
    print("\n" + "=" * 80)
    print(" SHOTCUT AUTOMATED TEST EXECUTION SUMMARY")
    print(" Timestamp: " + datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ"))
    print("=" * 80)
    print(f"{'Tier / Suite':<40} | {'Total':>6} | {'Pass':>6} | {'Fail':>6} | {'Skip':>6} | {'Time':>8} | {'Status':>6}")
    print("-" * 80)

    total_tests = 0
    total_passed = 0
    total_failed = 0
    total_skipped = 0
    total_time = 0.0
    all_success = True

    for r in results:
        status_str = "PASS" if r.success else "FAIL"
        if not r.success:
            all_success = False
        total_tests += r.total
        total_passed += r.passed
        total_failed += r.failed + r.errors
        total_skipped += r.skipped
        total_time += r.duration
        print(f"{r.name:<40} | {r.total:>6} | {r.passed:>6} | {r.failed + r.errors:>6} | {r.skipped:>6} | {r.duration:>7.2f}s | {status_str:>6}")

    print("-" * 80)
    overall_status = "SUCCESS" if all_success else "FAILURE"
    print(f"{'TOTAL AGGREGATE':<40} | {total_tests:>6} | {total_passed:>6} | {total_failed:>6} | {total_skipped:>6} | {total_time:>7.2f}s | {overall_status:>6}")
    print("=" * 80)

    return all_success


def main():
    parser = argparse.ArgumentParser(description="Shotcut Master Automated E2E Test Runner")
    parser.add_argument("--tier", type=int, choices=[1, 2, 3, 4, 5], help="Run specific tier only")
    parser.add_argument("--static", action="store_true", help="Run static syntax validation only")
    parser.add_argument("--fast", "--no-gui", dest="no_gui", action="store_true", help="Run static + Tiers 1-3 + Tier 5 unit/invariance (skip GUI process execution)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose test reporting")
    args = parser.parse_args()

    results = []
    run_all = not (args.tier or args.static)

    if args.static or run_all:
        results.append(run_static_validation(verbose=args.verbose))

    if args.tier == 1 or run_all:
        results.append(run_unittest_suite("Tier 1: Feature Coverage", "tests.test_tier1_features", verbose=args.verbose))

    if args.tier == 2 or run_all:
        results.append(run_unittest_suite("Tier 2: Boundary & Corner Cases", "tests.test_tier2_boundaries", verbose=args.verbose))

    if args.tier == 3 or run_all:
        results.append(run_unittest_suite("Tier 3: Pairwise Combinations", "tests.test_tier3_pairwise", verbose=args.verbose))

    if (args.tier == 4 or run_all) and not args.no_gui:
        results.append(run_unittest_suite("Tier 4: Real-World Scenarios", "tests.test_tier4_scenarios", verbose=args.verbose))

    if args.tier == 5 or run_all:
        results.append(run_tier5_adversarial(verbose=args.verbose, no_gui=args.no_gui))

    success = print_summary_table(results)

    if success:
        print("\n>>> ALL EXECUTED TEST SUITES COMPLETED WITH 100% PASS (Exit Code: 0) <<<\n")
        return 0
    else:
        print("\n>>> TEST SUITE REGRESSION DETECTED (Exit Code: 1) <<<\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
