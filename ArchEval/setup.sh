#!/bin/bash
set -e

echo "================================================="
echo "  Setting up ArchEval Environment"
echo "================================================="

if [ ! -d ".venv" ]; then
    echo "Creating Python virtual environment in .venv..."
    python3 -m venv .venv
fi

echo "Activating virtual environment..."
source .venv/bin/activate

echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "================================================="
echo "Setup complete! You can now run the benchmarks."
echo "================================================="
