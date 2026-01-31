"""Configuration management for Moltbook Monitor."""

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Config:
    """Application configuration loaded from environment variables."""

    api_key: str = field(default_factory=lambda: os.getenv("MOLTBOOK_API_KEY", ""))
    base_url: str = field(
        default_factory=lambda: os.getenv(
            "MOLTBOOK_BASE_URL", "https://www.moltbook.com/api/v1"
        )
    )
    scrape_interval_seconds: int = field(
        default_factory=lambda: int(os.getenv("SCRAPE_INTERVAL_SECONDS", "60"))
    )
    posts_limit: int = field(
        default_factory=lambda: int(os.getenv("POSTS_LIMIT", "25"))
    )
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    output_file: Optional[str] = field(
        default_factory=lambda: os.getenv("OUTPUT_FILE", "flagged_posts.json")
    )

    def validate(self) -> None:
        """Validate required configuration values."""
        # API key is optional - /posts endpoint works without auth
        if not self.base_url.startswith("https://"):
            raise ValueError("Base URL must use HTTPS")
        # Ensure we use www.moltbook.com (without www strips Authorization headers)
        if "moltbook.com" in self.base_url and "www.moltbook.com" not in self.base_url:
            raise ValueError("Must use www.moltbook.com (without www strips auth headers)")


def load_config() -> Config:
    """Load and validate configuration from environment."""
    config = Config()
    config.validate()
    return config
