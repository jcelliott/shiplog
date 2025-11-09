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
        """Fetch PRs from a single repository using GitHub Search API."""
        prs = []
        since_date = self.config.filters.get_since_date()

        # Build search queries for different states
        states_to_query = set(self.config.filters.states)
        queries = self._build_search_queries(repo_name, since_date, states_to_query)

        # Execute each search query
        for query in queries:
            try:
                results = self.client.search_issues(query=query)

                for issue in results:
                    # Convert Issue object to PullRequest
                    # Note: GitHub's search returns Issue objects, but PRs are issues
                    if not issue.pull_request:
                        continue

                    # Fetch the full PR object to get all details
                    gh_pr = repo.get_pull(issue.number)
                    pr = PullRequest.from_github_pr(gh_pr, repo_name)

                    # Filter by labels if specified (not in search query)
                    if self.config.filters.labels:
                        if not any(label in pr.labels for label in self.config.filters.labels):
                            continue

                    prs.append(pr)
            except Exception as e:
                print(f"Warning: Search query failed for {repo_name}: {e}")
                continue

        # Remove duplicates (in case a PR matches multiple queries)
        seen = set()
        unique_prs = []
        for pr in prs:
            if pr.number not in seen:
                seen.add(pr.number)
                unique_prs.append(pr)

        return unique_prs

    def _build_search_queries(self, repo_name: str, since_date: Optional[datetime], states: set) -> List[str]:
        """Build GitHub search queries based on filters."""
        queries = []

        # Format date for search query (ISO 8601 format with timezone)
        # GitHub requires timezone info, so we use isoformat() which includes it
        date_str = since_date.isoformat() if since_date else None

        # Base query parts
        base = f"repo:{repo_name} is:pr"

        # Handle different state combinations
        if "all" in states:
            # Search for all PRs (open and closed)
            if date_str:
                # Use created date for all PRs
                queries.append(f"{base} created:>={date_str}")
            else:
                queries.append(base)
        else:
            # Handle each state separately
            if "merged" in states:
                # Merged PRs - use merged date
                if date_str:
                    queries.append(f"{base} is:merged merged:>={date_str}")
                else:
                    queries.append(f"{base} is:merged")

            if "open" in states:
                # Open PRs - use created date
                if date_str:
                    queries.append(f"{base} is:open created:>={date_str}")
                else:
                    queries.append(f"{base} is:open")

            if "closed" in states and "merged" not in states:
                # Closed but not merged PRs - use closed date
                if date_str:
                    queries.append(f"{base} is:closed is:unmerged closed:>={date_str}")
                else:
                    queries.append(f"{base} is:closed is:unmerged")

        return queries

    def close(self):
        """Close the GitHub client."""
        self.client.close()
