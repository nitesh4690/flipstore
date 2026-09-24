"""Text helpers (slug generation, SKU generation)."""

import random
import re
import string
import uuid


def slugify(value: str, max_length: int = 260) -> str:
    """Create a URL-safe slug: 'Wireless Headphones!' -> 'wireless-headphones'."""
    value = value.strip().lower()
    value = re.sub(r"[^\w\s-]", "", value)
    value = re.sub(r"[\s_-]+", "-", value)
    value = re.sub(r"-{2,}", "-", value).strip("-")
    return value[:max_length] or f"item-{uuid.uuid4().hex[:8]}"


def unique_sku(prefix: str = "SKU") -> str:
    """Generate a random unique SKU like SKU-7F3K9Q."""
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"{prefix}-{suffix}"
