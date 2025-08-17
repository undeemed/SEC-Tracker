#!/bin/bash

# Simple script to run the application using the virtual environment

# Check if the virtual environment exists
if [ ! -d "activate" ]; then
    echo "Virtual environment not found. Please create it first."
    exit 1
fi

# Run the application with the virtual environment's Python
./activate/bin/python run.py "$@"