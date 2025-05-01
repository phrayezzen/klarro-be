#!/usr/bin/env python3
import os
import subprocess
import sys


def run_command(command):
    try:
        subprocess.run(command, check=True)
        print(f"Successfully ran: {' '.join(command)}")
    except subprocess.CalledProcessError as e:
        print(f"Error running {' '.join(command)}: {e}")
        sys.exit(1)


def main():
    # Get the project root directory
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)

    # Run autoflake to remove unused imports
    run_command(
        [
            "autoflake",
            "--in-place",
            "--recursive",
            "--remove-all-unused-imports",
            "--remove-unused-variables",
            "--exclude",
            ".git,__pycache__,build,dist,*.egg-info,migrations",
            ".",
        ]
    )

    # Run docformatter to format docstrings
    run_command(
        [
            "docformatter",
            "--in-place",
            "--recursive",
            "--wrap-summaries",
            "79",
            "--wrap-descriptions",
            "79",
            "--pre-summary-newline",
            "--make-summary-multi-line",
            "--exclude",
            ".git,__pycache__,build,dist,*.egg-info,migrations",
            ".",
        ]
    )


if __name__ == "__main__":
    main()
