# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This project is a Python-based tool that automatically tracks updates in specified GitHub repositories, summarizes new commits using a Large Language Model (LLM), and posts the summaries as a new GitHub Issue. It is designed to be run as a scheduled GitHub Action and uses GitHub Artifacts to maintain state between runs.

## Project Structure

```
.
├── .github/
│   └── workflows/
│       └── tracker.yml       # GitHub Actions workflow for scheduled execution
├── main.py                   # Main application script
├── config.json               # Configuration file for repositories to track
└── last_commits.json         # State file, passed between runs via Artifacts
```

## Core Components & Workflow

The workflow is orchestrated by `.github/workflows/tracker.yml` and executed by `main.py`.

1.  **Scheduled Trigger**: The GitHub Actions workflow is triggered on a schedule (`cron: '0 1,14 * * *'`) or can be run manually.

2.  **State Restoration**: At the beginning of a run, the workflow downloads the `last-commits` artifact from the previous run. This artifact contains `last_commits.json`, which stores the SHA of the last processed commit for each repository.

3.  **Dependency Installation**: It installs the necessary Python dependency (`requests`).

4.  **Script Execution (`main.py`)**:
    *   The Python script reads `config.json` to get the list of repositories to monitor.
    *   It loads the `last_commits.json` file to know where it left off.
    *   For each repository, it uses the GitHub API to fetch new commits that have occurred since the last recorded SHA.
    *   If new commits are found, their messages are aggregated and sent to a Large Language Model (the VolcEngine Ark API using model `doubao-seed-1-8-251228`) for summarization in Chinese.
    *   If any summaries are generated, the script creates a **single new GitHub Issue** in the repository where the Action is running. The Issue title contains the current date, and the body contains all the generated summaries.
    *   The script then updates the `last_commits.json` file in memory with the new latest commit SHAs.

5.  **State Persistence**: After the script finishes, the workflow uploads the updated `last_commits.json` file as the `last-commits` artifact. This makes it available for the next scheduled run.

## Key Design Choices

*   **Issue-based Notifications**: Instead of emailing or writing to a file, the system creates a GitHub Issue. This leverages GitHub's native notification system (anyone watching the repo gets an email) and creates a clean, searchable history of all summary reports.
*   **Artifacts for State**: The state (`last_commits.json`) is not committed to the repository. This keeps the git history clean from automated updates. Using artifacts is the standard, robust way to pass data between GitHub Actions runs.
*   **No File Commits**: The Action no longer commits files back to the repository, simplifying the workflow and its required permissions.

## Development and Local Testing

1.  **Environment Variables**: To run `main.py` locally, you need to set:
    *   `GITHUB_TOKEN`: A GitHub Personal Access Token with `repo` and `issue:write` scopes.
    *   `ARK_API_KEY`: API key for the LLM provider.
    *   `GITHUB_REPOSITORY`: The owner/repo slug where the script should create the issue (e.g., `your-name/your-repo`).

2.  **Configuration**: Edit `config.json` to list the repositories you want to track.

3.  **Execution**:
    ```bash
    pip install requests
    python main.py
    ```
    *Note: Local execution will read `last_commits.json` from the local disk and save it back there. It does not interact with GitHub Artifacts.*
