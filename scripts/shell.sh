#!/bin/bash

# Get the absolute path of the .pythonrc file
PYTHONRC_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/.pythonrc"

# Export the PYTHONSTARTUP environment variable
export PYTHONSTARTUP="$PYTHONRC_PATH"

# Start Django shell
python manage.py shell
