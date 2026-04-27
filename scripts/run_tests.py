#!/usr/bin/env python
"""
Test Runner for EduMate RAG System
Executes different test suites with detailed reporting
Usage: python scripts/run_tests.py [options]
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
        self.project_root = Path(__file__).parent.parent
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
            print(f"[Running] {description}")
            print(f"{'='*70}\n")
        
        try:
            result = subprocess.run(cmd, cwd=self.project_root)
            return result.returncode == 0
        except Exception as e:
            print(f"Error: {e}")
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
            [sys.executable, "-m", "pytest", "tests/integration", "-v"],
            "Running Integration Tests"
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
    
    def run_specific_test(self, test_path: str) -> bool:
        """Run a specific test file or test"""
        return self.run_command(
            [sys.executable, "-m", "pytest", test_path, "-v"],
            f"Running Specific Test: {test_path}"
        )
    
    def run_all_with_report(self) -> bool:
        """Run all tests and generate detailed report"""
        print(f"\n{'='*70}")
        print(f"🧪 EduMate RAG - Test Suite")
        print(f"{'='*70}")
        print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*70}\n")
        
        success = self.run_all_tests()
        
        print(f"\n{'='*70}")
        if success:
            print(f"✅ ALL TESTS PASSED!")
        else:
            print(f"❌ SOME TESTS FAILED - See above for details")
        print(f"{'='*70}\n")
        
        return success


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="EduMate RAG Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/run_tests.py                    # Run all tests
  python scripts/run_tests.py --integration      # Run integration tests only
  python scripts/run_tests.py --coverage         # Run with coverage report
  python scripts/run_tests.py --test tests/test_suite_final.py
        """
    )
    
    parser.add_argument(
        "--integration",
        action="store_true",
        help="Run integration tests only"
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Run tests with coverage report"
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
        if args.integration:
            success = runner.run_integration_tests()
        elif args.coverage:
            success = runner.run_with_coverage()
        elif args.test:
            success = runner.run_specific_test(args.test)
        else:
            success = runner.run_all_with_report()
        
        sys.exit(0 if success else 1)
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
