"""Moltbook API client."""

import logging
from typing import Optional

import httpx

from .config import Config
from .models import Post

logger = logging.getLogger(__name__)


class MoltbookAPIError(Exception):
    """Exception raised for Moltbook API errors."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class MoltbookClient:
    """Client for interacting with the Moltbook API."""

    def __init__(self, config: Config):
        self.config = config
        headers = {"Content-Type": "application/json"}
        # Only add auth header if API key is provided
        if config.api_key:
            headers["Authorization"] = f"Bearer {config.api_key}"
        self._client = httpx.Client(
            base_url=config.base_url,
            headers=headers,
            timeout=30.0,
        )
        self._authenticated = bool(config.api_key)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def _request(self, method: str, endpoint: str, **kwargs) -> dict:
        """Make an API request."""
        try:
            response = self._client.request(method, endpoint, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"API error: {e.response.status_code} - {e.response.text}")
            raise MoltbookAPIError(
                f"API request failed: {e.response.text}",
                status_code=e.response.status_code,
            )
        except httpx.RequestError as e:
            logger.error(f"Request error: {e}")
            raise MoltbookAPIError(f"Request failed: {e}")

    def get_posts(
        self,
        sort: str = "new",
        limit: int = 25,
        submolt: Optional[str] = None,
    ) -> list[Post]:
        """Fetch posts from the global feed or a specific submolt."""
        params = {"sort": sort, "limit": limit}
        if submolt:
            params["submolt"] = submolt

        data = self._request("GET", "/posts", params=params)
        posts = [Post.from_api_response(post) for post in data.get("posts", [])]
        logger.info(f"Fetched {len(posts)} posts")
        return posts

    def get_feed(self, sort: str = "new", limit: int = 25) -> list[Post]:
        """Fetch personalized feed."""
        params = {"sort": sort, "limit": limit}
        data = self._request("GET", "/feed", params=params)
        posts = [Post.from_api_response(post) for post in data.get("posts", [])]
        logger.info(f"Fetched {len(posts)} posts from feed")
        return posts

    def get_post(self, post_id: str) -> Post:
        """Fetch a single post by ID."""
        data = self._request("GET", f"/posts/{post_id}")
        return Post.from_api_response(data)

    def search(
        self,
        query: str,
        search_type: str = "posts",
        limit: int = 50,
    ) -> list[Post]:
        """Semantic search for posts."""
        params = {"q": query, "type": search_type, "limit": limit}
        data = self._request("GET", "/search", params=params)
        posts = [Post.from_api_response(post) for post in data.get("results", [])]
        logger.info(f"Search returned {len(posts)} results")
        return posts
