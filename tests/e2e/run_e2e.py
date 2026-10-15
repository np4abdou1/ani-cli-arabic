#!/usr/bin/env python3
"""
Standalone End-to-End (E2E) Test Runner for ani-cli-arabic & ani-cli-ar-backend.
Executes 4 tiers of opaque-box tests covering all 26 system features.
Usage:
    python tests/e2e/run_e2e.py
    python tests/e2e/run_e2e.py --target https://anicliar-dashboard.pages.dev
    python tests/e2e/run_e2e.py --tier 1
"""

import argparse
import os
import sys
import time
import unittest

# Ensure repository root is on sys.path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from tests.e2e.server import EdgeWorkerEmulatorServer

# ANSI color codes
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
CYAN = "\033[36m"
GRAY = "\033[90m"


class E2EResultCollector(unittest.TestResult):
    """Custom test result collector capturing timing, status, and failures."""

    def __init__(self, verbose=True):
        super().__init__()
        self.results = []
        self._start_time = None
        self.verbose = verbose

    def startTest(self, test):
        super().startTest(test)
        self._start_time = time.perf_counter()

    def addSuccess(self, test):
        super().addSuccess(test)
        duration = time.perf_counter() - self._start_time
        self.results.append((test, "PASS", duration, None))
        if self.verbose:
            test_name = test.id().split(".")[-1]
            print(f"  [{GREEN}PASS{RESET}] {test_name:<60} {GRAY}{duration * 1000:>6.1f}ms{RESET}")

    def addFailure(self, test, err):
        super().addFailure(test, err)
        duration = time.perf_counter() - self._start_time
        self.results.append((test, "FAIL", duration, self._exc_info_to_string(err, test)))
        if self.verbose:
            test_name = test.id().split(".")[-1]
            print(f"  [{RED}FAIL{RESET}] {test_name:<60} {GRAY}{duration * 1000:>6.1f}ms{RESET}")

    def addError(self, test, err):
        super().addError(test, err)
        duration = time.perf_counter() - self._start_time
        self.results.append((test, "ERROR", duration, self._exc_info_to_string(err, test)))
        if self.verbose:
            test_name = test.id().split(".")[-1]
            print(f"  [{RED}ERROR{RESET}] {test_name:<60} {GRAY}{duration * 1000:>6.1f}ms{RESET}")

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        duration = time.perf_counter() - self._start_time
        self.results.append((test, "SKIP", duration, reason))
        if self.verbose:
            test_name = test.id().split(".")[-1]
            print(f"  [{YELLOW}SKIP{RESET}] {test_name:<60} {GRAY}{duration * 1000:>6.1f}ms{RESET}")


