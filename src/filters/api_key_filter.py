"""Filter for detecting likely API keys and secrets in posts."""

import re
from typing import Optional

from ..models import FilterMatch, Post
from .base import BaseFilter


class APIKeyFilter(BaseFilter):
    """
    Detects likely API keys, tokens, and secrets in post content.

    This filter uses pattern matching to identify common API key formats
    from various providers including AWS, OpenAI, Stripe, GitHub, and more.
    """

    # Patterns for common API key formats
    # Format: (name, pattern, severity)
    API_KEY_PATTERNS = [
        # AWS
        (
            "AWS Access Key ID",
            r"AKIA[0-9A-Z]{16}",
            "high",
        ),
        (
            "AWS Secret Access Key",
            r"(?:aws)?_?(?:secret)?_?(?:access)?_?(?:key)?['\"]?\s*[:=]\s*['\"]?([A-Za-z0-9/+=]{40})['\"]?",
            "high",
        ),
        # OpenAI
        (
            "OpenAI API Key",
            r"sk-[A-Za-z0-9]{20}T3BlbkFJ[A-Za-z0-9]{20}",
            "high",
        ),
        (
            "OpenAI API Key (new format)",
            r"sk-(?:proj-)?[A-Za-z0-9_-]{40,}",
            "high",
        ),
        # Anthropic
        (
            "Anthropic API Key",
            r"sk-ant-(?:api\d{2}-)?[A-Za-z0-9_-]{40,}",
            "high",
        ),
        # Stripe
        (
            "Stripe Secret Key",
            r"sk_(?:live|test)_[A-Za-z0-9]{24,}",
            "high",
        ),
        (
            "Stripe Publishable Key",
            r"pk_(?:live|test)_[A-Za-z0-9]{24,}",
            "medium",
        ),
        # GitHub
        (
            "GitHub Token",
            r"gh[pousr]_[A-Za-z0-9]{36,}",
            "high",
        ),
        (
            "GitHub Personal Access Token (classic)",
            r"github_pat_[A-Za-z0-9]{22}_[A-Za-z0-9]{59}",
            "high",
        ),
        # Google
        (
            "Google API Key",
            r"AIza[0-9A-Za-z_-]{35}",
            "high",
        ),
        # Slack
        (
            "Slack Token",
            r"xox[baprs]-[0-9]{10,}-[0-9]{10,}-[A-Za-z0-9]{24,}",
            "high",
        ),
        (
            "Slack Webhook",
            r"https://hooks\.slack\.com/services/T[A-Z0-9]+/B[A-Z0-9]+/[A-Za-z0-9]+",
            "high",
        ),
        # Discord
        (
            "Discord Token",
            r"[MN][A-Za-z\d]{23,}\.[\w-]{6}\.[\w-]{27,}",
            "high",
        ),
        (
            "Discord Webhook",
            r"https://(?:ptb\.|canary\.)?discord(?:app)?\.com/api/webhooks/\d+/[\w-]+",
            "high",
        ),
        # Generic patterns
        (
            "Generic API Key",
            r"(?:api[_-]?key|apikey|api_secret|auth_token)['\"]?\s*[:=]\s*['\"]?([A-Za-z0-9_-]{20,})['\"]?",
            "medium",
        ),
        (
            "Bearer Token",
            r"[Bb]earer\s+[A-Za-z0-9_-]{20,}",
            "medium",
        ),
        (
            "Private Key Block",
            r"-----BEGIN (?:RSA |DSA |EC |OPENSSH )?PRIVATE KEY-----",
            "critical",
        ),
        # Database connection strings
        (
            "Database Connection String",
            r"(?:mongodb|postgres|mysql|redis)://[^\s'\"<>]+:[^\s'\"<>]+@[^\s'\"<>]+",
            "critical",
        ),
        # JWT tokens
        (
            "JWT Token",
            r"eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}",
            "medium",
        ),
        # Twilio
        (
            "Twilio Account SID",
            r"AC[a-f0-9]{32}",
            "medium",
        ),
        (
            "Twilio Auth Token",
            r"(?:twilio)?[_-]?(?:auth)?[_-]?token['\"]?\s*[:=]\s*['\"]?([a-f0-9]{32})['\"]?",
            "high",
        ),
        # SendGrid
        (
            "SendGrid API Key",
            r"SG\.[A-Za-z0-9_-]{22}\.[A-Za-z0-9_-]{43}",
            "high",
        ),
        # Mailchimp
        (
            "Mailchimp API Key",
            r"[a-f0-9]{32}-us\d{1,2}",
            "high",
        ),
    ]

    @property
    def name(self) -> str:
        return "api_key_detector"

    @property
    def description(self) -> str:
        return "Detects likely API keys, tokens, and secrets in post content"

    def analyze(self, post: Post) -> Optional[FilterMatch]:
        """Analyze post for potential API keys and secrets."""
        text = self.get_searchable_text(post)
        matches = []
        highest_severity = "low"
        severity_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}

        for pattern_name, pattern, severity in self.API_KEY_PATTERNS:
            regex = re.compile(pattern, re.IGNORECASE)
            found = regex.findall(text)
            if found:
                # Mask the actual key for safety
                for match in found:
                    if isinstance(match, tuple):
                        match = match[0] if match else ""
                    if len(match) > 8:
                        masked = f"{match[:4]}...{match[-4:]}"
                    else:
                        masked = "***"
                    matches.append(f"{pattern_name}: {masked}")

                if severity_order.get(severity, 0) > severity_order.get(
                    highest_severity, 0
                ):
                    highest_severity = severity

        if matches:
            return FilterMatch(
                filter_name=self.name,
                post=post,
                reason=f"Detected {len(matches)} potential secret(s)",
                severity=highest_severity,
                matched_patterns=matches,
            )

        return None
