"""
Input Validation Utility for WeChat Security

Provides validation functions for:
- WeChat account IDs
- Search queries
- Article IDs
- User input sanitization
"""

import re
import logging

logger = logging.getLogger(__name__)


def validate_wechat_account_id(account_id: str) -> str:
    """
    Validate WeChat account ID format.
    
    WeChat account IDs must match one of these formats:
    - MP_WXS_123456... (Official account)
    - gh_abc123def456... (Official or subscription account)
    
    Args:
        account_id: The WeChat account ID to validate
        
    Returns:
        str: The validated account_id
        
    Raises:
        ValueError: If account_id is invalid
    """
    if not isinstance(account_id, str):
        raise ValueError("WeChat account ID must be a string")
    
    account_id = account_id.strip()
    
    # Check length: 5-50 characters
    if len(account_id) < 5 or len(account_id) > 50:
        raise ValueError("WeChat account ID must be between 5 and 50 characters")
    
    # Check format: alphanumeric and underscores only
    if not re.match(r"^[a-zA-Z0-9_]+$", account_id):
        raise ValueError("WeChat account ID can only contain letters, numbers, and underscores")
    
    # Validate known prefixes
    valid_prefixes = ("MP_", "gh_", "wx")
    if not account_id.startswith(valid_prefixes):
        logger.warning(f"Account ID {account_id} has unexpected prefix (expected MP_, gh_, or wx)")
    
    logger.debug(f"Validated WeChat account ID: {account_id}")
    return account_id


def validate_search_query(query: str, max_len: int = 200) -> str:
    """
    Validate search query string.
    
    Args:
        query: The search query to validate
        max_len: Maximum allowed query length (default 200)
        
    Returns:
        str: The validated and sanitized query
        
    Raises:
        ValueError: If query is invalid
    """
    if not isinstance(query, str):
        raise ValueError("Search query must be a string")
    
    # Strip leading/trailing whitespace
    query = query.strip()
    
    if len(query) == 0:
        raise ValueError("Search query cannot be empty")
    
    if len(query) > max_len:
        raise ValueError(f"Search query exceeds maximum length of {max_len} characters")
    
    # Check for null bytes
    if "\x00" in query:
        raise ValueError("Search query contains invalid characters (null bytes)")
    
    # Remove excessive whitespace (multiple spaces/tabs/newlines)
    query = " ".join(query.split())
    
    logger.debug(f"Validated search query: {query[:50]}...")
    return query


def validate_article_id(article_id: str) -> str:
    """
    Validate article ID format.
    
    Article IDs must be:
    - Alphanumeric characters and hyphens only
    - 5-100 characters long
    
    Args:
        article_id: The article ID to validate
        
    Returns:
        str: The validated article_id
        
    Raises:
        ValueError: If article_id is invalid
    """
    if not isinstance(article_id, str):
        raise ValueError("Article ID must be a string")
    
    article_id = article_id.strip()
    
    # Check length: 5-100 characters
    if len(article_id) < 5 or len(article_id) > 100:
        raise ValueError("Article ID must be between 5 and 100 characters")
    
    # Check format: alphanumeric and hyphens only
    if not re.match(r"^[a-zA-Z0-9\-]+$", article_id):
        raise ValueError("Article ID can only contain letters, numbers, and hyphens")
    
    # Ensure it doesn't start or end with a hyphen
    if article_id.startswith("-") or article_id.endswith("-"):
        raise ValueError("Article ID cannot start or end with a hyphen")
    
    logger.debug(f"Validated article ID: {article_id}")
    return article_id


def sanitize_user_input(text: str, max_len: int = 500) -> str:
    """
    Sanitize and validate user input text.
    
    Performs:
    - Whitespace stripping
    - Null byte removal
    - Length validation
    - Excessive whitespace normalization
    
    Args:
        text: The user input to sanitize
        max_len: Maximum allowed text length (default 500)
        
    Returns:
        str: The sanitized text
        
    Raises:
        ValueError: If text is invalid
    """
    if not isinstance(text, str):
        raise ValueError("Input must be a string")
    
    # Strip leading/trailing whitespace
    text = text.strip()
    
    if len(text) == 0:
        raise ValueError("Input cannot be empty")
    
    if len(text) > max_len:
        raise ValueError(f"Input exceeds maximum length of {max_len} characters")
    
    # Remove null bytes
    if "\x00" in text:
        text = text.replace("\x00", "")
        logger.warning("Removed null bytes from user input")
    
    # Normalize excessive whitespace (multiple spaces/tabs/newlines become single space)
    text = " ".join(text.split())
    
    logger.debug(f"Sanitized user input: {text[:50]}...")
    return text


def validate_account_identifier(identifier: str) -> str:
    """
    Validate a WeChat account identifier (can be numeric ID or account name).
    
    Args:
        identifier: The account identifier to validate
        
    Returns:
        str: The validated identifier
        
    Raises:
        ValueError: If identifier is invalid
    """
    if not isinstance(identifier, str):
        raise ValueError("Account identifier must be a string")
    
    identifier = identifier.strip()
    
    if len(identifier) == 0:
        raise ValueError("Account identifier cannot be empty")
    
    if len(identifier) > 100:
        raise ValueError("Account identifier exceeds 100 characters")
    
    # Allow alphanumeric, underscores, hyphens, and periods
    if not re.match(r"^[a-zA-Z0-9_\-\.]+$", identifier):
        raise ValueError("Account identifier contains invalid characters")
    
    return identifier


def validate_pagination_params(limit: int, offset: int = 0) -> tuple:
    """
    Validate pagination parameters.
    
    Args:
        limit: Maximum number of results to return
        offset: Number of results to skip (default 0)
        
    Returns:
        tuple: (validated_limit, validated_offset)
        
    Raises:
        ValueError: If parameters are invalid
    """
    if not isinstance(limit, int) or not isinstance(offset, int):
        raise ValueError("Limit and offset must be integers")
    
    if limit < 1 or limit > 500:
        raise ValueError("Limit must be between 1 and 500")
    
    if offset < 0:
        raise ValueError("Offset cannot be negative")
    
    return limit, offset


def validate_sort_field(field: str, allowed_fields: list) -> str:
    """
    Validate sort field to prevent injection attacks.
    
    Args:
        field: The sort field name to validate
        allowed_fields: List of allowed field names
        
    Returns:
        str: The validated field name
        
    Raises:
        ValueError: If field is not in allowed_fields
    """
    if not isinstance(field, str):
        raise ValueError("Sort field must be a string")
    
    field = field.strip().lower()
    allowed_lower = [f.lower() for f in allowed_fields]
    
    if field not in allowed_lower:
        raise ValueError(f"Invalid sort field. Allowed fields: {', '.join(allowed_fields)}")
    
    return field
