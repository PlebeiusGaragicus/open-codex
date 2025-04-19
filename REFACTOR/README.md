# Open Codex CLI (Ollama Edition)

A Python-based refactor of the Open Codex CLI that uses Ollama for local LLM execution. This version focuses on self-hosted AI, running entirely on your local machine without requiring any external API keys.

## Project Goals

This refactor aims to:
1. Convert the existing Node.js-based CLI to Python
2. Replace OpenAI/cloud dependencies with Ollama for local execution
3. Maintain the same user experience and features while being fully self-hosted
4. Keep the same security model and permissions system
5. Optimize for local LLM performance and resource usage

## Project Structure

```
REFACTOR/
├── src/                    # Source code directory
│   ├── cli/               # CLI-related code
│   ├── core/              # Core functionality
│   ├── security/          # Security and sandboxing
│   └── utils/             # Utility functions
├── tests/                 # Test directory
├── docs/                  # Documentation
└── requirements.txt       # Python dependencies
```

## Development Status

🚧 **Currently in Planning Phase** 🚧

- [x] Initial project structure
- [ ] Core functionality migration
- [ ] CLI interface implementation
- [ ] Security model implementation
- [ ] Testing suite setup
- [ ] Documentation

## Prerequisites

1. Install Ollama from [ollama.ai](https://ollama.ai)
2. Pull the required models:
```bash
ollama pull qwen2.5-coder:7b-instruct-q8_0  # For interactive coding
ollama pull llama3.1:8b    # For full context analysis
```

## Installation

```bash
pip install open-codex
```

## Development Setup (Coming Soon)

```bash
# Clone the repository
git clone <repository-url>
cd open-codex/REFACTOR

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Contributing

This project is under active development. Contribution guidelines will be added soon.

## License

This project is licensed under the Apache-2.0 License - see the LICENSE file for details.
