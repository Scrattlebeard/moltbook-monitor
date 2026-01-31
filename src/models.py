"""Data models for Moltbook Monitor."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Author:
    """Post author information."""

    name: str


@dataclass
class Submolt:
    """Submolt (community) information."""

    name: str
    display_name: str


@dataclass
class Post:
    """Represents a Moltbook post."""

    id: str
    title: str
    content: str
    upvotes: int
    downvotes: int
    created_at: datetime
    author: Author
    submolt: Submolt
    url: Optional[str] = None

    @classmethod
    def from_api_response(cls, data: dict) -> "Post":
        """Create a Post from API response data."""
        return cls(
            id=data["id"],
            title=data["title"],
            content=data.get("content", ""),
            upvotes=data.get("upvotes", 0),
            downvotes=data.get("downvotes", 0),
            created_at=datetime.fromisoformat(
                data["created_at"].replace("Z", "+00:00")
            ),
            author=Author(name=data["author"]["name"]),
            submolt=Submolt(
                name=data["submolt"]["name"],
                display_name=data["submolt"]["display_name"],
            ),
            url=data.get("url"),
        )


@dataclass
class FilterMatch:
    """Result of a filter matching a post."""

    filter_name: str
    post: Post
    reason: str
    severity: str = "medium"
    matched_patterns: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "filter_name": self.filter_name,
            "post_id": self.post.id,
            "post_title": self.post.title,
            "author": self.post.author.name,
            "submolt": self.post.submolt.name,
            "reason": self.reason,
            "severity": self.severity,
            "matched_patterns": self.matched_patterns,
            "created_at": self.post.created_at.isoformat(),
        }
