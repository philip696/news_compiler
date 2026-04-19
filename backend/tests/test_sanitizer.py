"""
Tests for HTML sanitization utilities

Tests the sanitizer functions to ensure XSS prevention
and proper handling of safe HTML tags.
"""

import pytest
from app.utils.sanitizer import (
    sanitize_article_content,
    sanitize_article_title,
    sanitize_article_summary,
)


class TestSanitizeArticleContent:
    """Tests for sanitize_article_content function"""

    def test_safe_html_preserved(self):
        """Basic safe HTML should be preserved"""
        safe_html = '<p>Hello <strong>world</strong></p>'
        result = sanitize_article_content(safe_html)
        assert '<p>' in result
        assert '<strong>' in result
        assert 'Hello' in result
        assert 'world' in result

    def test_script_tags_removed(self):
        """Script tags should be removed (content preserved as text, but tags gone so no execution)"""
        dangerous = '<p>Hello <script>alert("xss")</script> world</p>'
        result = sanitize_article_content(dangerous)
        assert '<script>' not in result
        assert '</script>' not in result
        assert 'Hello' in result
        assert 'world' in result
        # Note: The text content of script tag is preserved as plain text, which is safe
        # because without <script> tags, it won't execute as code

    def test_event_handlers_removed(self):
        """Event handlers should be removed"""
        dangerous = '<p onclick="alert()">Click me</p>'
        result = sanitize_article_content(dangerous)
        assert 'onclick' not in result
        assert 'alert' not in result
        assert 'Click me' in result

    def test_allowed_tags_preserved(self):
        """All allowed tags should be preserved"""
        html = '''
        <p>Paragraph</p>
        <br>
        <strong>Bold</strong>
        <em>Italic</em>
        <u>Underline</u>
        <a href="http://example.com">Link</a>
        <img src="http://example.com/img.jpg" alt="Image" width="100" height="100">
        <ul><li>Item</li></ul>
        <ol><li>Item</li></ol>
        <blockquote>Quote</blockquote>
        <code>Code</code>
        <pre>Preformatted</pre>
        '''
        result = sanitize_article_content(html)
        assert '<p>' in result
        assert '<strong>' in result
        assert '<em>' in result
        assert '<u>' in result
        assert '<a href=' in result
        assert '<img src=' in result
        assert '<ul>' in result
        assert '<ol>' in result
        assert '<blockquote>' in result
        assert '<code>' in result
        assert '<pre>' in result

    def test_disallowed_tags_removed(self):
        """Disallowed tags should be removed but content preserved"""
        html = '<div>Div content</div><span>Span content</span>'
        result = sanitize_article_content(html)
        assert '<div>' not in result
        assert '<span>' not in result
        assert 'Div content' in result
        assert 'Span content' in result

    def test_javascript_url_removed(self):
        """JavaScript URLs should be removed from links"""
        dangerous = '<a href="javascript:alert(\'xss\')">Click</a>'
        result = sanitize_article_content(dangerous)
        assert 'javascript:' not in result

    def test_data_attributes_removed(self):
        """Data attributes should be removed"""
        dangerous = '<p data-value="xss">Content</p>'
        result = sanitize_article_content(dangerous)
        assert 'data-value' not in result
        assert 'Content' in result

    def test_empty_string(self):
        """Empty string should return empty string"""
        result = sanitize_article_content("")
        assert result == ""

    def test_none_returns_empty_string(self):
        """None should return empty string"""
        result = sanitize_article_content(None)
        assert result == ""

    def test_img_attributes_limited(self):
        """Only allowed image attributes should be preserved"""
        html = '<img src="img.jpg" alt="alt" width="100" height="100" onclick="alert()" data-id="123">'
        result = sanitize_article_content(html)
        assert 'src=' in result
        assert 'alt=' in result
        assert 'width=' in result
        assert 'height=' in result
        assert 'onclick=' not in result
        assert 'data-id=' not in result


