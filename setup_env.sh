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

