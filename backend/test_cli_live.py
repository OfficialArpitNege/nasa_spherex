#!/usr/bin/env python3
"""
Live verification script for SPHEREx Moving Object Explorer Interactive CLI.
Executes the CLI workflow against the REAL NASA/IRSA SPHEREx archive.
"""

import sys
from app.cli import run_cli

def main():
    print("=" * 65)
    print("  NASA/IRSA SPHEREx LIVE CLI WORKFLOW VERIFICATION")
    print("=" * 65)

    # Automated test inputs for the live CLI run:
    # RA = 276.26, DEC = 64.82, Radius = 30.0 arcmin, Selected Dates = 1,2
    test_inputs = ["276.26", "64.82", "30", "1,2"]

    def mock_input(prompt: str = "") -> str:
        val = test_inputs.pop(0)
        print(f"{prompt}{val}")
        return val

    results = run_cli(input_func=mock_input, print_func=print)

    if results and len(results) >= 2:
        print("\n[SUCCESS] Live CLI verification completed successfully with real NASA data!")
        sys.exit(0)
    else:
        print("\n[FAILED] Live CLI verification failed to return selected observations.")
        sys.exit(1)

if __name__ == "__main__":
    main()
