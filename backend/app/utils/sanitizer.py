"""
HTML Sanitization utilities for preventing XSS attacks

Provides sanitization functions for article content, titles, and summaries
using bleach library with a safe whitelist of allowed HTML tags and attributes.
"""

import logging
import bleach
from typing import Optional

logger = logging.getLogger(__name__)

# Whitelist of safe HTML tags for article content
ALLOWED_TAGS = [
    'p',          # Paragraphs
    'br',         # Line breaks
    'strong',     # Bold
    'em',         # Italic / emphasis
    'u',          # Underline
    'a',          # Anchor links
    'img',        # Images
    'ul',         # Unordered list
    'ol',         # Ordered list
    'li',         # List items
    'blockquote', # Block quotes
    'code',       # Inline code
    'pre',        # Preformatted text
]

# Whitelist of safe attributes per tag
ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title'],           # Allow href and title on links
    'img': ['src', 'alt', 'width', 'height'],  # Allow image attributes
}


def sanitize_article_content(html_content: Optional[str]) -> str:
    """
    Sanitize article content HTML to prevent XSS attacks.
    
    Uses bleach.clean() with a whitelist of safe tags and attributes.
    Removes all scripts, event handlers, and dangerous attributes.
    
    Args:
        html_content: Raw HTML content from article
        
    Returns:
        Cleaned HTML content safe to display
        
    Examples:
        >>> sanitize_article_content('<p>Hello <strong>world</strong></p>')
        '<p>Hello <strong>world</strong></p>'
        
        >>> sanitize_article_content('<p>Hello <script>alert("xss")</script></p>')
        '<p>Hello </p>'
        
        >>> sanitize_article_content('<p onclick="alert()">Dangerous</p>')
        '<p>Dangerous</p>'
    """
    if not html_content:
        return ""
    
    try:
        # Use bleach to clean HTML with whitelist
        cleaned = bleach.clean(
            html_content,
            tags=ALLOWED_TAGS,
            attributes=ALLOWED_ATTRIBUTES,
            strip=True,  # Strip disallowed tags instead of escaping
            strip_comments=True  # Remove HTML comments
        )
        logger.debug("Article content sanitized successfully")
        return cleaned
    except Exception as e:
        logger.error(f"Error sanitizing article content: {e}", exc_info=True)
        # Return escaped text as fallback
        return bleach.clean(html_content, tags=[], strip=True)


def sanitize_article_title(text: Optional[str]) -> str:
    """
    Sanitize article title by removing ALL HTML tags.
    
    Titles should be plain text only. This removes any HTML markup
    and returns clean plain text.
    
    Args:
        text: Article title (may contain HTML)
        
    Returns:
        Plain text title with all HTML removed
        
    Examples:
        >>> sanitize_article_title('My <strong>Title</strong>')
        'My Title'
        
        >>> sanitize_article_title('<script>alert("xss")</script>Title')
        'Title'
    """
    if not text:
        return ""
    
    try:
        # Remove all HTML tags, keep only text
        cleaned = bleach.clean(text, tags=[], strip=True)
        logger.debug("Article title sanitized successfully")
        return cleaned
    except Exception as e:
        logger.error(f"Error sanitizing article title: {e}", exc_info=True)
        # Return as-is, bleach.clean should handle it
        return text


def sanitize_article_summary(text: Optional[str]) -> str:
    """
    Sanitize article summary by removing ALL HTML tags.
    
    Summaries should be plain text only. This removes any HTML markup
    and returns clean plain text. Same behavior as sanitize_article_title.
    
    Args:
        text: Article summary (may contain HTML)
        
    Returns:
        Plain text summary with all HTML removed
        
    Examples:
        >>> sanitize_article_summary('Article <em>summary</em> text')
        'Article summary text'
        
        >>> sanitize_article_summary('<img src=x onerror="alert()">Summary')
        'Summary'
    """
    if not text:
        return ""
    
    try:
        # Remove all HTML tags, keep only text
        cleaned = bleach.clean(text, tags=[], strip=True)
        logger.debug("Article summary sanitized successfully")
        return cleaned
    except Exception as e:
        logger.error(f"Error sanitizing article summary: {e}", exc_info=True)
        # Return as-is, bleach.clean should handle it
        return text
