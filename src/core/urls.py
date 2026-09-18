"""Display URL policy shared by imported records, navigation and templates."""

from urllib.parse import urlsplit


def safe_url(value, *, relative=False):
    if not isinstance(value, str) or not value:
        return None
    # Browsers normalize controls and backslashes differently from URL parsers.
    if any(ord(char) < 32 or 127 <= ord(char) <= 159 for char in value) or "\\" in value:
        return None
    value = value.strip()
    if relative and value.startswith("/") and not value.startswith("//"):
        return value
    try:
        url = urlsplit(value)
        if (url.scheme.lower() in {"http", "https"} and url.hostname
                and not url.username and not url.password
                and not any(char.isspace() for char in url.netloc)):
            _ = url.port  # Reject malformed ports.
            return value
    except ValueError:
        pass
    return None
