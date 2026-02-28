
import os
import json
import requests
from datetime import datetime

# --- Configuration ---
CONFIG_FILE = 'config.json'
LAST_COMMITS_FILE = 'last_commits.json'
SUMMARY_FILE = 'summaries.md'
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')
ARK_API_KEY = os.environ.get('ARK_API_KEY')
# Corrected API URL based on the new example
ARK_API_URL = "https://ark.cn-beijing.volces.com/api/v3/responses"

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
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        all_commits = response.json()
        new_commits = []
        for commit in all_commits:
            if commit['sha'] == last_commit_sha:
                break
            new_commits.append(commit)
        return list(reversed(new_commits))
    else:
        params['per_page'] = 1
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()

def summarize_commits_with_llm(commit_messages):
    """Summarizes commit messages using the corrected VolcEngine Ark API."""
    if not ARK_API_KEY:
        print("Error: ARK_API_KEY not set. Check your repository's secrets.")
        return "Could not summarize commits: API key is missing."

    messages_str = "\n".join(f"- {msg}" for msg in commit_messages)
    user_prompt = f"""
    请用中文总结以下 Git commit 信息的核心功能变动、修复和主要更新。
    要求总结内容精炼、清晰、易于理解。

    Commit Messages:
    {messages_str}

    总结:
    """

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {ARK_API_KEY}'
    }
    data = {
        "model": "doubao-seed-1-8-251228",
        "input": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": user_prompt
                    }
                ]
            }
        ]
    }

    try:
        response = requests.post(ARK_API_URL, headers=headers, json=data)
        response.raise_for_status()
        response_data = response.json()

        # --- Final fix for response parsing ---
        output_list = response_data.get('output', [])
        for item in output_list:
            if item.get('type') == 'message' and item.get('role') == 'assistant':
                content_list = item.get('content', [])
                for content_item in content_list:
                    if content_item.get('type') == 'output_text':
                        summary = content_item.get('text', '')
                        return summary.strip()

        # If summary is not found, print debug info and return an error
        print("--- Unexpected API Response: Could not find summary text ---")
        print(json.dumps(response_data, indent=2, ensure_ascii=False))
        print("----------------------------------------------------------")
        error_info = response_data.get('error', {'message': 'Summary not found in response structure'})
        return f"Could not extract summary from Ark API response: {error_info.get('message')}"

    except requests.exceptions.RequestException as e:
        print(f"Error calling VolcEngine Ark API: {e}")
        if e.response is not None:
            print(f"Response body: {e.response.text}")
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

            latest_commit_sha = new_commits[-1]['sha']
            last_commits[repo] = latest_commit_sha
            print(f"Updated last commit for {repo} to {latest_commit_sha[:7]}")

        except requests.exceptions.HTTPError as e:
            print(f"Error accessing GitHub API for {repo}: {e}")
        except Exception as e:
            print(f"An unexpected error occurred for {repo}: {e}")

    if changes_made:
        save_json(LAST_COMMITS_FILE, last_commits)
        if 'GITHUB_OUTPUT' in os.environ:
            with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
                f.write('changes_made=true\n')

    print("\nUpdate check finished.")


if __name__ == "__main__":
    main()
