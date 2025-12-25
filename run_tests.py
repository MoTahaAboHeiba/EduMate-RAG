#!/usr/bin/env python
"""
Test Runner for EduMate RAG System
Executes different test suites with detailed reporting
Usage: python run_tests.py [options]
"""

import subprocess
import sys
from pathlib import Path
from typing import List
import argparse
from datetime import datetime


class TestRunner:
    """Manages test execution and reporting"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.test_dir = self.project_root / "tests"
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def run_command(self, cmd: List[str], description: str = "") -> bool:
        """
        Run a command and return success status
        
        Args:
            cmd: Command to run as list
            description: Description for logging
        
        Returns:
            True if successful, False otherwise
        """
        if description:
            print(f"\n{'='*70}")
            print(f" {description}")
            print(f"{'='*70}\n")
        
        try:
            result = subprocess.run(cmd, cwd=self.project_root)
            return result.returncode == 0
        except Exception as e:
            print(f" Error: {e}")
            return False
    
    def run_all_tests(self) -> bool:
        """Run all tests"""
        return self.run_command(
            [sys.executable, "-m", "pytest", "tests/", "-v"],
            "Running All Tests"
        )
    
    def run_unit_tests(self) -> bool:
        """Run only unit tests"""
        return self.run_command(
            [sys.executable, "-m", "pytest", "tests/", "-m", "unit", "-v"],
            "Running Unit Tests"
        )
    
    def run_integration_tests(self) -> bool:
        """Run only integration tests"""
        return self.run_command(
            [sys.executable, "-m", "pytest", "tests/", "-m", "integration", "-v"],
            "Running Integration Tests"
        )
    
    def run_api_tests(self) -> bool:
        """Run only API tests"""
        return self.run_command(
            [sys.executable, "-m", "pytest", "tests/", "-m", "api", "-v"],
            "Running API Tests"
        )
    
    def run_specific_test(self, test_path: str) -> bool:
        """Run a specific test file or test"""
        return self.run_command(
            [sys.executable, "-m", "pytest", test_path, "-v"],
            f"Running Specific Test: {test_path}"
        )
    
    def run_with_coverage(self) -> bool:
        """Run tests with coverage report"""
        return self.run_command(
            [
                sys.executable, "-m", "pytest", "tests/",
                "--cov=src",
                "--cov-report=html",
                "--cov-report=term-missing",
                "-v"
            ],
            "Running Tests with Coverage Report"
        )
    
    def run_fast_tests(self) -> bool:
        """Run only fast tests (exclude slow ones)"""
        return self.run_command(
            [sys.executable, "-m", "pytest", "tests/", "-m", "not slow", "-v"],
            "Running Fast Tests (excluding slow)"
        )
    
    def run_parallel_tests(self, workers: int = 4) -> bool:
        """Run tests in parallel"""
        return self.run_command(
            [sys.executable, "-m", "pytest", "tests/", f"-n", str(workers), "-v"],
            f"Running Tests in Parallel ({workers} workers)"
        )
    
    def run_smoke_tests(self) -> bool:
        """Run smoke tests (quick sanity checks)"""
        smoke_tests = [
            "tests/test_config.py::TestConfig::test_config_exists",
            "tests/test_api.py::TestAPI::test_root_endpoint",
            "tests/test_pdf_loader.py::TestPDFLoader::test_pdf_loader_initializes",
        ]
        
        print(f"\n{'='*70}")
        print(f" Running Smoke Tests (Quick Sanity Checks)")
        print(f"{'='*70}\n")
        
        all_passed = True
        for test in smoke_tests:
            result = self.run_command(
                [sys.executable, "-m", "pytest", test, "-v"],
                f"Smoke: {test.split('::')[-1]}"
            )
            all_passed = all_passed and result
        
        return all_passed
    
    def run_all_with_report(self) -> bool:
        """Run all tests and generate detailed report"""
        print(f"\n{'='*70}")
        print(f" EduMate RAG - Comprehensive Test Suite")
        print(f"{'='*70}")
        print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*70}\n")
        
        results = {
            "Unit Tests": self.run_unit_tests(),
            "Integration Tests": self.run_integration_tests(),
            "API Tests": self.run_api_tests(),
            "Coverage Report": self.run_with_coverage(),
        }
        
        # Print summary
        print(f"\n{'='*70}")
        print(f" TEST SUMMARY")
        print(f"{'='*70}\n")
        
        for name, passed in results.items():
            status = " PASSED" if passed else "❌ FAILED"
            print(f"{name:.<50} {status}")
        
        all_passed = all(results.values())
        
        print(f"\n{'='*70}")
        if all_passed:
            print(f" ALL TESTS PASSED!")
        else:
            print(f" SOME TESTS FAILED - See above for details")
        print(f"{'='*70}\n")
        
        return all_passed


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="EduMate RAG Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_tests.py                    # Run all tests
  python run_tests.py --unit             # Run unit tests only
  python run_tests.py --coverage         # Run with coverage report
  python run_tests.py --smoke            # Run smoke tests
  python run_tests.py --fast             # Run fast tests
  python run_tests.py --parallel 8       # Run parallel with 8 workers
  python run_tests.py --test tests/test_api.py::TestAPI::test_health_endpoint
        """
    )
    
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all tests with full report (default)"
    )
    parser.add_argument(
        "--unit",
        action="store_true",
        help="Run unit tests only"
    )
    parser.add_argument(
        "--integration",
        action="store_true",
        help="Run integration tests only"
    )
    parser.add_argument(
        "--api",
        action="store_true",
        help="Run API tests only"
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Run tests with coverage report"
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Run smoke tests (quick sanity checks)"
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Run fast tests (exclude slow)"
    )
    parser.add_argument(
        "--parallel",
        type=int,
        metavar="N",
        help="Run tests in parallel with N workers"
    )
    parser.add_argument(
        "--test",
        type=str,
        metavar="PATH",
        help="Run specific test file or test"
    )
    
    args = parser.parse_args()
    
    runner = TestRunner()
    
    try:
        if args.unit:
            success = runner.run_unit_tests()
        elif args.integration:
            success = runner.run_integration_tests()
        elif args.api:
            success = runner.run_api_tests()
        elif args.coverage:
            success = runner.run_with_coverage()
        elif args.smoke:
            success = runner.run_smoke_tests()
        elif args.fast:
            success = runner.run_fast_tests()
        elif args.parallel:
            success = runner.run_parallel_tests(args.parallel)
        elif args.test:
            success = runner.run_specific_test(args.test)
        else:
            # Default: run all with report
            success = runner.run_all_with_report()
        
        sys.exit(0 if success else 1)
    
    except KeyboardInterrupt:
        print("\n\n  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
