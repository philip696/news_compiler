"""
Quick tests for WeChat input validation utilities

Run with: pytest backend/test_validation_utils.py
"""

import pytest
from app.core.validation import (
    validate_wechat_account_id,
    validate_search_query,
    validate_article_id,
    sanitize_user_input,
    validate_account_identifier,
    validate_pagination_params,
    validate_sort_field,
)


class TestValidateWeChatAccountId:
    """Test WeChat account ID validation"""
    
    def test_valid_gh_format(self):
        result = validate_wechat_account_id("gh_abc123def456")
        assert result == "gh_abc123def456"
    
    def test_valid_mp_wxs_format(self):
        result = validate_wechat_account_id("MP_WXS_123456")
        assert result == "MP_WXS_123456"
    
    def test_valid_wx_format(self):
        result = validate_wechat_account_id("wx1234567890")
        assert result == "wx1234567890"
    
    def test_too_short(self):
        with pytest.raises(ValueError, match="between 5 and 50"):
            validate_wechat_account_id("gh_a")
    
    def test_too_long(self):
        with pytest.raises(ValueError, match="between 5 and 50"):
            validate_wechat_account_id("gh_" + "a" * 100)
    
    def test_invalid_characters(self):
        with pytest.raises(ValueError, match="letters, numbers, and underscores"):
            validate_wechat_account_id("gh_abc@def")
    
    def test_not_a_string(self):
        with pytest.raises(ValueError, match="must be a string"):
            validate_wechat_account_id(12345)  # type: ignore
    
    def test_strips_whitespace(self):
        result = validate_wechat_account_id("  gh_abc123def456  ")
        assert result == "gh_abc123def456"


class TestValidateSearchQuery:
    """Test search query validation"""
    
    def test_valid_query(self):
        result = validate_search_query("python programming")
        assert result == "python programming"
    
    def test_max_length_default(self):
        query = "a" * 200
        result = validate_search_query(query)
        assert len(result) == 200
    
    def test_exceeds_max_length(self):
        query = "a" * 201
        with pytest.raises(ValueError, match="exceeds maximum"):
            validate_search_query(query)
    
    def test_empty_query(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_search_query("   ")
    
    def test_normalizes_whitespace(self):
        result = validate_search_query("python   programming   tips")
        assert result == "python programming tips"
    
    def test_null_bytes_rejected(self):
        with pytest.raises(ValueError, match="invalid characters"):
            validate_search_query("python\x00programming")
    
    def test_custom_max_length(self):
        with pytest.raises(ValueError, match="exceeds maximum"):
            validate_search_query("a" * 51, max_len=50)
    
    def test_not_a_string(self):
        with pytest.raises(ValueError, match="must be a string"):
            validate_search_query(12345)  # type: ignore


class TestValidateArticleId:
    """Test article ID validation"""
    
    def test_valid_article_id(self):
        result = validate_article_id("article-123-abc")
        assert result == "article-123-abc"
    
    def test_alphanumeric_only(self):
        result = validate_article_id("ABC123")
        assert result == "ABC123"
    
    def test_too_short(self):
        with pytest.raises(ValueError, match="between 5 and 100"):
            validate_article_id("abc")
    
    def test_too_long(self):
        with pytest.raises(ValueError, match="between 5 and 100"):
            validate_article_id("a" * 101)
    
    def test_starts_with_hyphen(self):
        with pytest.raises(ValueError, match="cannot start or end with a hyphen"):
            validate_article_id("-article-123")
    
    def test_ends_with_hyphen(self):
        with pytest.raises(ValueError, match="cannot start or end with a hyphen"):
            validate_article_id("article-123-")
    
    def test_invalid_characters(self):
        with pytest.raises(ValueError, match="letters, numbers, and hyphens"):
            validate_article_id("article@123")
    
    def test_not_a_string(self):
        with pytest.raises(ValueError, match="must be a string"):
            validate_article_id(12345)  # type: ignore


class TestSanitizeUserInput:
    """Test user input sanitization"""
    
    def test_valid_input(self):
        result = sanitize_user_input("Hello, World!")
        assert result == "Hello, World!"
    
    def test_strips_whitespace(self):
        result = sanitize_user_input("   Hello, World!   ")
        assert result == "Hello, World!"
    
    def test_normalizes_whitespace(self):
        result = sanitize_user_input("Hello,      World!")
        assert result == "Hello, World!"
    
    def test_empty_input(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            sanitize_user_input("   ")
    
    def test_exceeds_max_length(self):
        with pytest.raises(ValueError, match="exceeds maximum"):
            sanitize_user_input("a" * 501)
    
    def test_removes_null_bytes(self):
        result = sanitize_user_input("Hello\x00World")
        assert result == "HelloWorld"
    
    def test_custom_max_length(self):
        with pytest.raises(ValueError, match="exceeds maximum"):
            sanitize_user_input("a" * 51, max_len=50)
    
    def test_not_a_string(self):
        with pytest.raises(ValueError, match="must be a string"):
            sanitize_user_input(12345)  # type: ignore


class TestValidateAccountIdentifier:
    """Test account identifier validation"""
    
    def test_valid_identifier(self):
        result = validate_account_identifier("user.name-123")
        assert result == "user.name-123"
    
    def test_alphanumeric(self):
        result = validate_account_identifier("username123")
        assert result == "username123"
    
    def test_too_long(self):
        with pytest.raises(ValueError, match="exceeds 100 characters"):
            validate_account_identifier("a" * 101)
    
    def test_empty_identifier(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_account_identifier("   ")
    
    def test_invalid_characters(self):
        with pytest.raises(ValueError, match="invalid characters"):
            validate_account_identifier("user@domain")
    
    def test_not_a_string(self):
        with pytest.raises(ValueError, match="must be a string"):
            validate_account_identifier(12345)  # type: ignore


class TestValidatePaginationParams:
    """Test pagination parameter validation"""
    
    def test_valid_params(self):
        limit, offset = validate_pagination_params(50, 0)
        assert limit == 50
        assert offset == 0
    
    def test_limit_too_low(self):
        with pytest.raises(ValueError, match="between 1 and 500"):
            validate_pagination_params(0)
    
    def test_limit_too_high(self):
        with pytest.raises(ValueError, match="between 1 and 500"):
            validate_pagination_params(501)
    
    def test_negative_offset(self):
        with pytest.raises(ValueError, match="cannot be negative"):
            validate_pagination_params(50, -1)
    
    def test_not_integers(self):
        with pytest.raises(ValueError, match="must be integers"):
            validate_pagination_params("50", 0)  # type: ignore


class TestValidateSortField:
    """Test sort field validation"""
    
    def test_valid_sort_field(self):
        result = validate_sort_field("title", ["title", "date", "author"])
        assert result == "title"
    
    def test_case_insensitive(self):
        result = validate_sort_field("TITLE", ["title", "date", "author"])
        assert result == "title"
    
    def test_invalid_sort_field(self):
        with pytest.raises(ValueError, match="Invalid sort field"):
            validate_sort_field("invalid", ["title", "date", "author"])
    
    def test_not_a_string(self):
        with pytest.raises(ValueError, match="must be a string"):
            validate_sort_field(123, ["title", "date"])  # type: ignore


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
