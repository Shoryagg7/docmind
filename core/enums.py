from enum import StrEnum


class PrivacyMode(StrEnum):
    # `off` exists only for the privacy-cost experiment: raw text goes to Groq.
    OFF = "off"
    MINIMIZE = "minimize"


class PrivacyAction(StrEnum):
    ALLOW = "ALLOW"  # no sensitive entities were sent
    MINIMIZE = "MINIMIZE"  # entities were replaced by placeholders before sending
    REQUIRE_CONSENT = "REQUIRE_CONSENT"  # the question needs a sensitive value in clear
    BLOCK = "BLOCK"  # PII detection failed, so nothing was sent
