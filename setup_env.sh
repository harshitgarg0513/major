#!/usr/bin/env bash
# This script sets up a local Python virtual environment to resolve IDE errors on Mac/Windows.
# It does NOT install Mininet's system dependencies (which require Linux).

echo "Creating virtual environment..."
python3 -m venv venv

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing requirements..."
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "================================================================"
echo "Done! To fix your IDE errors:"
echo "1. Select the Python interpreter inside the 'venv' folder in VSCode/PyCharm."
echo "2. Run 'source venv/bin/activate' before running any local tests."
echo "================================================================"
