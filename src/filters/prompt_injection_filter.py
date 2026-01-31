"""Filter for detecting likely prompt injection attempts in posts."""

import re
from typing import Optional

from ..models import FilterMatch, Post
from .base import BaseFilter


class PromptInjectionFilter(BaseFilter):
    """
    Detects likely prompt injection attempts in post content.

    This filter identifies patterns commonly used in prompt injection attacks
    against LLMs, including instruction overrides, role-playing exploits,
    and system prompt extraction attempts.
    """

    # Patterns indicating prompt injection attempts
    # Format: (category, pattern, severity, description)
    INJECTION_PATTERNS = [
        # Direct instruction overrides
        (
            "instruction_override",
            r"ignore (?:all )?(?:previous|prior|above|earlier|the) (?:instructions?|prompts?|rules?|guidelines?)",
            "high",
            "Attempts to override previous instructions",
        ),
        (
            "instruction_override",
            r"disregard (?:all )?(?:previous|prior|your) (?:instructions?|programming|directives?)",
            "high",
            "Attempts to disregard instructions",
        ),
        (
            "instruction_override",
            r"forget (?:everything|all|what) (?:you(?:'ve)? (?:been|were) told|above|previous)",
            "high",
            "Attempts to make model forget instructions",
        ),
        # New instruction injection
        (
            "new_instructions",
            r"(?:new|your new|from now on|henceforth)[,:]?\s*(?:instructions?|rules?|you (?:are|will|must|should))",
            "high",
            "Attempts to inject new instructions",
        ),
        (
            "new_instructions",
            r"(?:start|begin) (?:fresh|anew|over)|reset (?:your|the) (?:context|instructions?)",
            "medium",
            "Attempts to reset context",
        ),
        # Role-playing exploits
        (
            "roleplay_exploit",
            r"(?:you are|act as|pretend (?:to be|you(?:'re| are))|roleplay as|imagine you(?:'re| are)) (?:a |an )?(?:different|new|evil|unrestricted|unfiltered)",
            "high",
            "Attempts to change model role/persona",
        ),
        (
            "roleplay_exploit",
            r"\b(?:jailbreak|DAN|do anything now|STAN|DUDE|AIM|evil mode|developer mode|god mode)\b",
            "critical",
            "Known jailbreak attempt patterns",
        ),
        (
            "roleplay_exploit",
            r"(?:enter|switch to|activate|enable) (?:.*?)(?:mode|persona)",
            "medium",
            "Mode switching attempts",
        ),
        # System prompt extraction
        (
            "prompt_extraction",
            r"(?:reveal|show|display|print|output|tell me|what (?:is|are)) (?:your |the )?(?:system ?prompt|initial prompt|instructions?|rules?|guidelines?|configuration)",
            "high",
            "Attempts to extract system prompt",
        ),
        (
            "prompt_extraction",
            r"(?:repeat|recite|echo|copy) (?:everything|all|your|the) (?:above|previous|instructions?|prompt)",
            "high",
            "Attempts to echo system prompt",
        ),
        (
            "prompt_extraction",
            r"what (?:were you|are you) (?:told|instructed|programmed) to",
            "medium",
            "Indirect prompt extraction",
        ),
        # Boundary/delimiter attacks
        (
            "delimiter_attack",
            r"<\|(?:im_start|im_end|system|user|assistant|endoftext)\|>",
            "critical",
            "ChatML delimiter injection",
        ),
        (
            "delimiter_attack",
            r"\[(?:INST|/INST|SYS|/SYS)\]",
            "critical",
            "Llama-style delimiter injection",
        ),
        (
            "delimiter_attack",
            r"(?:Human|Assistant|System):\s*$",
            "high",
            "Role delimiter injection",
        ),
        (
            "delimiter_attack",
            r"```(?:system|instructions?|prompt)",
            "medium",
            "Code block delimiter attack",
        ),
        # Encoding/obfuscation attempts
        (
            "obfuscation",
            r"(?:base64|rot13|hex|binary)[:\s]+(?:decode|encoded?|decrypt)",
            "medium",
            "Encoding-based obfuscation",
        ),
        (
            "obfuscation",
            r"(?:read|interpret|execute) (?:this |the )?(?:backwards|reversed|encoded)",
            "medium",
            "Instruction obfuscation",
        ),
        # Indirect injection markers
        (
            "indirect_injection",
            r"(?:when|if) (?:you |an? )?(?:AI|LLM|language model|assistant|chatbot) (?:reads?|sees?|processes?|encounters?) this",
            "high",
            "Indirect injection targeting AI readers",
        ),
        (
            "indirect_injection",
            r"(?:attention|note to|message for) (?:the )?(?:AI|assistant|model|LLM)",
            "high",
            "Direct address to AI systems",
        ),
        (
            "indirect_injection",
            r"<!--.*?(?:ignore|instruction|prompt|system).*?-->",
            "high",
            "Hidden HTML comment injection",
        ),
        # Privilege escalation
        (
            "privilege_escalation",
            r"(?:admin|root|sudo|superuser|override) (?:mode|access|privileges?|commands?)",
            "high",
            "Privilege escalation attempts",
        ),
        (
            "privilege_escalation",
            r"(?:bypass|disable|turn off|remove) (?:all )?(?:safety|security|restrictions?|filters?|guardrails?|limits?)",
            "critical",
            "Safety bypass attempts",
        ),
        # Output manipulation
        (
            "output_manipulation",
            r"(?:only |just )?(?:respond|reply|answer|output|say) (?:with |in )?(?:yes|no|true|false|json|xml|code)",
            "low",
            "Output format manipulation",
        ),
        (
            "output_manipulation",
            r"do not (?:add|include|mention|say|output) (?:anything|any) (?:else|other|extra)",
            "low",
            "Output restriction attempts",
        ),
    ]

    @property
    def name(self) -> str:
        return "prompt_injection_detector"

    @property
    def description(self) -> str:
        return "Detects likely prompt injection attempts targeting LLMs"

    def analyze(self, post: Post) -> Optional[FilterMatch]:
        """Analyze post for potential prompt injection attempts."""
        text = self.get_searchable_text(post)
        text_lower = text.lower()

        matches = []
        categories_found = set()
        highest_severity = "low"
        severity_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}

        for category, pattern, severity, description in self.INJECTION_PATTERNS:
            regex = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
            found = regex.findall(text)
            if found:
                categories_found.add(category)
                # Get a snippet of the match for context
                match_obj = regex.search(text)
                if match_obj:
                    snippet = match_obj.group(0)
                    if len(snippet) > 50:
                        snippet = snippet[:47] + "..."
                    matches.append(f"[{category}] {description}: '{snippet}'")

                if severity_order.get(severity, 0) > severity_order.get(
                    highest_severity, 0
                ):
                    highest_severity = severity

        # Additional heuristic checks
        heuristic_matches = self._check_heuristics(text_lower)
        if heuristic_matches:
            matches.extend(heuristic_matches)
            categories_found.add("heuristic")
            if severity_order.get("medium", 0) > severity_order.get(
                highest_severity, 0
            ):
                highest_severity = "medium"

        if matches:
            return FilterMatch(
                filter_name=self.name,
                post=post,
                reason=f"Detected {len(matches)} potential injection pattern(s) across {len(categories_found)} category(ies)",
                severity=highest_severity,
                matched_patterns=matches,
            )

        return None

    def _check_heuristics(self, text: str) -> list[str]:
        """Apply heuristic checks for suspicious patterns."""
        matches = []

        # Check for excessive use of imperative commands
        imperative_words = [
            "must",
            "shall",
            "will",
            "always",
            "never",
            "do not",
            "don't",
            "cannot",
            "can't",
        ]
        imperative_count = sum(1 for word in imperative_words if word in text)
        if imperative_count >= 4:
            matches.append(
                f"[heuristic] High imperative word density ({imperative_count} found)"
            )

        # Check for unusual character patterns
        if text.count("```") >= 3:
            matches.append("[heuristic] Multiple code block delimiters")

        # Check for suspicious whitespace or zero-width characters
        suspicious_chars = [
            "\u200b",  # Zero-width space
            "\u200c",  # Zero-width non-joiner
            "\u200d",  # Zero-width joiner
            "\ufeff",  # Zero-width no-break space
        ]
        for char in suspicious_chars:
            if char in text:
                matches.append("[heuristic] Contains zero-width/invisible characters")
                break

        return matches
