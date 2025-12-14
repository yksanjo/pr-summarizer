#!/usr/bin/env python3
"""
PR Summarizer

Automatically generates TL;DR summaries of GitHub Pull Requests.
"""

import os
import re
import argparse
from typing import Dict, List, Optional, Tuple
from pathlib import Path

try:
    from github import Github
    GITHUB_AVAILABLE = True
except ImportError:
    GITHUB_AVAILABLE = False

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def get_pr_data(repo_name: str, pr_number: int, github_token: str) -> Dict:
    """Fetch PR data from GitHub API."""
    if not GITHUB_AVAILABLE:
        raise ImportError("PyGithub not installed. Install with: pip install PyGithub")
    
    g = Github(github_token)
    repo = g.get_repo(repo_name)
    pr = repo.get_pull(pr_number)
    
    # Get files changed
    files = []
    for file in pr.get_files():
        files.append({
            "filename": file.filename,
            "status": file.status,
            "additions": file.additions,
            "deletions": file.deletions,
            "patch": file.patch[:500] if file.patch else None  # Limit patch size
        })
    
    # Get commits
    commits = []
    for commit in pr.get_commits():
        commits.append({
            "sha": commit.sha[:7],
            "message": commit.commit.message.split("\n")[0],
            "author": commit.commit.author.name
        })
    
    return {
        "title": pr.title,
        "body": pr.body or "",
        "author": pr.user.login,
        "state": pr.state,
        "created_at": pr.created_at.isoformat(),
        "files": files,
        "commits": commits,
        "additions": pr.additions,
        "deletions": pr.deletions,
        "changed_files": pr.changed_files,
        "base_branch": pr.base.ref,
        "head_branch": pr.head.ref,
        "labels": [label.name for label in pr.labels],
        "reviewers": [r.login for r in pr.requested_reviewers]
    }


def assess_risk_level(files: List[Dict], title: str, body: str) -> Tuple[str, str]:
    """Assess risk level based on files changed and PR content."""
    high_risk_keywords = [
        "auth", "authentication", "security", "password", "token", "credential",
        "payment", "billing", "charge", "transaction",
        "database", "migration", "schema", "sql",
        "config", "environment", "secret", "key"
    ]
    
    medium_risk_keywords = [
        "api", "endpoint", "route", "controller",
        "deploy", "infrastructure", "docker", "kubernetes",
        "test", "testing", "spec"
    ]
    
    content = (title + " " + body).lower()
    filenames = " ".join([f["filename"].lower() for f in files])
    all_content = content + " " + filenames
    
    # Check for high-risk indicators
    high_risk_count = sum(1 for keyword in high_risk_keywords if keyword in all_content)
    medium_risk_count = sum(1 for keyword in medium_risk_keywords if keyword in all_content)
    
    # Check file types
    critical_extensions = [".py", ".js", ".ts", ".java", ".go", ".rb"]
    critical_files = sum(1 for f in files if any(f["filename"].endswith(ext) for ext in critical_extensions))
    
    if high_risk_count > 0 or critical_files > 10:
        risk_level = "High"
        reasoning = f"Touches {high_risk_count} high-risk areas or {critical_files} critical files"
    elif medium_risk_count > 2 or critical_files > 5:
        risk_level = "Medium"
        reasoning = f"Moderate changes affecting {medium_risk_count} areas"
    else:
        risk_level = "Low"
        reasoning = "Limited scope, low-risk changes"
    
    return risk_level, reasoning


def suggest_reviewers(files: List[Dict], repo_name: str, github_token: str) -> List[str]:
    """Suggest reviewers based on file ownership (CODEOWNERS or git blame)."""
    # This is a simplified version - in production, you'd check CODEOWNERS file
    # or use git blame to find frequent contributors
    
    # Group files by directory
    directories = {}
    for file in files:
        dir_path = "/".join(file["filename"].split("/")[:-1])
        if dir_path:
            directories[dir_path] = directories.get(dir_path, 0) + 1
    
    # Simple heuristic: suggest based on file paths
    suggestions = []
    
    # Check for common patterns
    if any("auth" in f["filename"].lower() or "security" in f["filename"].lower() for f in files):
        suggestions.append("security-team")
    
    if any("test" in f["filename"].lower() for f in files):
        suggestions.append("qa-team")
    
    if any("frontend" in f["filename"].lower() or "ui" in f["filename"].lower() for f in files):
        suggestions.append("frontend-team")
    
    if any("backend" in f["filename"].lower() or "api" in f["filename"].lower() for f in files):
        suggestions.append("backend-team")
    
    return suggestions[:3]  # Limit to 3 suggestions


