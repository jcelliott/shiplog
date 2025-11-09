"""AI-based PR categorization using Claude."""

from typing import List, Dict
from anthropic import Anthropic

from .config import Config
from .github_client import PullRequest


class PRCategorizer:
    """Categorize pull requests using Claude AI."""

    def __init__(self, config: Config):
        """Initialize the categorizer."""
        self.config = config
        self.client = Anthropic(api_key=config.claude.api_key)
        self.categories = config.output.categories

    def categorize_batch(self, prs: List[PullRequest]) -> Dict[str, str]:
        """Categorize a batch of PRs.

        Returns a mapping of PR number to category name.
        """
        if not prs:
            return {}

        # Build the prompt with all PRs
        prompt = self._build_prompt(prs)

        # Call Claude API
        response = self.client.messages.create(
            model=self.config.claude.model,
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )

        # Parse the response
        categorization = self._parse_response(response.content[0].text, prs)
        return categorization

    def _build_prompt(self, prs: List[PullRequest]) -> str:
        """Build the categorization prompt."""
        categories_str = ", ".join(f'"{cat}"' for cat in self.categories)

        prompt = f"""You are helping categorize pull requests for an internal team changelog.

Available categories: {categories_str}

For each PR below, determine which category it belongs to based on its title and description. Consider:
- "Features" - New functionality, enhancements, new capabilities
- "Bug Fixes" - Fixes for bugs, errors, or incorrect behavior
- "Dev Ex" - Developer experience improvements, tooling, CI/CD, documentation, refactoring

Respond with ONLY a JSON object mapping PR numbers to categories. Format:
{{
  "123": "Features",
  "456": "Bug Fixes"
}}

Pull Requests to categorize:

"""

        for pr in prs:
            prompt += f"\nPR #{pr.number} ({pr.repo})\n"
            prompt += f"Title: {pr.title}\n"
            if pr.body:
                # Truncate very long descriptions
                body = pr.body[:500] + "..." if len(pr.body) > 500 else pr.body
                prompt += f"Description: {body}\n"
            prompt += f"URL: {pr.url}\n"
            prompt += "---\n"

        prompt += "\nReturn ONLY the JSON object, no other text."

        return prompt

    def _parse_response(self, response_text: str, prs: List[PullRequest]) -> Dict[str, str]:
        """Parse Claude's response into a categorization mapping."""
        import json

        try:
            # Extract JSON from response
            # Claude might wrap it in markdown code blocks
            text = response_text.strip()
            if text.startswith("```"):
                # Remove markdown code blocks
                lines = text.split("\n")
                text = "\n".join(lines[1:-1])
                if text.startswith("json"):
                    text = "\n".join(text.split("\n")[1:])

            categorization = json.loads(text)

            # Convert PR numbers to strings for consistent lookup
            result = {}
            for pr in prs:
                pr_key = str(pr.number)
                if pr_key in categorization:
                    category = categorization[pr_key]
                    # Validate category
                    if category in self.categories:
                        result[pr_key] = category
                    else:
                        # Default to first category if invalid
                        result[pr_key] = self.categories[0]
                else:
                    # Default to first category if not found
                    result[pr_key] = self.categories[0]

            return result

        except json.JSONDecodeError as e:
            print(f"Warning: Failed to parse Claude response: {e}")
            print(f"Response was: {response_text}")
            # Fallback: assign all to first category
            return {str(pr.number): self.categories[0] for pr in prs}

    def close(self):
        """Close the client."""
        self.client.close()
