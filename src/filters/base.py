"""Base filter class and registry for extensible post filtering."""

from abc import ABC, abstractmethod
from typing import Optional

from ..models import FilterMatch, Post


class BaseFilter(ABC):
    """
    Abstract base class for post filters.

    To create a new filter:
    1. Subclass BaseFilter
    2. Implement the `name` property
    3. Implement the `analyze` method
    4. Register with FilterRegistry.register()
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name identifying this filter."""
        pass

    @property
    def description(self) -> str:
        """Human-readable description of what this filter detects."""
        return "No description provided"

    @property
    def enabled(self) -> bool:
        """Whether this filter is enabled."""
        return True

    @abstractmethod
    def analyze(self, post: Post) -> Optional[FilterMatch]:
        """
        Analyze a post and return a FilterMatch if it matches filter criteria.

        Args:
            post: The post to analyze

        Returns:
            FilterMatch if the post matches criteria, None otherwise
        """
        pass

    def get_searchable_text(self, post: Post) -> str:
        """Get combined searchable text from a post."""
        parts = [post.title, post.content]
        if post.url:
            parts.append(post.url)
        return "\n".join(parts)


class FilterRegistry:
    """
    Registry for managing and running filters.

    Example usage:
        registry = FilterRegistry()
        registry.register(APIKeyFilter())
        registry.register(PromptInjectionFilter())

        for post in posts:
            matches = registry.run_all(post)
            for match in matches:
                print(f"Filter '{match.filter_name}' matched: {match.reason}")
    """

    def __init__(self):
        self._filters: dict[str, BaseFilter] = {}

    def register(self, filter_instance: BaseFilter) -> None:
        """Register a filter instance."""
        if filter_instance.name in self._filters:
            raise ValueError(f"Filter '{filter_instance.name}' is already registered")
        self._filters[filter_instance.name] = filter_instance

    def unregister(self, filter_name: str) -> None:
        """Unregister a filter by name."""
        if filter_name in self._filters:
            del self._filters[filter_name]

    def get(self, filter_name: str) -> Optional[BaseFilter]:
        """Get a filter by name."""
        return self._filters.get(filter_name)

    def list_filters(self) -> list[str]:
        """List all registered filter names."""
        return list(self._filters.keys())

    def run_all(self, post: Post) -> list[FilterMatch]:
        """
        Run all enabled filters against a post.

        Returns:
            List of FilterMatch objects for filters that matched
        """
        matches = []
        for filter_instance in self._filters.values():
            if not filter_instance.enabled:
                continue
            match = filter_instance.analyze(post)
            if match:
                matches.append(match)
        return matches

    def run_filter(self, filter_name: str, post: Post) -> Optional[FilterMatch]:
        """Run a specific filter against a post."""
        filter_instance = self._filters.get(filter_name)
        if not filter_instance:
            raise ValueError(f"Filter '{filter_name}' not found")
        return filter_instance.analyze(post)


def create_default_registry() -> FilterRegistry:
    """Create a registry with all default filters enabled."""
    from .api_key_filter import APIKeyFilter
    from .prompt_injection_filter import PromptInjectionFilter

    registry = FilterRegistry()
    registry.register(APIKeyFilter())
    registry.register(PromptInjectionFilter())
    return registry
