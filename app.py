#!/usr/bin/env python3
"""
Web interface for PR Summarizer
"""

from flask import Flask, render_template_string, request, jsonify
from summarize_pr import summarize_pr
import os

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>PR Summarizer</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            margin-bottom: 30px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #555;
        }
        input[type="text"], select {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
            box-sizing: border-box;
        }
        button {
            background: #007bff;
            color: white;
            padding: 12px 24px;
            border: none;
            border-radius: 4px;
            font-size: 16px;
            cursor: pointer;
            margin-right: 10px;
        }
        button:hover {
            background: #0056b3;
        }
        .summary {
            margin-top: 30px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 4px;
            border: 1px solid #ddd;
        }
        .summary pre {
            white-space: pre-wrap;
            word-wrap: break-word;
            font-family: 'Courier New', monospace;
            font-size: 14px;
            line-height: 1.6;
        }
        .error {
            color: #dc3545;
            padding: 10px;
            background: #f8d7da;
            border-radius: 4px;
            margin-top: 10px;
        }
        .loading {
            display: none;
            text-align: center;
            padding: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 PR Summarizer</h1>
        
        <form id="prForm">
            <div class="form-group">
                <label for="repo">Repository (owner/repo) *</label>
                <input type="text" id="repo" name="repo" required placeholder="e.g., facebook/react">
            </div>
            
            <div class="form-group">
                <label for="prNumber">PR Number *</label>
                <input type="text" id="prNumber" name="prNumber" required placeholder="e.g., 123">
            </div>
            
            <div class="form-group">
                <label for="provider">Provider</label>
                <select id="provider" name="provider">
                    <option value="basic">Basic (Fast, No API)</option>
                    <option value="openai">OpenAI (Accurate)</option>
                    <option value="ollama">Ollama (Local)</option>
                </select>
            </div>
            
            <button type="submit">Summarize PR</button>
        </form>
        
        <div class="loading" id="loading">Fetching PR and generating summary...</div>
        <div id="error"></div>
        
        <div class="summary" id="summary" style="display:none;">
            <h2>Summary</h2>
            <pre id="summaryContent"></pre>
        </div>
    </div>
    
    <script>
        document.getElementById('prForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const repo = document.getElementById('repo').value;
            const prNumber = document.getElementById('prNumber').value;
            const provider = document.getElementById('provider').value;
            const loading = document.getElementById('loading');
            const error = document.getElementById('error');
            const summary = document.getElementById('summary');
            
            loading.style.display = 'block';
            error.innerHTML = '';
            summary.style.display = 'none';
            
            try {
                const response = await fetch('/summarize', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ repo, prNumber: parseInt(prNumber), provider })
                });
                
                const data = await response.json();
                
                if (data.error) {
                    error.innerHTML = `<div class="error">${data.error}</div>`;
                } else {
                    document.getElementById('summaryContent').textContent = data.summary;
                    summary.style.display = 'block';
                }
            } catch (err) {
                error.innerHTML = `<div class="error">Error: ${err.message}</div>`;
            } finally {
                loading.style.display = 'none';
            }
        });
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route("/summarize", methods=["POST"])
def summarize():
    try:
        data = request.json
        repo = data.get("repo", "")
        pr_number = data.get("prNumber")
        provider = data.get("provider", "basic")
        
        if not repo or not pr_number:
            return jsonify({"error": "Repository and PR number are required"}), 400
        
        kwargs = {}
        if provider == "ollama":
            kwargs["base_url"] = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            kwargs["model"] = os.getenv("OLLAMA_MODEL", "llama2")
        
        summary = summarize_pr(repo, pr_number, provider=provider, **kwargs)
        
        return jsonify({"summary": summary})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5002)
