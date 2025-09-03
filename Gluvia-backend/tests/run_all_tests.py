#!/usr/bin/env python3
"""
Comprehensive test runner for Gluvia application.
Runs all test suites and generates detailed reports.
"""

import os
import sys
import json
import time
import argparse
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Any

# Add the parent directory to sys.path so we can import from the main application
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import coverage


class TestRunner:
    """Main test runner class that orchestrates all test execution."""

    def __init__(self, test_dir: str = None):
        self.test_dir = test_dir or str(Path(__file__).parent)
        self.project_root = str(Path(__file__).parent.parent)
        self.results = {}
        self.coverage_instance = None

    def setup_test_environment(self):
        """Set up the test environment and ensure all dependencies are available."""
        print("🔧 Setting up test environment...")

        # Ensure we're in the right directory
        os.chdir(self.project_root)

        # Initialize coverage
        self.coverage_instance = coverage.Coverage(
            source=[self.project_root],
            omit=[
                "*/tests/*",
                "*/venv/*",
                "*/__pycache__/*",
                "*/.*",
                "setup.py"
            ]
        )
        self.coverage_instance.start()

        # Set environment variables for testing
        os.environ["TESTING"] = "true"
        os.environ["DATABASE_URL"] = "sqlite:///test_gluvia.db"

        print("✅ Test environment ready")

    def run_test_suite(self, show_warnings: bool = False) -> Tuple[Dict, str]:
        """Run all test suites and collect results."""
        print("\n🚀 Starting test execution...")

        test_files = [
            ("test_auth.py", "Authentication", "User registration, login, deletion, concurrent operations"),
            ("test_prescriptions.py", "Prescriptions", "Prescription creation, questionnaires, dose logging"),
            ("test_safety_validators.py", "Safety", "Insulin dose safety checks, overdose detection"),
            ("test_performance.py", "Performance", "Load testing, concurrent users, memory usage"),
            ("test_integration_auth.py", "Integration", "End-to-end authentication flow testing"),
        ]

        results = {
            "timestamp": datetime.now().isoformat(),
            "total_suites": len(test_files),
            "results": [],
            "passed_suites": 0,
            "failed_suites": 0,
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "warnings": [],
            "coverage": {}
        }

        for test_file, suite_name, description in test_files:
            print(f"\n📋 Running {suite_name} tests ({test_file})...")

            test_path = os.path.join(self.test_dir, test_file)
            if not os.path.exists(test_path):
                print(f"⚠️  Test file {test_file} not found, skipping...")
                continue

            # Run pytest for this specific file
            cmd = [
                sys.executable, "-m", "pytest",
                test_path,
                "-v",
                "--tb=short",
                "--json-report",
                "--json-report-file=temp_result.json"
            ]

            if not show_warnings:
                cmd.append("--disable-warnings")

            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    cwd=self.project_root,
                    timeout=300  # 5 minute timeout per test suite
                )

                # Parse results
                suite_result = self._parse_test_result(result, suite_name, description)
                results["results"].append(suite_result)

                if suite_result["success"]:
                    results["passed_suites"] += 1
                    print(f"✅ {suite_name} tests passed")
                else:
                    results["failed_suites"] += 1
                    print(f"❌ {suite_name} tests failed")

                results["total_tests"] += suite_result.get("total_tests", 0)
                results["passed_tests"] += suite_result.get("passed_tests", 0)
                results["failed_tests"] += suite_result.get("failed_tests", 0)

            except subprocess.TimeoutExpired:
                print(f"⏰ {suite_name} tests timed out")
                results["results"].append({
                    "suite": suite_name,
                    "details": description,
                    "success": False,
                    "error": "Test suite timed out after 5 minutes",
                    "total_tests": 0,
                    "passed_tests": 0,
                    "failed_tests": 0
                })
                results["failed_suites"] += 1

            except Exception as e:
                print(f"💥 Error running {suite_name} tests: {e}")
                results["results"].append({
                    "suite": suite_name,
                    "details": description,
                    "success": False,
                    "error": str(e),
                    "total_tests": 0,
                    "passed_tests": 0,
                    "failed_tests": 0
                })
                results["failed_suites"] += 1

        # Stop coverage and get report
        if self.coverage_instance:
            self.coverage_instance.stop()
            self.coverage_instance.save()

            # Generate coverage report
            coverage_data = self._generate_coverage_report()
            results["coverage"] = coverage_data

        # Determine overall status
        final_status = "PASS" if results["failed_suites"] == 0 else "FAIL"

        print(f"\n📊 Test Summary:")
        print(f"   Total Suites: {results['total_suites']}")
        print(f"   Passed: {results['passed_suites']}")
        print(f"   Failed: {results['failed_suites']}")
        print(f"   Total Tests: {results['total_tests']}")
        print(f"   Overall Status: {final_status}")

        return results, final_status

    def _parse_test_result(self, result: subprocess.CompletedProcess, suite_name: str, description: str) -> Dict:
        """Parse the result of a test suite run."""
        success = result.returncode == 0

        suite_result = {
            "suite": suite_name,
            "details": description,
            "success": success,
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "stdout": result.stdout,
            "stderr": result.stderr
        }

        # Try to parse JSON report if available
        temp_result_file = os.path.join(self.project_root, "temp_result.json")
        if os.path.exists(temp_result_file):
            try:
                with open(temp_result_file, 'r') as f:
                    json_data = json.load(f)

                summary = json_data.get("summary", {})
                suite_result["total_tests"] = summary.get("total", 0)
                suite_result["passed_tests"] = summary.get("passed", 0)
                suite_result["failed_tests"] = summary.get("failed", 0)

                # Clean up temp file
                os.remove(temp_result_file)

            except Exception as e:
                print(f"⚠️  Could not parse JSON report: {e}")

        return suite_result

    def _generate_coverage_report(self) -> Dict:
        """Generate coverage report data."""
        try:
            coverage_data = {
                "total_coverage": 0,
                "lines_covered": 0,
                "lines_total": 0,
                "files": {}
            }

            # Get coverage data
            if self.coverage_instance:
                total = self.coverage_instance.report(show_missing=False, skip_covered=False)
                coverage_data["total_coverage"] = round(total, 2)

                # Generate detailed report
                report_data = {}
                for filename in self.coverage_instance.get_data().measured_files():
                    if filename.startswith(self.project_root):
                        rel_path = os.path.relpath(filename, self.project_root)
                        analysis = self.coverage_instance.analysis2(filename)

                        report_data[rel_path] = {
                            "statements": len(analysis.statements),
                            "missing": len(analysis.missing),
                            "excluded": len(analysis.excluded),
                            "coverage": round(
                                (len(analysis.statements) - len(analysis.missing)) / len(analysis.statements) * 100
                                if analysis.statements else 0, 2
                            )
                        }

                coverage_data["files"] = report_data

            return coverage_data

        except Exception as e:
            print(f"⚠️  Error generating coverage report: {e}")
            return {"error": str(e)}

    def generate_test_report(self, results: Dict):
        """Generate comprehensive test reports."""
        print("\n📝 Generating test reports...")

        # Generate JSON report
        json_report_path = os.path.join(self.test_dir, "test_results.json")
        with open(json_report_path, 'w') as f:
            json.dump(results, f, indent=2)

        # Generate summary JSON (legacy format)
        summary_data = {
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "TotalSuites": results["total_suites"],
            "Results": [
                {
                    "Suite": r["suite"],
                    "Details": r["details"],
                    "Success": r["success"]
                }
                for r in results["results"]
            ],
            "PassedSuites": results["passed_suites"]
        }

        summary_report_path = os.path.join(self.test_dir, "test_summary.json")
        with open(summary_report_path, 'w') as f:
            json.dump(summary_data, f, indent=4)

        # Generate HTML coverage report
        if self.coverage_instance:
            try:
                html_dir = os.path.join(self.test_dir, "htmlcov")
                self.coverage_instance.html_report(directory=html_dir)
                print(f"📊 HTML coverage report generated in {html_dir}")
            except Exception as e:
                print(f"⚠️  Could not generate HTML coverage report: {e}")

        # Generate markdown report
        self._generate_markdown_report(results)

        print(f"✅ Reports generated:")
        print(f"   - JSON: {json_report_path}")
        print(f"   - Summary: {summary_report_path}")
        print(f"   - HTML Coverage: {os.path.join(self.test_dir, 'htmlcov', 'index.html')}")
        print(f"   - Markdown: {os.path.join(self.test_dir, 'TEST_REPORT.md')}")

    def _generate_markdown_report(self, results: Dict):
        """Generate a markdown test report."""
        report_path = os.path.join(self.test_dir, "TEST_REPORT.md")

        with open(report_path, 'w') as f:
            f.write(f"# Gluvia Test Report\n\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            f.write(f"## Summary\n\n")
            f.write(f"- **Total Test Suites:** {results['total_suites']}\n")
            f.write(f"- **Passed Suites:** {results['passed_suites']}\n")
            f.write(f"- **Failed Suites:** {results['failed_suites']}\n")
            f.write(f"- **Total Tests:** {results['total_tests']}\n")
            f.write(f"- **Success Rate:** {round(results['passed_suites']/results['total_suites']*100, 1)}%\n\n")

            if "coverage" in results and "total_coverage" in results["coverage"]:
                f.write(f"- **Code Coverage:** {results['coverage']['total_coverage']}%\n\n")

            f.write(f"## Test Suite Results\n\n")
            for result in results["results"]:
                status = "✅ PASS" if result["success"] else "❌ FAIL"
                f.write(f"### {result['suite']} {status}\n\n")
                f.write(f"**Description:** {result['details']}\n\n")

                if result.get("total_tests", 0) > 0:
                    f.write(f"- Tests Run: {result['total_tests']}\n")
                    f.write(f"- Passed: {result['passed_tests']}\n")
                    f.write(f"- Failed: {result['failed_tests']}\n\n")

                if not result["success"] and result.get("error"):
                    f.write(f"**Error:** {result['error']}\n\n")

    def cleanup_test_artifacts(self):
        """Clean up temporary test files and artifacts."""
        print("\n🧹 Cleaning up test artifacts...")

        artifacts = [
            "temp_result.json",
            ".coverage",
            "test_gluvia.db"
        ]

        for artifact in artifacts:
            artifact_path = os.path.join(self.project_root, artifact)
            if os.path.exists(artifact_path):
                try:
                    os.remove(artifact_path)
                except Exception as e:
                    print(f"⚠️  Could not remove {artifact}: {e}")

        print("✅ Cleanup completed")


def setup_test_environment():
    """Global test environment setup."""
    runner = TestRunner()
    runner.setup_test_environment()


def run_test_suite(show_warnings: bool = False) -> Tuple[Dict, str]:
    """Run all test suites."""
    runner = TestRunner()
    return runner.run_test_suite(show_warnings)


def generate_test_report(results: Dict):
    """Generate test reports."""
    runner = TestRunner()
    runner.generate_test_report(results)


def cleanup_test_artifacts():
    """Clean up test artifacts."""
    runner = TestRunner()
    runner.cleanup_test_artifacts()


def main():
    """Main entry point for the test runner."""
    parser = argparse.ArgumentParser(description="Gluvia Test Runner")
    parser.add_argument(
        "--show-warnings",
        action="store_true",
        help="Show pytest warnings"
    )
    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="Skip cleanup of test artifacts"
    )

    args = parser.parse_args()

    print("🧪 Gluvia Test Suite Runner")
    print("=" * 50)

    try:
        # Setup
        setup_test_environment()

        # Run tests
        results, final_status = run_test_suite(show_warnings=args.show_warnings)

        # Generate reports
        generate_test_report(results)

        # Cleanup
        if not args.no_cleanup:
            cleanup_test_artifacts()

        # Determine exit code
        exit_code = 0 if final_status == "PASS" else 1

        print(f"\n🏁 Test run completed with status: {final_status}")
        return exit_code

    except Exception as e:
        print(f"\n💥 Test runner error: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
