"""Changelog formatting utilities."""

from typing import List, Dict
from collections import defaultdict

from .config import Config
from .github_client import PullRequest
from .categorizer import PRClassification


class ChangelogFormatter:
    """Format pull requests into a changelog grouped by categories."""

    def __init__(self, config: Config):
        """Initialize formatter with configuration."""
        self.config = config

    def format(self, prs: List[PullRequest], categorization: Dict[str, PRClassification]) -> str:
        """Format pull requests into a changelog.

        Args:
            prs: List of pull requests to format
            categorization: Mapping of PR number (as string) to PRClassification

        Returns:
            Formatted changelog as markdown string
        """
        if not prs:
            return "No pull requests found matching the criteria."

        # Build the changelog
        lines = []
        lines.append("# Changelog")
        lines.append("")

        # Add summary
        total_prs = len(prs)
        repo_count = len(set(pr.repo for pr in prs))
        lines.append(f"**{total_prs} pull request{'s' if total_prs != 1 else ''} across {repo_count} repositor{'ies' if repo_count != 1 else 'y'}**")
        lines.append("")

        if self.config.output.skip_categorization:
            # Flat list without category headers
            sorted_prs = sorted(prs, key=lambda pr: (pr.repo, -pr.number))
            for pr in sorted_prs:
                lines.append(self._format_pr(pr, categorization))
            lines.append("")
        else:
            # Group PRs by category
            categorized = self._group_by_category(prs, categorization)

            # Add each category in the order defined in config
            for category in self.config.output.categories:
                if category not in categorized or not categorized[category]:
                    continue

                lines.append(f"**{category}**")
                lines.append("")

                # Sort PRs by repo, then by PR number
                category_prs = categorized[category]
                category_prs.sort(key=lambda pr: (pr.repo, -pr.number))

                for pr in category_prs:
                    lines.append(self._format_pr(pr, categorization))

                lines.append("")

        return "\n".join(lines)

    def _group_by_category(self, prs: List[PullRequest], categorization: Dict[str, PRClassification]) -> Dict[str, List[PullRequest]]:
        """Group PRs by their assigned categories."""
        categorized = defaultdict(list)

        for pr in prs:
            pr_key = str(pr.number)
            classification = categorization.get(pr_key)
            if classification:
                category = classification.category
            else:
                category = self.config.output.categories[0]
            categorized[category].append(pr)

        return dict(categorized)

    def _format_pr(self, pr: PullRequest, categorization: Dict[str, PRClassification]) -> str:
        """Format a single PR into a changelog entry."""
        parts = []

        # Get the summary (AI-generated or original title)
        pr_key = str(pr.number)
        classification = categorization.get(pr_key)
        summary = classification.summary if classification else pr.title

        # PR summary/title
        parts.append(f"- **{summary}**")

        # Repository name
        parts.append(f"(`{pr.repo}`)")

        # PR number with link
        if self.config.output.show_pr_number:
            parts.append(f"[#{pr.number}]({pr.url})")

        # Author
        if self.config.output.show_author:
            slack_users = self.config.output.slack_users
            display_name = slack_users.get(pr.author, pr.author) if slack_users else pr.author
            parts.append(f"by @{display_name}")

        return " ".join(parts)
