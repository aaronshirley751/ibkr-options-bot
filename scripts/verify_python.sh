#!/bin/bash
# Python Installation Verification Script

echo "=== Python Installation Verification ==="
echo ""

# Test Python availability
echo "Testing Python installation..."

if command -v python &> /dev/null; then
    echo "✓ 'python' command found"
    python --version
    PYTHON_CMD="python"
elif command -v python3 &> /dev/null; then
    echo "✓ 'python3' command found"
    python3 --version
    PYTHON_CMD="python3"
elif command -v py &> /dev/null; then
    echo "✓ 'py' command found (Python Launcher)"
    py --version
    PYTHON_CMD="py"
else
    echo "❌ Python not found in PATH"
    echo ""
    echo "Please install Python from https://python.org/downloads/"
    echo "Make sure to check 'Add Python to PATH' during installation"
    exit 1
fi

echo ""
echo "Testing pip (package manager)..."
if $PYTHON_CMD -m pip --version &> /dev/null; then
    echo "✓ pip is working"
    $PYTHON_CMD -m pip --version
else
    echo "❌ pip not working"
    exit 1
fi

echo ""
echo "Testing virtual environment creation..."
if $PYTHON_CMD -m venv --help &> /dev/null; then
    echo "✓ venv module is available"
else
    echo "❌ venv module not available"
    exit 1
fi

echo ""
echo "=== Python Installation Verified Successfully! ==="
echo "Python command to use: $PYTHON_CMD"
echo ""
echo "Next steps:"
echo "1. Run: $PYTHON_CMD -m venv .venv"
echo "2. Activate: source .venv/Scripts/activate"
echo "3. Install deps: pip install -r requirements.txt -r requirements-dev.txt"
echo "4. Run tests: pytest tests/ -v"
