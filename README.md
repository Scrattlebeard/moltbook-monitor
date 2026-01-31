# moltbook-monitor

Scrape Moltbook content to do telemetry and analysis, e.g. check for prompt injection attempts, secrets leaked, etc.

## Features

- **Regular Scraping**: Automatically fetches new posts at configurable intervals
- **Extensible Filter Framework**: Easy to add new filters/classifiers
- **Built-in Filters**:
  - `api_key_detector`: Identifies likely API keys, tokens, and secrets (AWS, OpenAI, Stripe, GitHub, etc.)
  - `prompt_injection_detector`: Detects prompt injection attempts targeting LLMs

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Set your Moltbook API key:
   ```bash
   MOLTBOOK_API_KEY=your_api_key_here
   ```

## Usage

```bash
# Run continuous monitoring
python main.py

# Run a single scrape cycle
python main.py --once

# Monitor a specific submolt
python main.py --submolt technology

# List available filters
python main.py --list-filters

# Change sort order (new, hot, top, rising)
python main.py --sort hot
```

## Adding Custom Filters

Create a new filter by subclassing `BaseFilter`:

```python
from src.filters.base import BaseFilter
from src.models import FilterMatch, Post

class MyCustomFilter(BaseFilter):
    @property
    def name(self) -> str:
        return "my_custom_filter"

    @property
    def description(self) -> str:
        return "Detects something interesting"

    def analyze(self, post: Post) -> FilterMatch | None:
        text = self.get_searchable_text(post)
        if "interesting_pattern" in text:
            return FilterMatch(
                filter_name=self.name,
                post=post,
                reason="Found interesting pattern",
                severity="medium",
            )
        return None
```

Register it in `src/filters/__init__.py` and `src/filters/base.py:create_default_registry()`.

## Output

Flagged posts are saved to `flagged_posts.json` (configurable) with details including:
- Filter that matched
- Post metadata (ID, title, author, submolt)
- Match reason and severity
- Matched patterns
