"""Configuration handling for PR changelog tool."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from dateutil.parser import parse as parse_date


@dataclass
class GitHubConfig:
    """GitHub configuration."""

    token: str
    repositories: List[str]


@dataclass
class FilterConfig:
    """Filter configuration for PRs."""

    since: str
    states: List[str]
    labels: Optional[List[str]] = None

    def get_since_date(self) -> Optional[datetime]:
        """Parse the since field into a datetime.

        Supports formats:
        - "7d", "14d" etc. for relative days
        - "2025-01-01" for specific date
        - "2025-01-01T14:30:00" for timestamp (uses local timezone if not specified)
        - "2025-01-01:2025-12-31" for date range (returns start date)

        Returns timezone-aware datetime. Naive datetimes are interpreted as local time.
        """
        if not self.since:
            return None

        # Get local timezone for naive datetimes
        local_tz = datetime.now().astimezone().tzinfo

        # Handle relative dates like "7d"
        if self.since.endswith("d"):
            try:
                days = int(self.since[:-1])
                return datetime.now(timezone.utc) - timedelta(days=days)
            except ValueError:
                pass

        # Handle date ranges
        if ":" in self.since:
            start_date = self.since.split(":")[0]
            dt = parse_date(start_date)
            # Ensure timezone-aware using local timezone
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=local_tz)
            return dt

        # Handle absolute dates/timestamps
        dt = parse_date(self.since)
        # Ensure timezone-aware using local timezone
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=local_tz)
        return dt


@dataclass
class ClaudeConfig:
    """Claude API configuration."""

    api_key: str
    model: str = "claude-sonnet-4-5"


@dataclass
class OutputConfig:
    """Output configuration."""

    categories: List[str]
    show_author: bool = True
    show_pr_number: bool = True
    slack_users: Optional[Dict[str, str]] = None


@dataclass
class Config:
    """Main configuration."""

    github: GitHubConfig
    filters: FilterConfig
    output: OutputConfig
    claude: ClaudeConfig

    @classmethod
    def from_file(cls, path: Path) -> "Config":
        """Load configuration from a YAML file."""
        with open(path, "r") as f:
            data = yaml.safe_load(f)

        return cls(
            github=GitHubConfig(**data["github"]),
            filters=FilterConfig(**data["filters"]),
            output=OutputConfig(**data["output"]),
            claude=ClaudeConfig(**data["claude"]),
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Config":
        """Create config from dictionary."""
        return cls(
            github=GitHubConfig(**data["github"]),
            filters=FilterConfig(**data["filters"]),
            output=OutputConfig(**data["output"]),
            claude=ClaudeConfig(**data["claude"]),
        )
