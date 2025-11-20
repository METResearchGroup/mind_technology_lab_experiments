#!/bin/bash

# Default number of requests
NUM_REQUESTS=100

# Allow overriding via command line argument
if [ ! -z "$1" ]; then
    NUM_REQUESTS=$1
fi

echo "Running experiment with $NUM_REQUESTS requests..."
./venv/bin/python main.py --num_requests $NUM_REQUESTS