def summarize_with_openai(pr_data: Dict, api_key: Optional[str] = None) -> str:
    """Generate PR summary using OpenAI."""
    if not OPENAI_AVAILABLE:
        raise ImportError("openai package not installed. Install with: pip install openai")
    
    api_key = api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment or provided")
    
    client = OpenAI(api_key=api_key)
    
    # Prepare context
    files_summary = "\n".join([
        f"- {f['filename']} ({f['status']}, +{f['additions']}/-{f['deletions']})"
        for f in pr_data["files"][:20]  # Limit to 20 files
    ])
    
    commits_summary = "\n".join([
        f"- {c['sha']}: {c['message']}"
        for c in pr_data["commits"][:10]  # Limit to 10 commits
    ])
    
    prompt = f"""Analyze this GitHub Pull Request and provide a concise summary:

Title: {pr_data['title']}
Description: {pr_data['body'][:500]}
Author: {pr_data['author']}
Files Changed: {pr_data['changed_files']} files (+{pr_data['additions']}/-{pr_data['deletions']} lines)

Files:
{files_summary}

Commits:
{commits_summary}

Provide a structured summary with:
1. TL;DR (one sentence)
2. Files Changed + Purpose (brief description of what each major file does)
3. Risk Level (Low/Medium/High) with reasoning
4. Suggested Reviewers (based on file ownership/patterns)
5. Key Changes (3-5 bullet points)
6. Testing Notes (what should be tested)

Format as Markdown."""

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that summarizes GitHub Pull Requests for code review."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        
        return response.choices[0].message.content
    except Exception as e:
        raise Exception(f"OpenAI API error: {e}")


def summarize_with_ollama(pr_data: Dict, base_url: str = "http://localhost:11434", model: str = "llama2") -> str:
    """Generate PR summary using Ollama."""
    if not REQUESTS_AVAILABLE:
        raise ImportError("requests package not installed. Install with: pip install requests")
    
    files_summary = "\n".join([
        f"- {f['filename']} ({f['status']}, +{f['additions']}/-{f['deletions']})"
        for f in pr_data["files"][:20]
    ])
    
    commits_summary = "\n".join([
        f"- {c['sha']}: {c['message']}"
        for c in pr_data["commits"][:10]
    ])
    
    prompt = f"""Analyze this GitHub Pull Request and provide a concise summary:

Title: {pr_data['title']}
Description: {pr_data['body'][:500]}
Author: {pr_data['author']}
Files Changed: {pr_data['changed_files']} files (+{pr_data['additions']}/-{pr_data['deletions']} lines)

Files:
{files_summary}

Commits:
{commits_summary}

Provide a structured summary with:
1. TL;DR (one sentence)
2. Files Changed + Purpose (brief description of what each major file does)
3. Risk Level (Low/Medium/High) with reasoning
4. Suggested Reviewers (based on file ownership/patterns)
5. Key Changes (3-5 bullet points)
6. Testing Notes (what should be tested)

Format as Markdown."""

    try:
        response = requests.post(
            f"{base_url}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False
            },
            timeout=120
        )
        response.raise_for_status()
        
        return response.json().get("response", "")
    except Exception as e:
        raise Exception(f"Ollama API error: {e}")


