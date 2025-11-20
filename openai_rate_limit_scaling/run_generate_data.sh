#!/bin/bash

# Ensure we are in the directory of the script
cd "$(dirname "$0")"

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    echo "Virtual environment not found at venv/bin/activate"
    exit 1
fi

# Run the generation script
# Pass any arguments to the python script (e.g. --num_posts 50)
python generate_fake_r_aita_data.py "$@"

