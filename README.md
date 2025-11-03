# OllamaCode

An autonomous agentic coding assistant powered by Ollama with native tool calling. Similar to OpenCode or Claude Code, but using local LLMs through Ollama. Works completely offline and respects your privacy.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## Features

- 🤖 **Autonomous Agentic Coding** - Works independently to complete tasks without constant supervision
- 🛠️ **Native Ollama Tool Calling** - Uses Ollama's built-in tool calling capabilities for structured function execution
- 📁 **File Operations** - Read, write, create, delete files and directories
- 💻 **Terminal Commands** - Execute shell commands (cd, ls, git, npm, pip, etc.)
- 🌐 **Web Search** - Search the internet using DuckDuckGo (no API keys required)
- 🌍 **Browser Automation** - Control Chrome/Selenium for web interactions and scraping
- 💬 **Beautiful Terminal UI** - Rich library-based interface with syntax highlighting
- 🔒 **Privacy-First** - All processing happens locally, no data sent to external services
- 🚀 **Fast & Efficient** - Uses local LLM inference, works offline

## Prerequisites

- **Python 3.8+** (`python3`)
- **Ollama** - [Install from ollama.ai](https://ollama.ai)
- **Chrome/Chromium** and ChromeDriver (optional, for browser automation)
  - Arch Linux: `sudo pacman -S chromium chromium-driver`
  - Ubuntu/Debian: `sudo apt-get install chromium-browser chromium-chromedriver`
  - macOS: `brew install chromium chromedriver`

## Installation

### Option 1: Using the Setup Script (Recommended)

```bash
git clone https://github.com/r3dg0d/ollamacode.git
cd ollamacode
chmod +x setup.sh
./setup.sh
```

The setup script will:
- Create a Python virtual environment
- Install all dependencies
- Check for Ollama installation
- Optionally pull the default model
- Create a launcher script

### Option 2: Manual Installation

```bash
git clone https://github.com/r3dg0d/ollamacode.git
cd ollamacode

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Make launcher executable
chmod +x ollamacode
```

### Option 3: Install from AUR (Arch Linux)

```bash
# Using yay
yay -S ollamacode

# Using paru
paru -S ollamacode

# Or manually
git clone https://aur.archlinux.org/ollamacode.git
cd ollamacode
makepkg -si
```

## Quick Start

### Make it Available from Anywhere

Add to your PATH:

```bash
echo 'export PATH="$PATH:$HOME/Documents/ollamacode"' >> ~/.bashrc
source ~/.bashrc
```

Or create a symlink:

```bash
ln -s ~/Documents/ollamacode/ollamacode ~/.local/bin/ollamacode
```

### Ensure Ollama is Running

```bash
# Start Ollama (if not already running)
ollama serve

# Pull the recommended model (if not already installed)
ollama pull huihui_ai/qwen3-abliterated:32b
```

**Note:** You can use any Ollama model that supports tool calling. Check [Ollama's model library](https://ollama.ai/library) for compatible models.

### Run OllamaCode

**Interactive Mode:**
```bash
ollamacode
# or
python main.py
```

**Autonomous Mode:**
```bash
ollamacode --task "Create a Python script that prints 'Hello World'"
# or
python main.py --task "Create a new React project with TypeScript"
```

## Usage

### Command-Line Options

```bash
ollamacode [OPTIONS]

Options:
  --model MODEL          Ollama model to use 
                         (default: huihui_ai/qwen3-abliterated:32b)
  
  --endpoint URL         Ollama API endpoint 
                         (default: http://127.0.0.1:11434)
  
  --base-dir PATH        Base directory for file operations 
                         (default: ~/Documents)
  
  --task TASK            Initial task to execute (autonomous mode)
```

### Examples

#### Create a New Project

```bash
ollamacode --task "Create a new Python project called 'myapp' with a main.py file and a requirements.txt"
```

#### Search and Learn

```bash
ollamacode --task "Search for information about Python decorators and create a file with examples"
```

#### Web Automation

```bash
ollamacode --task "Open a browser, navigate to example.com, and save the page HTML to a file"
```

#### Interactive Session

```bash
ollamacode
# Then type your tasks interactively
Task: Create a Flask REST API with endpoints for users
Task: Add authentication middleware
Task: Write unit tests
```

## Available Tools

The assistant has access to these tools:

### File Operations
- `read_file(filepath)` - Read file contents
- `write_file(filepath, content)` - Write to a file (creates parent directories)
- `create_directory(dirpath)` - Create directories
- `list_directory(dirpath)` - List directory contents
- `delete_file(filepath)` - Delete a file
- `delete_directory(dirpath, recursive)` - Delete directories

### Terminal Operations
- `run_command(command, cwd)` - Execute shell commands (cd, ls, git, npm, pip, etc.)

### Web Operations
- `web_search(query, max_results)` - Search the web using DuckDuckGo
- `open_browser(headless)` - Open Chrome browser
- `navigate_to(url)` - Navigate to URL
- `browser_click(selector, by)` - Click element
- `browser_type(selector, text, by)` - Type text
- `browser_get_text(selector, by)` - Get element text
- `browser_get_html()` - Get page HTML
- `close_browser()` - Close browser

## How It Works

1. **You provide a task or question** - Either interactively or via command-line
2. **The assistant uses Ollama with tool calling** - Plans and executes actions autonomously
3. **Tools are executed automatically** - File operations, commands, web searches, etc.
4. **Results are fed back to the model** - The model processes results and continues
5. **The process continues until the task is complete** - Up to 50 iterations per task

## Configuration

### Changing the Default Model

Edit `main.py` or pass via command-line:

```bash
ollamacode --model llama3.2:3b --task "your task"
```

### Changing the Base Directory

```bash
ollamacode --base-dir ~/Projects --task "create a new project"
```

### Changing the Ollama Endpoint

If Ollama is running on a different host/port:

```bash
ollamacode --endpoint http://192.168.1.100:11434 --task "your task"
```

## Troubleshooting

### Ollama Connection Issues

**Problem:** `Failed to connect to Ollama at http://127.0.0.1:11434`

**Solution:**
```bash
# Make sure Ollama is running
ollama serve

# Check if Ollama is accessible
curl http://127.0.0.1:11434/api/tags
```

### Browser Automation Not Working

**Problem:** Selenium/Chrome errors when using browser tools

**Solution:**
```bash
# Install Chrome/Chromium and ChromeDriver
# Arch Linux
sudo pacman -S chromium chromium-driver

# Ubuntu/Debian
sudo apt-get install chromium-browser chromium-chromedriver

# macOS
brew install chromium chromedriver
```

### Model Not Found

**Problem:** `Error: model not found`

**Solution:**
```bash
# Pull the model
ollama pull huihui_ai/qwen3-abliterated:32b

# Or use a different model
ollamacode --model llama3.2:3b --task "your task"
```

### Permission Errors

**Problem:** Permission denied when accessing files/directories

**Solution:**
- Check file/directory permissions in the base directory
- Ensure the base directory path is correct
- Use absolute paths if relative paths fail

### Virtual Environment Issues

**Problem:** Module not found errors

**Solution:**
```bash
# Make sure virtual environment is activated
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate  # Windows

# Reinstall dependencies
pip install -r requirements.txt
```

## Project Structure

```
ollamacode/
├── main.py              # Main entry point
├── ollama_client.py     # Ollama API client with tool calling
├── tools.py             # Tool implementations (file ops, terminal, web)
├── ui.py                # Terminal UI using Rich library
├── ollamacode           # Launcher script (bash)
├── setup.sh             # Setup script
├── requirements.txt     # Python dependencies
├── README.md            # This file
├── PKGBUILD             # AUR package build file
└── LICENSE              # MIT License
```

## Development

### Running in Development Mode

```bash
# Activate virtual environment
source venv/bin/activate

# Run directly with Python
python main.py

# Or use the launcher
./ollamacode
```

### Adding New Tools

1. Add tool implementation to `tools.py` in the `ToolRegistry` class
2. Add tool definition to `get_tool_definitions()` method
3. Tools are automatically available to the LLM

### Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Supported Models

OllamaCode works with any Ollama model that supports tool calling. Recommended models:

- `huihui_ai/qwen3-abliterated:32b` - Default, excellent coding capabilities
- `llama3.2:3b` - Lightweight, fast
- `codellama:7b` - Code-specialized model
- `deepseek-coder:6.7b` - Strong coding model

Check [Ollama's model library](https://ollama.ai/library) for more options.

## Security & Privacy

- **100% Local** - All processing happens on your machine
- **No Data Collection** - No telemetry, no analytics, no external requests (except web search)
- **No API Keys Required** - Uses local Ollama instance
- **File System Access** - Be careful with commands, the assistant can read/write files

⚠️ **Warning:** This tool can execute arbitrary shell commands and modify your file system. Only use with trusted models and tasks.

## License

MIT License - see [LICENSE](LICENSE) file for details

## Acknowledgments

- [Ollama](https://ollama.ai) - Amazing local LLM runtime
- [Rich](https://github.com/Textualize/rich) - Beautiful terminal UI
- [Selenium](https://www.selenium.dev/) - Browser automation
- [DuckDuckGo Search](https://github.com/deedy5/duckduckgo_search) - Web search

## Support

- **Issues:** [GitHub Issues](https://github.com/r3dg0d/ollamacode/issues)
- **Discussions:** [GitHub Discussions](https://github.com/r3dg0d/ollamacode/discussions)

---

Made with ❤️ by [r3dg0d](https://github.com/r3dg0d)
