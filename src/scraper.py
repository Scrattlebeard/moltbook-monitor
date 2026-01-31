"""Main scraper module for monitoring Moltbook posts."""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from .api_client import MoltbookClient, MoltbookAPIError
from .config import Config
from .filters.base import FilterRegistry, create_default_registry
from .models import FilterMatch, Post

logger = logging.getLogger(__name__)


class PostScraper:
    """
    Scrapes Moltbook posts and runs them through filters.

    The scraper maintains state about seen posts to avoid duplicate processing
    and periodically fetches new posts based on the configured interval.
    """

    def __init__(
        self,
        config: Config,
        registry: Optional[FilterRegistry] = None,
    ):
        self.config = config
        self.registry = registry or create_default_registry()
        self.client = MoltbookClient(config)
        self._seen_post_ids: set[str] = set()
        self._flagged_posts: list[dict] = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client.close()

    def process_posts(self, posts: list[Post]) -> list[FilterMatch]:
        """
        Process a batch of posts through all filters.

        Args:
            posts: List of posts to process

        Returns:
            List of FilterMatch objects for posts that triggered filters
        """
        all_matches = []

        for post in posts:
            # Skip already processed posts
            if post.id in self._seen_post_ids:
                continue

            self._seen_post_ids.add(post.id)
            matches = self.registry.run_all(post)

            if matches:
                logger.info(
                    f"Post '{post.id}' flagged by {len(matches)} filter(s): "
                    f"{[m.filter_name for m in matches]}"
                )
                all_matches.extend(matches)

        return all_matches

    def fetch_and_process(
        self,
        sort: str = "new",
        submolt: Optional[str] = None,
    ) -> list[FilterMatch]:
        """
        Fetch new posts and process them through filters.

        Args:
            sort: Sort order for posts (new, hot, top, rising)
            submolt: Optional submolt to fetch from

        Returns:
            List of FilterMatch objects for flagged posts
        """
        try:
            posts = self.client.get_posts(
                sort=sort,
                limit=self.config.posts_limit,
                submolt=submolt,
            )
            return self.process_posts(posts)
        except MoltbookAPIError as e:
            logger.error(f"Failed to fetch posts: {e}")
            return []

    def save_flagged_posts(self, matches: list[FilterMatch]) -> None:
        """Save flagged posts to the output file and download full content."""
        if not matches or not self.config.output_file:
            return

        # Create flagged_posts directory for full post downloads
        flagged_dir = Path("flagged_posts")
        flagged_dir.mkdir(exist_ok=True)

        for match in matches:
            flagged_data = {
                **match.to_dict(),
                "flagged_at": datetime.utcnow().isoformat(),
                "full_content": {
                    "title": match.post.title,
                    "content": match.post.content,
                    "author": match.post.author.name,
                    "submolt": match.post.submolt.name,
                    "submolt_display": match.post.submolt.display_name,
                    "upvotes": match.post.upvotes,
                    "downvotes": match.post.downvotes,
                    "created_at": match.post.created_at.isoformat(),
                    "url": match.post.url,
                },
            }
            self._flagged_posts.append(flagged_data)

            # Save individual post file
            post_file = flagged_dir / f"{match.post.id}.json"
            post_file.write_text(json.dumps(flagged_data, indent=2, default=str))
            logger.info(f"Saved flagged post to {post_file}")

        output_path = Path(self.config.output_file)
        output_path.write_text(
            json.dumps(self._flagged_posts, indent=2, default=str)
        )
        logger.info(f"Saved {len(self._flagged_posts)} flagged posts to {output_path}")

    def run_once(self, sort: str = "new", submolt: Optional[str] = None) -> int:
        """
        Run a single scrape cycle.

        Returns:
            Number of posts flagged
        """
        logger.info(f"Starting scrape cycle (sort={sort}, submolt={submolt})")
        matches = self.fetch_and_process(sort=sort, submolt=submolt)

        if matches:
            self.save_flagged_posts(matches)
            logger.info(f"Flagged {len(matches)} posts in this cycle")
        else:
            logger.info("No posts flagged in this cycle")

        return len(matches)

    def run_continuous(
        self,
        sort: str = "new",
        submolt: Optional[str] = None,
    ) -> None:
        """
        Run the scraper continuously at the configured interval.

        This method runs indefinitely until interrupted.
        """
        logger.info(
            f"Starting continuous scraper (interval={self.config.scrape_interval_seconds}s)"
        )
        logger.info(f"Enabled filters: {self.registry.list_filters()}")

        total_flagged = 0
        cycles = 0

        try:
            while True:
                cycles += 1
                flagged = self.run_once(sort=sort, submolt=submolt)
                total_flagged += flagged

                logger.info(
                    f"Cycle {cycles} complete. "
                    f"Total flagged: {total_flagged}. "
                    f"Seen posts: {len(self._seen_post_ids)}"
                )

                time.sleep(self.config.scrape_interval_seconds)

        except KeyboardInterrupt:
            logger.info("Scraper stopped by user")
            logger.info(
                f"Final stats: {cycles} cycles, "
                f"{total_flagged} flagged, "
                f"{len(self._seen_post_ids)} unique posts seen"
            )

    def get_stats(self) -> dict:
        """Get current scraper statistics."""
        return {
            "seen_posts": len(self._seen_post_ids),
            "flagged_posts": len(self._flagged_posts),
            "enabled_filters": self.registry.list_filters(),
        }
