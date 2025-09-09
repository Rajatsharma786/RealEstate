#!/usr/bin/env python3
"""
Simple test runner for the Real Estate Agent application.

Usage:
    python run_tests.py                    # Run all simple tests
    python run_tests.py imports           # Run only import tests
    python run_tests.py simple            # Run only simple tests
"""

import subprocess
import sys
import os

def run_tests(test_type="all"):
    """Run tests based on type."""
    print(f"🧪 Running {test_type} tests for Real Estate Agent")
    print("=" * 50)
    
    # Change to project root directory
    project_root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_root)
    
    try:
        if test_type == "imports":
            # Run only import tests
            result = subprocess.run([
                sys.executable, "-m", "pytest", 
                "tests/test_imports.py", 
                "-v", 
                "-s",
                "--tb=short"
            ], capture_output=False, text=True)
            
        elif test_type == "simple":
            # Run only simple tests
            result = subprocess.run([
                sys.executable, "-m", "pytest", 
                "tests/test_simple.py", 
                "-v", 
                "-s",
                "--tb=short"
            ], capture_output=False, text=True)
            
        else:
            # Run all tests
            result = subprocess.run([
                sys.executable, "-m", "pytest", 
                "tests/", 
                "-v", 
                "-s",
                "--tb=short"
            ], capture_output=False, text=True)
        
        if result.returncode == 0:
            print(f"\n✅ All {test_type} tests passed!")
            return True
        else:
            print(f"\n❌ Some {test_type} tests failed!")
            return False
            
    except Exception as e:
        print(f"\n❌ Error running tests: {e}")
        return False

def show_help():
    """Show help message."""
    print("""
🧪 Real Estate Agent Test Runner

Usage:
    python run_tests.py                    # Run all tests
    python run_tests.py imports           # Run only import tests  
    python run_tests.py simple            # Run only simple tests
    python run_tests.py help              # Show this help

Available test types:
    - imports: Basic import tests
    - simple: Simple functionality tests
    - all: All available tests (default)
""")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_type = sys.argv[1].lower()
        if test_type == "help":
            show_help()
            sys.exit(0)
        elif test_type in ["imports", "simple", "all"]:
            success = run_tests(test_type)
        else:
            print(f"❌ Unknown test type: {test_type}")
            show_help()
            sys.exit(1)
    else:
        # Run all tests by default
        success = run_tests("all")
    
    sys.exit(0 if success else 1)