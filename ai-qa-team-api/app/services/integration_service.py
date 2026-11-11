import httpx
from fastapi import HTTPException
import os
import tempfile
import subprocess
import glob
import re
from app.db.connection import db

PLAYWRIGHT_PATTERNS = ["*.spec.ts", "*.test.ts", "*.spec.js", "*.test.js"]


async def fetch_github_repos(access_token: str):
    headers = {"Authorization": f"Bearer {access_token}"}

    async with httpx.AsyncClient() as client:
        res = await client.get("https://api.github.com/user/repos", headers=headers)

    if res.status_code != 200:
        raise HTTPException(400, f"GitHub API error: {res.text}")

    repos = res.json()
    return [
        {
            "id": r["id"],
            "name": r["name"],
            "full_name": r["full_name"],
            "private": r["private"],
            "url": r["clone_url"],
            "default_branch": r["default_branch"],
        }
        for r in repos
    ]


async def fetch_gitlab_repos(access_token: str):
    headers = {"Authorization": f"Bearer {access_token}"}

    async with httpx.AsyncClient() as client:
        res = await client.get("https://gitlab.com/api/v4/projects?membership=true", headers=headers)

    if res.status_code != 200:
        raise HTTPException(400, f"GitLab API error: {res.text}")

    repos = res.json()
    return [
        {
            "id": r["id"],
            "name": r["name"],
            "full_name": r["path_with_namespace"],
            "private": not r["public"],
            "url": r["http_url_to_repo"],
            "default_branch": r["default_branch"],
        }
        for r in repos
    ]

async def fetch_bitbucket_repos(access_token: str):
    headers = {"Authorization": f"Bearer {access_token}"}

    async with httpx.AsyncClient() as client:
        res = await client.get("https://api.bitbucket.org/2.0/repositories?role=member", headers=headers)

    if res.status_code != 200:
        raise HTTPException(400, f"Bitbucket API error: {res.text}")

    data = res.json()
    repos = data.get("values", [])

    return [
        {
            "id": r["uuid"],
            "name": r["name"],
            "full_name": r["full_name"],
            "private": r["is_private"],
            "url": r["links"]["clone"][0]["href"],
            "default_branch": r.get("mainbranch", {}).get("name", "main"),
        }
        for r in repos
    ]

async def clone_repo(repo_url, branch, access_token, provider):
    temp_dir = tempfile.mkdtemp()

    if provider == "github":
        # Insert token for authenticated clone
        token_url = repo_url.replace("https://", f"https://{access_token}:x-oauth-basic@")
    else:
        # fallback: anonymous clone
        token_url = repo_url

    cmd = ["git", "clone", "--branch", branch, token_url, temp_dir]

    subprocess.run(cmd, check=True)

    return temp_dir

def find_playwright_tests(path):
    tests = []
    for pattern in PLAYWRIGHT_PATTERNS:
        tests.extend(glob.glob(os.path.join(path, "**", pattern), recursive=True))
    return tests

def parse_playwright_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Extract describe title as Story
    story_match = re.search(r'describe\(["\'](.+?)["\']', content)
    story = story_match.group(1) if story_match else "Untitled Story"

    # Extract test() titles as scenarios
    scenarios = re.findall(r'test(?:\.only|\.skip)?\(["\'](.+?)["\']', content)

    return story, scenarios

async def import_playwright_tests(repo_url, branch, access_token, project_id, provider):
    temp_dir = await clone_repo(repo_url, branch, access_token, provider)
    test_files = find_playwright_tests(temp_dir)

    created = {"stories": 0, "scenarios": 0, "testcases": 0}

    for file in test_files:
        story_title, scenarios = parse_playwright_file(file)

        story_doc = {
            "project_id": project_id,
            "title": story_title,
        }
        story_res = await db["stories"].insert_one(story_doc)
        story_id = str(story_res.inserted_id)
        created["stories"] += 1

        for scenario_title in scenarios:
            sc_doc = {
                "project_id": project_id,
                "story_id": story_id,
                "title": scenario_title,
                "complexity": "medium",
                "approved": False
            }
            sc_res = await db["scenarios"].insert_one(sc_doc)
            scenario_id = str(sc_res.inserted_id)
            created["scenarios"] += 1

            tc_doc = {
                "project_id": project_id,
                "scenario_id": scenario_id,
                "title": scenario_title,
                "complexity": "medium",
            }
            await db["testcases"].insert_one(tc_doc)
            created["testcases"] += 1

    return created
