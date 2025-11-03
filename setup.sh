#!/bin/bash
# Setup script for OllamaCode

echo "🚀 Setting up OllamaCode..."

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment and install dependencies
echo "📦 Installing Python dependencies in virtual environment..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
deactivate

echo "✅ Virtual environment created and dependencies installed"

# Check for Ollama
if ! command -v ollama &> /dev/null; then
    echo "⚠️  Ollama is not installed. Please install it from https://ollama.ai"
else
    echo "✅ Ollama found"
    # Check if model exists
    if ollama list | grep -q "huihui_ai/qwen3-abliterated:32b"; then
        echo "✅ Model 'huihui_ai/qwen3-abliterated:32b' found"
    else
        echo "📥 Model 'huihui_ai/qwen3-abliterated:32b' not found. Pulling..."
        ollama pull huihui_ai/qwen3-abliterated:32b
    fi
fi

# Check for Chrome/Chromium
if command -v chromium &> /dev/null || command -v google-chrome &> /dev/null; then
    echo "✅ Chrome/Chromium found"
else
    echo "⚠️  Chrome/Chromium not found. Browser automation will not work."
fi

# Make scripts executable
chmod +x main.py ollamacode

echo "✅ Setup complete!"
echo ""
echo "To use from anywhere, add to your PATH:"
echo "  echo 'export PATH=\"\$PATH:$SCRIPT_DIR\"' >> ~/.bashrc"
echo "  source ~/.bashrc"
echo ""
echo "Or create a symlink:"
echo "  ln -s $SCRIPT_DIR/ollamacode ~/.local/bin/ollamacode"
echo ""
echo "Usage:"
echo "  ollamacode                        # Interactive mode"
echo "  ollamacode --task 'your task'     # Autonomous mode"
echo "  ./ollamacode                      # Or run from this directory"

