from langchain.tools import tool
from github import Github
import os, subprocess

@tool
def create_hotfix_pr(repo_name: str, branch_name: str, file_path: str, new_content: str, pr_title: str, pr_body: str) -> str:
    """Create a GitHub Pull Request with a hotfix patch from the GitOps agent."""
    g = Github(os.getenv("GITHUB_TOKEN"))
    repo = g.get_repo(repo_name)
    main_branch = repo.get_branch("main")
    try:
        repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=main_branch.commit.sha)
    except Exception:
        pass  # branch already exists
    contents = repo.get_contents(file_path, ref="main")
    repo.update_file(
        path=file_path, message=f"fix: automated hotfix - {pr_title}",
        content=new_content, sha=contents.sha, branch=branch_name
    )
    pr = repo.create_pull(title=pr_title, body=pr_body, head=branch_name, base="main")
    return f"PR created: {pr.html_url}"

gitops_tools = [create_hotfix_pr]
