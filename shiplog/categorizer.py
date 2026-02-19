"""AI-based PR categorization using Claude."""

from typing import List, Dict, NamedTuple
from anthropic import Anthropic

from .config import Config
from .github_client import PullRequest


class PRClassification(NamedTuple):
    """Classification result for a PR."""
    category: str
    summary: str


class PRCategorizer:
    """Categorize pull requests using Claude AI."""

    def __init__(self, config: Config):
        """Initialize the categorizer."""
        self.config = config
        self.client = Anthropic(api_key=config.claude.api_key)
        self.categories = config.output.categories

    def categorize_batch(self, prs: List[PullRequest]) -> Dict[str, PRClassification]:
        """Categorize a batch of PRs.

        Returns a mapping of PR number (as string) to PRClassification (category and summary).
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
        """Build the prompt, adapting based on skip flags."""
        skip_cat = self.config.output.skip_categorization
        skip_sum = self.config.output.skip_summaries

        prompt = "You are helping process pull requests for an internal team changelog.\n\n"

        if not skip_cat and not skip_sum:
            # Full mode: categorize + summarize
            categories_str = ", ".join(f'"{cat}"' for cat in self.categories)
            prompt += f"Available categories: {categories_str}\n\n"
            prompt += """For each PR below:
1. Determine which category it belongs to based on its title and description
2. Write a concise summary (1 sentence) describing WHAT was done, not WHY or the benefits

Summary guidelines:
- Focus on WHAT changed, not the rationale or benefits
- Be concise - avoid explanatory clauses about performance, benefits, or reasons
- Keep it factual and direct
- Use past tense (e.g., "Added", "Fixed", "Refactored")

Good examples:
- "Improved text file diffing to use version store interface with asynchronous operations"
- "Refactored layout components into unified src/layout directory structure"

Bad examples (too verbose):
- BAD: "Improved text file diffing to use version store interface with asynchronous operations, enhancing performance and responsiveness for large operations"
- BAD: "Refactored layout components into unified src/layout directory structure, establishing consistent header and container patterns with max 1920px width"

Respond with ONLY a JSON object. Format:
{{
  "123": {{
    "category": "Features",
    "summary": "Added dark mode support with automatic theme switching"
  }}
}}
"""
        elif skip_cat and not skip_sum:
            # Summary-only mode
            prompt += """For each PR below, write a concise summary (1 sentence) describing WHAT was done, not WHY or the benefits.

Summary guidelines:
- Focus on WHAT changed, not the rationale or benefits
- Be concise - avoid explanatory clauses about performance, benefits, or reasons
- Keep it factual and direct
- Use past tense (e.g., "Added", "Fixed", "Refactored")

Good examples:
- "Improved text file diffing to use version store interface with asynchronous operations"
- "Refactored layout components into unified src/layout directory structure"

Respond with ONLY a JSON object. Format:
{{
  "123": {{
    "summary": "Added dark mode support with automatic theme switching"
  }}
}}
"""
        elif not skip_cat and skip_sum:
            # Category-only mode
            categories_str = ", ".join(f'"{cat}"' for cat in self.categories)
            prompt += f"Available categories: {categories_str}\n\n"
            prompt += """For each PR below, determine which category it belongs to based on its title and description.

Respond with ONLY a JSON object. Format:
{{
  "123": {{
    "category": "Features"
  }}
}}
"""

        prompt += "\nPull Requests to process:\n\n"

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

    def _parse_response(self, response_text: str, prs: List[PullRequest]) -> Dict[str, PRClassification]:
        """Parse Claude's response into a categorization mapping."""
        import json

        skip_cat = self.config.output.skip_categorization
        skip_sum = self.config.output.skip_summaries
        default_cat = "" if skip_cat else self.categories[0]

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
                    if isinstance(categorization[pr_key], dict):
                        entry = categorization[pr_key]
                        if skip_cat:
                            category = ""
                        else:
                            category = entry.get("category", self.categories[0])
                            if category not in self.categories:
                                category = self.categories[0]

                        summary = pr.title if skip_sum else entry.get("summary", pr.title)
                    else:
                        category = default_cat
                        summary = pr.title

                    result[pr_key] = PRClassification(category=category, summary=summary)
                else:
                    result[pr_key] = PRClassification(category=default_cat, summary=pr.title)

            return result

        except json.JSONDecodeError as e:
            print(f"Warning: Failed to parse Claude response: {e}")
            print(f"Response was: {response_text}")
            return {
                str(pr.number): PRClassification(category=default_cat, summary=pr.title)
                for pr in prs
            }

    def close(self):
        """Close the client."""
        self.client.close()
