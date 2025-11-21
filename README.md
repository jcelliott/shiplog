# Shiplog 🚢

A Python tool to aggregate pull requests across multiple GitHub repositories and compile internal changelogs for your team.

## Features

- 📦 **Multi-repository support** - Track PRs across multiple repos
- 🤖 **AI-powered categorization** - Uses Claude to intelligently categorize PRs by title and description
- ✨ **AI-generated summaries** - Generates concise, clear summaries for each PR
- 🎯 **Flexible filtering** - Filter by date, state, and labels
- 🎨 **Rich terminal output** - Beautiful markdown formatting in your terminal
- 📄 **Export to file** - Save changelogs to markdown files

## Installation

This project uses [uv](https://github.com/astral-sh/uv) for dependency management.

### Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Install dependencies

```bash
uv sync
```

## Configuration

1. Copy the example configuration:

```bash
cp config.example.yaml config.yaml
```

2. Edit `config.yaml` with your settings:

```yaml
github:
  token: "ghp_your_token_here"  # GitHub personal access token
  repositories:
    - "owner/repo1"
    - "owner/repo2"

claude:
  api_key: "sk-ant-your_key_here"  # Claude API key

filters:
  since: "7d"  # Last 7 days, or use "2025-01-01" for specific date
  states:
    - "merged"

output:
  categories:
    - "Features"
    - "Bug Fixes"
    - "Dev Ex"
  show_author: true
  show_pr_number: true
```

### GitHub Token

Generate a personal access token at: https://github.com/settings/tokens

Required scopes:
- `repo` (for private repositories)
- `public_repo` (for public repositories only)

### Claude API Key

Get your API key at: https://console.anthropic.com/settings/keys

The tool uses Claude to:
- Intelligently categorize PRs based on their titles and descriptions
- Generate concise, clear summaries for each PR

## Usage

### Basic usage

```bash
uv run shiplog
```

This reads `config.yaml` and outputs a formatted changelog to your terminal.

### Save to file

```bash
uv run shiplog -o shiplog.md
```

### Custom config file

```bash
uv run shiplog -c custom-config.yaml
```

### Override date filter

```bash
# Last 30 days
uv run shiplog --since 30d

# Specific date range
uv run shiplog --since 2025-01-01

# Date range
uv run shiplog --since 2025-01-01:2025-12-31
```

### Plain text output (no formatting)

```bash
uv run shiplog --plain
```

## Date Filtering

The `since` field in the config (or `--since` flag) supports multiple formats:

- **Relative days**: `"7d"`, `"14d"`, `"30d"`
- **Specific date**: `"2025-01-01"` (uses local timezone)
- **Specific timestamp**: `"2025-01-01T14:30:00"` (uses local timezone)
- **Timestamp with timezone**: `"2025-01-01T14:30:00-05:00"` (explicit timezone offset)
- **Date range**: `"2025-01-01:2025-12-31"` (uses start date)

Note: Dates and timestamps without explicit timezone info are interpreted as your local timezone.

## Example Output

```markdown
# Shiplog

**15 pull requests across 3 repositories**

**Features**

- **Add dark mode support** (`company/frontend`) [#123](https://github.com/company/frontend/pull/123) by @alice
- **Implement user search** (`company/api`) [#456](https://github.com/company/api/pull/456) by @bob

**Bug Fixes**

- **Fix login redirect loop** (`company/frontend`) [#124](https://github.com/company/frontend/pull/124) by @charlie
- **Handle null values in API response** (`company/api`) [#457](https://github.com/company/api/pull/457) by @alice

**Dev Ex**

- **Improve CI pipeline speed** (`company/infrastructure`) [#789](https://github.com/company/infrastructure/pull/789) by @dave
```

## Development

### Project Structure

```
shiplog/
├── shiplog/
│   ├── __init__.py
│   ├── cli.py           # CLI entry point
│   ├── config.py        # Configuration handling
│   ├── github_client.py # GitHub API client
│   ├── categorizer.py   # Claude AI categorization
│   └── formatter.py     # Changelog formatting
├── pyproject.toml       # Project configuration
├── config.example.yaml  # Example config file
└── README.md
```

### Running tests

```bash
# Coming soon
uv run pytest
```

## Future Enhancements

- [ ] Slack integration for posting changelogs
- [ ] Filter by PR author
- [ ] Group by repository instead of category

## License

MIT
