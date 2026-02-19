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
    skip_categorization: bool = False
    skip_summaries: bool = False


def _merge_section(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Shallow per-field merge: override keys replace base keys."""
    merged = dict(base)
    merged.update(override)
    return merged


@dataclass
class Config:
    """Main configuration."""

    github: GitHubConfig
    filters: FilterConfig
    output: OutputConfig
    claude: ClaudeConfig

    @property
    def needs_claude(self) -> bool:
        """Whether the Claude API is needed for this config."""
        return not (self.output.skip_categorization and self.output.skip_summaries)

    @staticmethod
    def _apply_profile(data: Dict[str, Any], profile_name: str) -> Dict[str, Any]:
        """Apply a named profile's overrides to the base config data."""
        profiles = data.get("profiles", {})
        if profile_name not in profiles:
            available = ", ".join(profiles.keys()) if profiles else "none"
            raise ValueError(
                f"Profile '{profile_name}' not found. Available profiles: {available}"
            )

        profile = profiles[profile_name]
        merged = {}
        for section in ("github", "filters", "output", "claude"):
            base_section = data.get(section, {})
            profile_section = profile.get(section, {})
            merged[section] = _merge_section(base_section, profile_section)

        return merged

    @classmethod
    def from_file(cls, path: Path, profile: Optional[str] = None) -> "Config":
        """Load configuration from a YAML file."""
        with open(path, "r") as f:
            data = yaml.safe_load(f)

        if profile:
            data = cls._apply_profile(data, profile)

        return cls(
            github=GitHubConfig(**data["github"]),
            filters=FilterConfig(**data["filters"]),
            output=OutputConfig(**data["output"]),
            claude=ClaudeConfig(**data["claude"]),
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any], profile: Optional[str] = None) -> "Config":
        """Create config from dictionary."""
        if profile:
            data = cls._apply_profile(data, profile)

        return cls(
            github=GitHubConfig(**data["github"]),
            filters=FilterConfig(**data["filters"]),
            output=OutputConfig(**data["output"]),
            claude=ClaudeConfig(**data["claude"]),
        )
