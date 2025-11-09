"""GitHub API client for fetching pull requests."""

from typing import List, Optional
from datetime import datetime
from dataclasses import dataclass

from github import Github, PullRequest as GHPullRequest
from github.PaginatedList import PaginatedList

from .config import Config


@dataclass
class PullRequest:
    """Simplified pull request data."""
    number: int
    title: str
    body: Optional[str]
    url: str
    author: str
    repo: str
    labels: List[str]
    merged_at: Optional[datetime]
    created_at: datetime
    state: str

    @classmethod
    def from_github_pr(cls, pr: GHPullRequest, repo_name: str) -> 'PullRequest':
        """Convert GitHub PR object to our simplified format."""
        return cls(
            number=pr.number,
            title=pr.title,
            body=pr.body,
            url=pr.html_url,
            author=pr.user.login if pr.user else "unknown",
            repo=repo_name,
            labels=[label.name for label in pr.labels],
            merged_at=pr.merged_at,
            created_at=pr.created_at,
            state="merged" if pr.merged else pr.state
        )


class GitHubClient:
    """Client for interacting with GitHub API."""

    def __init__(self, config: Config):
        """Initialize GitHub client."""
        self.config = config
        self.client = Github(config.github.token)

    def fetch_pull_requests(self) -> List[PullRequest]:
        """Fetch pull requests from all configured repositories."""
        all_prs = []

        for repo_name in self.config.github.repositories:
            try:
                repo = self.client.get_repo(repo_name)
                prs = self._fetch_repo_prs(repo, repo_name)
                all_prs.extend(prs)
            except Exception as e:
                print(f"Warning: Failed to fetch PRs from {repo_name}: {e}")
                continue

        return all_prs

    def _fetch_repo_prs(self, repo, repo_name: str) -> List[PullRequest]:
        """Fetch PRs from a single repository."""
        prs = []
        since_date = self.config.filters.get_since_date()

        # Determine which states to query
        states_to_query = set(self.config.filters.states)
        if "all" in states_to_query:
            query_states = ["open", "closed"]
        elif "merged" in states_to_query:
            # Need to query closed PRs and filter for merged
            query_states = ["closed"]
            if "open" in states_to_query:
                query_states.append("open")
            if "closed" in states_to_query:
                # Already included
                pass
        else:
            query_states = list(states_to_query)

        for state in query_states:
            gh_prs = repo.get_pulls(
                state=state,
                sort="updated",
                direction="desc"
            )

            for gh_pr in gh_prs:
                # Check date filter
                if since_date:
                    pr_date = gh_pr.merged_at if gh_pr.merged else gh_pr.created_at
                    if pr_date and pr_date < since_date:
                        # Since we're sorted by update time, we can break early
                        break

                pr = PullRequest.from_github_pr(gh_pr, repo_name)

                # Filter by state (handle merged separately)
                if "merged" in states_to_query and pr.state == "merged":
                    pass  # Include merged PRs
                elif pr.state not in states_to_query and "all" not in states_to_query:
                    continue

                # Filter by labels if specified
                if self.config.filters.labels:
                    if not any(label in pr.labels for label in self.config.filters.labels):
                        continue

                prs.append(pr)

        return prs

    def close(self):
        """Close the GitHub client."""
        self.client.close()