class TestSanitizeArticleTitle:
    """Tests for sanitize_article_title function"""

    def test_all_html_removed(self):
        """All HTML tags should be removed from title"""
        title = 'My <strong>Title</strong> Text'
        result = sanitize_article_title(title)
        assert result == 'My Title Text'
        assert '<strong>' not in result

    def test_script_tags_removed(self):
        """Script tags should be removed"""
        title = '<script>alert("xss")</script>Title'
        result = sanitize_article_title(title)
        assert '<script>' not in result
        assert '</script>' not in result
        assert 'Title' in result
        # Note: Text content preserved as plain text is safe - no tags means no execution

    def test_plain_text_preserved(self):
        """Plain text should be preserved"""
        title = 'Plain Text Title'
        result = sanitize_article_title(title)
        assert result == 'Plain Text Title'

    def test_empty_string(self):
        """Empty string should return empty string"""
        result = sanitize_article_title("")
        assert result == ""

    def test_none_returns_empty_string(self):
        """None should return empty string"""
        result = sanitize_article_title(None)
        assert result == ""

    def test_mixed_content(self):
        """Mixed HTML and text should return text only"""
        title = '<em>Breaking</em> News: <img src="x" onerror="alert()"> Crisis'
        result = sanitize_article_title(title)
        assert 'Breaking News' in result
        assert 'Crisis' in result
        assert '<' not in result
        assert '>' not in result


class TestSanitizeArticleSummary:
    """Tests for sanitize_article_summary function"""

    def test_all_html_removed(self):
        """All HTML tags should be removed from summary"""
        summary = 'This is a <em>summary</em> with <strong>formatting</strong>'
        result = sanitize_article_summary(summary)
        assert result == 'This is a summary with formatting'
        assert '<em>' not in result
        assert '<strong>' not in result

    def test_dangerous_attributes_removed(self):
        """Dangerous attributes should be removed"""
        summary = '<p onerror="alert()">Summary</p>'
        result = sanitize_article_summary(summary)
        assert 'onerror' not in result
        assert 'Summary' in result

    def test_empty_string(self):
        """Empty string should return empty string"""
        result = sanitize_article_summary("")
        assert result == ""

    def test_none_returns_empty_string(self):
        """None should return empty string"""
        result = sanitize_article_summary(None)
        assert result == ""

    def test_multiple_tags(self):
        """Multiple tags should all be removed"""
        summary = '<div><p><span>Article summary text</span></p></div>'
        result = sanitize_article_summary(summary)
        assert 'Article summary text' in result
        assert '<' not in result
        assert '>' not in result


class TestXSSVectorPrevention:
    """Tests for real-world XSS prevention"""

    xss_vectors = [
        '<img src=x onerror="alert(\'xss\')">',
        '<svg onload="alert(\'xss\')">',
        '<iframe src="javascript:alert(\'xss\')">',
        '<body onload="alert(\'xss\')">',
        '<input onfocus="alert(\'xss\')" autofocus>',
        '<marquee onstart="alert(\'xss\')">',
        '<div style="background:url(javascript:alert(\'xss\'))">',
    ]

    @pytest.mark.parametrize("xss_vector", xss_vectors)
    def test_xss_vectors_blocked_in_content(self, xss_vector):
        """Various XSS vectors should be blocked in content"""
        result = sanitize_article_content(xss_vector)
        assert 'alert' not in result.lower()
        assert 'javascript:' not in result.lower()
        assert 'onerror' not in result.lower()
        assert 'onload' not in result.lower()
        assert 'onfocus' not in result.lower()
        assert 'onstart' not in result.lower()

    @pytest.mark.parametrize("xss_vector", xss_vectors)
    def test_xss_vectors_blocked_in_title(self, xss_vector):
        """XSS vectors should be blocked in titles"""
        result = sanitize_article_title(xss_vector)
        assert 'alert' not in result.lower()
        assert 'javascript:' not in result.lower()
        assert '<' not in result


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
