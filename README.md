# PR Summarizer

[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/) [![GitHub stars](https://img.shields.io/github/stars/yksanjo/pr-summarizer?style=social)](https://github.com/yksanjo/pr-summarizer/stargazers) [![GitHub forks](https://img.shields.io/github/forks/yksanjo/pr-summarizer.svg)](https://github.com/yksanjo/pr-summarizer/network/members) [![GitHub issues](https://img.shields.io/github/issues/yksanjo/pr-summarizer.svg)](https://github.com/yksanjo/pr-summarizer/issues)
[![Last commit](https://img.shields.io/github/last-commit/yksanjo/pr-summarizer.svg)](https://github.com/yksanjo/pr-summarizer/commits/main)


Automatically generates TL;DR summaries of GitHub Pull Requests to speed up code review.

## Features

- Analyzes PR files, commits, and descriptions
- Generates concise summaries with:
  - Files changed + purpose
  - Risk level assessment
  - Suggested reviewers
- Supports OpenAI and Ollama (local LLM)
- CLI and web interface

## Installation

```bash
pip install -r requirements.txt
```

## Setup

1. Get a GitHub Personal Access Token:
   - Go to GitHub Settings → Developer settings → Personal access tokens
   - Create a token with `repo` scope

2. Set up API keys (create `.env` file):
```env
GITHUB_TOKEN=your_github_token_here
OPENAI_API_KEY=your_openai_key_here  # Optional, for OpenAI provider
OLLAMA_BASE_URL=http://localhost:11434  # Optional, for Ollama provider
```

## Usage

### CLI Mode

```bash
# Summarize a PR
python summarize_pr.py owner/repo 123

# Using OpenAI
python summarize_pr.py owner/repo 123 --provider openai

# Using Ollama (local)
python summarize_pr.py owner/repo 123 --provider ollama

# Save to file
python summarize_pr.py owner/repo 123 --output summary.md
```

### Web Interface

```bash
python app.py
```

Then open http://localhost:5002 in your browser.

### Python API

```python
from summarize_pr import summarize_pr

summary = summarize_pr("owner/repo", 123, provider="openai")
print(summary)
```

## Output Format

The summary includes:
- **TL;DR**: One-line summary
- **Files Changed**: List of modified files with purpose
- **Risk Level**: Low/Medium/High with reasoning
- **Suggested Reviewers**: Based on file ownership
- **Key Changes**: Major modifications
- **Testing Notes**: Suggestions for testing

## License

MIT