def run_e2e_suite(target_url=None, selected_tier=None, verbose=True):
    """Main execution function for running the E2E test suite."""
    server = None
    if target_url:
        os.environ["E2E_BASE_URL"] = target_url
        print(f"{CYAN}{BOLD}[Target]{RESET} Running against remote live deployment: {target_url}")
    elif "E2E_BASE_URL" in os.environ:
        print(f"{CYAN}{BOLD}[Target]{RESET} Using environment deployment: {os.environ['E2E_BASE_URL']}")
    else:
        # Start hermetic local emulator
        server = EdgeWorkerEmulatorServer(port=0)
        server.start()
        os.environ["E2E_BASE_URL"] = server.base_url
        print(f"{CYAN}{BOLD}[Target]{RESET} Started hermetic Edge Worker emulator: {server.base_url}")

    # Import tier modules
    from tests.e2e import test_tier1_features
    from tests.e2e import test_tier2_boundaries
    from tests.e2e import test_tier3_combinations
    from tests.e2e import test_tier4_scenarios

    tier_map = {
        1: ("Tier 1: Feature Coverage", test_tier1_features.TestTier1FeatureCoverage),
        2: ("Tier 2: Boundary & Corner Cases", test_tier2_boundaries.TestTier2BoundaryCases),
        3: ("Tier 3: Cross-Feature Combinations", test_tier3_combinations.TestTier3Combinations),
        4: ("Tier 4: Real-World Scenarios", test_tier4_scenarios.TestTier4Scenarios),
    }

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    selected_tiers = [selected_tier] if selected_tier in tier_map else [1, 2, 3, 4]

    tier_test_counts = {}
    for t in selected_tiers:
        name, test_cls = tier_map[t]
        s = loader.loadTestsFromTestCase(test_cls)
        suite.addTests(s)
        tier_test_counts[t] = (name, s.countTestCases())

    print(f"\n{BOLD}{'=' * 78}{RESET}")
    print(f"{BOLD} ani-cli-arabic / ani-cli-ar-backend OPAQUE-BOX E2E TEST SUITE {RESET}")
    print(f"{BOLD}{'=' * 78}{RESET}")
    for t in selected_tiers:
        name, count = tier_test_counts[t]
        print(f"  {BLUE}●{RESET} {BOLD}{name}{RESET}: {count} tests loaded")
    total_planned = sum(c for _, c in tier_test_counts.values())
    print(f"  {CYAN}Total Test Cases Planned:{RESET} {BOLD}{total_planned}{RESET}")
    print(f"{BOLD}{'-' * 78}{RESET}\n")

    collector = E2EResultCollector(verbose=verbose)
    start_time = time.perf_counter()

    suite.run(collector)

    total_duration = time.perf_counter() - start_time

    # Cleanup emulator server
    if server:
        server.stop()

    # Reporting
    passed = sum(1 for _, st, _, _ in collector.results if st == "PASS")
    failed = sum(1 for _, st, _, _ in collector.results if st == "FAIL")
    errors = sum(1 for _, st, _, _ in collector.results if st == "ERROR")
    skipped = sum(1 for _, st, _, _ in collector.results if st == "SKIP")
    total_executed = len(collector.results)

    print(f"\n{BOLD}{'=' * 78}{RESET}")
    print(f"{BOLD} E2E TEST EXECUTION SUMMARY {RESET}")
    print(f"{BOLD}{'=' * 78}{RESET}")
    print(f"  Total Tests Executed : {BOLD}{total_executed}{RESET}")
    print(f"  Passed               : {GREEN}{passed}{RESET}")
    print(f"  Failed               : {RED if failed else GREEN}{failed}{RESET}")
    print(f"  Errors               : {RED if errors else GREEN}{errors}{RESET}")
    print(f"  Skipped              : {YELLOW}{skipped}{RESET}")
    print(f"  Total Duration       : {BOLD}{total_duration:.2f}s{RESET}")
    print(f"{BOLD}{'=' * 78}{RESET}")

    # Print failures if any
    if failed or errors:
        print(f"\n{RED}{BOLD}FAILURES / ERRORS DETAIL:{RESET}")
        for test, st, dur, detail in collector.results:
            if st in ("FAIL", "ERROR"):
                print(f"\n{RED}[{st}] {test.id()}{RESET}")
                print(detail)
        return 1

    # Check minimum requirement >= 100 tests when running full suite
    if selected_tier is None and total_executed < 100:
        print(f"\n{RED}{BOLD}ERROR: Total executed tests ({total_executed}) < required 100 tests!{RESET}")
        return 1

    print(f"\n{GREEN}{BOLD}✓ ALL {total_executed} E2E TESTS PASSED SUCCESSFULLY!{RESET}\n")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Run ani-cli-arabic E2E Test Suite")
    parser.add_argument("--target", help="Base URL of live deployment (e.g. https://anicliar-dashboard.pages.dev)")
    parser.add_argument("--tier", type=int, choices=[1, 2, 3, 4], help="Run only specific tier")
    parser.add_argument("-q", "--quiet", action="store_true", help="Quiet output (summary only)")
    args = parser.parse_args()

    exit_code = run_e2e_suite(
        target_url=args.target,
        selected_tier=args.tier,
        verbose=not args.quiet
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
