#!/bin/bash

# Default number of requests
NUM_REQUESTS=1000
MODEL="gpt-4o-mini"

# Allow overriding via command line argument
if [ ! -z "$1" ]; then
    NUM_REQUESTS=$1
fi

if [ ! -z "$2" ]; then
    MODEL=$2
fi

echo "Running experiment with $NUM_REQUESTS requests using $MODEL..."
./venv/bin/python main.py --num_requests $NUM_REQUESTS --model $MODEL
