
import os
import json
import requests
from datetime import datetime

# --- Configuration ---
CONFIG_FILE = 'config.json'
LAST_COMMITS_FILE = 'last_commits.json'
SUMMARY_FILE = 'summaries.md'
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_API_KEY}"


# --- Helper Functions ---

def load_json(file_path):
    """Loads a JSON file with a default value."""
    if not os.path.exists(file_path):
        return {}
    with open(file_path, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_json(file_path, data):
    """Saves data to a JSON file."""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def append_to_summary_file(repo_name, summary):
    """Appends a new summary to the markdown file."""
    timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
    with open(SUMMARY_FILE, 'a', encoding='utf-8') as f:
        f.write(f"## {repo_name} - {timestamp}\n\n")
        f.write(f"{summary}\n\n")
        f.write("---\n\n")
    print(f"Appended summary for {repo_name} to {SUMMARY_FILE}")

def get_new_commits(repo, last_commit_sha):
    """Fetches new commits from a GitHub repository."""
    owner, repo_name = repo.split('/')
    url = f"https://api.github.com/repos/{owner}/{repo_name}/commits"
    headers = {'Authorization': f'token {GITHUB_TOKEN}'}
    params = {}
    if last_commit_sha:
        # We fetch recent commits and filter them until we find the last known SHA.
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        all_commits = response.json()
        new_commits = []
        for commit in all_commits:
            if commit['sha'] == last_commit_sha:
                break
            new_commits.append(commit)
        return list(reversed(new_commits))  # Chronological order
    else:
        # First time, get the most recent commit
        params['per_page'] = 1
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()

def summarize_commits_with_llm(commit_messages):
    """Summarizes commit messages using Google Gemini API."""
    if not GEMINI_API_KEY:
        print("Error: GEMINI_API_KEY not set.")
        return "Could not summarize commits: API key is missing."

    messages_str = "\n".join(f"- {msg}" for msg in commit_messages)
    prompt = f"""
    Please summarize the following commit messages in Chinese. Focus on the key features, fixes, and changes.
    Keep the summary concise and easy to understand.

    Commit messages:
    {messages_str}

    Summary:
    """

    headers = {
        'Content-Type': 'application/json'
    }
    data = {
        "contents": [{
            "parts": [{
                "text": prompt
            }]
        }]
    }

    try:
        response = requests.post(GEMINI_API_URL, headers=headers, json=data)
        response.raise_for_status()
        response_data = response.json()

        # Safely extract the text from the response
        candidates = response_data.get('candidates', [])
        if not candidates or 'content' not in candidates[0] or 'parts' not in candidates[0]['content']:
            # Handle cases where the response is blocked or has an unexpected format
            finish_reason = candidates[0].get('finishReason', 'UNKNOWN')
            if finish_reason == 'SAFETY':
                 return "Summary generation was blocked for safety reasons."
            return f"Could not extract summary from Gemini API response. Finish Reason: {finish_reason}"

        summary = candidates[0]['content']['parts'][0]['text']
        return summary
    except requests.exceptions.RequestException as e:
        print(f"Error calling Google Gemini API: {e}")
        return f"Error during summarization: {e}"

# --- Main Logic ---

def main():
    """Main function to run the update tracker."""
    print("Starting GitHub repository update check...")
    config = load_json(CONFIG_FILE)
    last_commits = load_json(LAST_COMMITS_FILE)

    repositories = config.get('repositories', [])

    if not repositories:
        print("No repositories configured. Exiting.")
        return

    # Track if any file was changed
    changes_made = False

    for repo in repositories:
        print(f"\n--- Checking repository: {repo} ---")
        last_commit_sha = last_commits.get(repo)

        try:
            new_commits = get_new_commits(repo, last_commit_sha)

            if not new_commits:
                print("No new commits since last check.")
                continue

            print(f"Found {len(new_commits)} new commit(s).")
            changes_made = True

            commit_messages = [c['commit']['message'] for c in new_commits]

            summary = summarize_commits_with_llm(commit_messages)

            append_to_summary_file(repo, summary)

            # Update last commit SHA
            latest_commit_sha = new_commits[-1]['sha']
            last_commits[repo] = latest_commit_sha
            print(f"Updated last commit for {repo} to {latest_commit_sha[:7]}")

        except requests.exceptions.HTTPError as e:
            print(f"Error accessing GitHub API for {repo}: {e}")
        except Exception as e:
            print(f"An unexpected error occurred for {repo}: {e}")

    if changes_made:
        save_json(LAST_COMMITS_FILE, last_commits)
        # Set an output for the GitHub Action to know if there were changes
        if 'GITHUB_OUTPUT' in os.environ:
            with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
                f.write('changes_made=true\n')

    print("\nUpdate check finished.")


if __name__ == "__main__":
    main()
