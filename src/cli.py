import os
import sys
import argparse
import requests

REPO_OWNER = "astrafy"
REPO_NAME = "astrafy-agent-tools"


def _build_headers(token: str = None) -> dict:
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _fetch_contents(path: str, headers: dict) -> list:
    api_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{path}"
    response = requests.get(api_url, headers=headers)

    if response.status_code == 404:
        print(f"❌ Error: Skill or path '{path}' not found in the repository.")
        sys.exit(1)
    elif response.status_code in (401, 403):
        print("❌ Error: Permission denied or API rate limit exceeded.")
        print(
            "💡 Set the GITHUB_TOKEN environment variable with a personal access token."
        )
        sys.exit(1)

    response.raise_for_status()
    items = response.json()

    if not isinstance(items, list):
        items = [items]
    return items


def collect_remote_files(
    path: str, dest_dir: str, token: str = None
) -> list[tuple[str, str, str]]:
    """
    Recursively queries the GitHub API to collect all files that would be
    downloaded, without actually downloading them.

    Returns a list of (remote_path, local_path, download_url) tuples.
    """
    headers = _build_headers(token)
    items = _fetch_contents(path, headers)
    files = []

    for item in items:
        item_type = item.get("type")
        item_name = item.get("name")
        local_path = os.path.join(dest_dir, item_name)

        if item_type == "dir":
            files.extend(collect_remote_files(item.get("path"), local_path, token))
        elif item_type == "file" and item.get("download_url"):
            files.append((item.get("path"), local_path, item.get("download_url")))

    return files


def download_files(files: list[tuple[str, str, str]], token: str = None):
    """Downloads a pre-collected list of (remote_path, local_path, download_url) tuples."""
    headers = _build_headers(token)

    for remote_path, local_path, download_url in files:
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        print(f"Downloading {remote_path}...")
        file_resp = requests.get(download_url, headers=headers)
        file_resp.raise_for_status()

        with open(local_path, "wb") as f:
            f.write(file_resp.content)


def main():
    parser = argparse.ArgumentParser(
        description=f"Download skills directly from {REPO_OWNER}/{REPO_NAME}"
    )
    parser.add_argument(
        "skill",
        help="The path of the skill/folder in the repository (e.g., 'agents/claude/writing')",
    )
    parser.add_argument(
        "--dest",
        default=".",
        help="The local destination directory (defaults to current directory)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing local files. Without this flag the command fails if any target file already exists.",
    )

    args = parser.parse_args()

    github_token = os.environ.get("GITHUB_TOKEN")

    final_dest = os.path.join(args.dest, args.skill.replace("/", os.sep))

    print(f"🚀 Fetching '{args.skill}' from {REPO_OWNER}/{REPO_NAME}...")
    files = collect_remote_files(args.skill, final_dest, token=github_token)

    if not args.overwrite:
        existing = [local for _, local, _ in files if os.path.exists(local)]
        if existing:
            print("❌ Error: The following files already exist locally:")
            for f in existing:
                print(f"   - {f}")
            print("💡 Use --overwrite to replace existing files.")
            sys.exit(1)

    download_files(files, token=github_token)
    print(f"✅ Successfully downloaded to '{os.path.abspath(final_dest)}'")


if __name__ == "__main__":
    main()