def summarize_with_basic(pr_data: Dict) -> str:
    """Generate basic PR summary without LLM."""
    risk_level, risk_reasoning = assess_risk_level(pr_data["files"], pr_data["title"], pr_data["body"])
    suggested_reviewers = suggest_reviewers(pr_data["files"], "", "")
    
    # Group files by type
    file_types = {}
    for file in pr_data["files"]:
        ext = Path(file["filename"]).suffix or "no extension"
        file_types[ext] = file_types.get(ext, 0) + 1
    
    summary = f"""# PR Summary: {pr_data['title']}

## TL;DR
{pr_data['title']} by @{pr_data['author']} - {pr_data['changed_files']} files changed (+{pr_data['additions']}/-{pr_data['deletions']} lines)

## Files Changed + Purpose
- **Total Files**: {pr_data['changed_files']}
- **Lines Changed**: +{pr_data['additions']} additions, -{pr_data['deletions']} deletions
- **File Types**: {', '.join(f'{ext}: {count}' for ext, count in sorted(file_types.items(), key=lambda x: x[1], reverse=True)[:5])}

### Major Files:
"""
    
    # Show top 10 files by change size
    sorted_files = sorted(pr_data["files"], key=lambda x: x["additions"] + x["deletions"], reverse=True)
    for file in sorted_files[:10]:
        summary += f"- `{file['filename']}` ({file['status']}, +{file['additions']}/-{file['deletions']})\n"
    
    summary += f"""
## Risk Level
**{risk_level}** - {risk_reasoning}

## Suggested Reviewers
"""
    
    if suggested_reviewers:
        for reviewer in suggested_reviewers:
            summary += f"- @{reviewer}\n"
    else:
        summary += "- Review based on file ownership\n"
    
    summary += f"""
## Key Changes
- {pr_data['changed_files']} files modified
- {len(pr_data['commits'])} commits
- Base: `{pr_data['base_branch']}` ← Head: `{pr_data['head_branch']}`
"""
    
    if pr_data["labels"]:
        summary += f"- Labels: {', '.join(pr_data['labels'])}\n"
    
    summary += f"""
## Testing Notes
- Review changes in critical files
- Test affected functionality
- Verify no breaking changes
- Check for proper error handling
"""
    
    return summary


def summarize_pr(repo_name: str, pr_number: int, provider: str = "basic", github_token: Optional[str] = None, **kwargs) -> str:
    """
    Summarize a GitHub Pull Request.
    
    Args:
        repo_name: Repository in format "owner/repo"
        pr_number: Pull request number
        provider: "basic", "openai", or "ollama"
        github_token: GitHub personal access token
        **kwargs: Additional arguments for specific providers
    
    Returns:
        Markdown-formatted PR summary
    """
    github_token = github_token or os.getenv("GITHUB_TOKEN")
    if not github_token:
        raise ValueError("GITHUB_TOKEN not found in environment or provided")
    
    # Fetch PR data
    print(f"Fetching PR #{pr_number} from {repo_name}...")
    pr_data = get_pr_data(repo_name, pr_number, github_token)
    
    # Generate summary
    if provider == "openai":
        print("Generating summary with OpenAI...")
        return summarize_with_openai(pr_data, kwargs.get("api_key"))
    elif provider == "ollama":
        print("Generating summary with Ollama...")
        return summarize_with_ollama(
            pr_data,
            kwargs.get("base_url", "http://localhost:11434"),
            kwargs.get("model", "llama2")
        )
    else:
        print("Generating basic summary...")
        return summarize_with_basic(pr_data)


def main():
    parser = argparse.ArgumentParser(description="Summarize GitHub Pull Requests")
    parser.add_argument("repo", help="Repository in format 'owner/repo'")
    parser.add_argument("pr_number", type=int, help="Pull request number")
    parser.add_argument("--provider", "-p", default="basic", choices=["basic", "openai", "ollama"],
                       help="Summary provider (default: basic)")
    parser.add_argument("--output", "-o", help="Output file path")
    parser.add_argument("--token", "-t", help="GitHub personal access token")
    parser.add_argument("--ollama-url", default="http://localhost:11434",
                       help="Ollama base URL (default: http://localhost:11434)")
    parser.add_argument("--ollama-model", default="llama2",
                       help="Ollama model name (default: llama2)")
    
    args = parser.parse_args()
    
    try:
        kwargs = {}
        if args.provider == "ollama":
            kwargs["base_url"] = args.ollama_url
            kwargs["model"] = args.ollama_model
        
        summary = summarize_pr(
            args.repo,
            args.pr_number,
            provider=args.provider,
            github_token=args.token,
            **kwargs
        )
        
        if args.output:
            with open(args.output, "w") as f:
                f.write(summary)
            print(f"\n✓ Summary saved to {args.output}")
        else:
            print("\n" + "=" * 60)
            print(summary)
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
