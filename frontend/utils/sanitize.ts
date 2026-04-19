/**
 * HTML Sanitization Utility
 * 
 * Prevents XSS attacks by sanitizing article content from WeChat.
 * Uses DOMPurify library to strip malicious scripts and dangerous attributes.
 * 
 * Installation:
 *   npm install dompurify
 *   npm install -D @types/dompurify
 */

import DOMPurify from 'dompurify'

interface SanitizeOptions {
  allowedTags?: string[]
  allowedAttributes?: string[]
  keepContent?: boolean
}

const DEFAULT_ALLOWED_TAGS = [
  'p',
  'br',
  'strong',
  'em',
  'u',
  'h1',
  'h2',
  'h3',
  'h4',
  'h5',
  'h6',
  'blockquote',
  'a',
  'ul',
  'ol',
  'li',
  'img',
  'figure',
  'figcaption',
  'table',
  'thead',
  'tbody',
  'tr',
  'th',
  'td',
  'div',
  'span',
  'code',
  'pre',
  'hr',
  'article',
  'section',
]

const DEFAULT_ALLOWED_ATTRIBUTES = [
  'href',
  'src',
  'alt',
  'title',
  'target',
  'rel',
  'class',
  'id',
  'width',
  'height',
  'colspan',
  'rowspan',
]

/**
 * Sanitize HTML content to remove XSS payloads
 * 
 * @param html - Raw HTML string (potentially untrusted)
 * @param options - Customization options
 * @returns Sanitized HTML safe to render
 * 
 * @example
 * const unsafe = '<img src=x onerror="alert(\'XSS\')">'
 * const safe = sanitizeHTML(unsafe)
 * // Returns: '' (img tag removed due to invalid src)
 * 
 * @example
 * const markup = '<p>Hello <strong>World</strong></p>'
 * const safe = sanitizeHTML(markup)
 * // Returns: '<p>Hello <strong>World</strong></p>'
 */
export function sanitizeHTML(
  html: string,
  options: SanitizeOptions = {}
): string {
  if (!html) {
    return ''
  }

  const config = {
    ALLOWED_TAGS: options.allowedTags || DEFAULT_ALLOWED_TAGS,
    ALLOWED_ATTR: options.allowedAttributes || DEFAULT_ALLOWED_ATTRIBUTES,
    KEEP_CONTENT: options.keepContent !== false,
    FORCE_BODY: true,
    RETURN_DOM: false,
    RETURN_DOM_FRAGMENT: false,
    RETURN_DOM_IMPORT: false,
  }

  try {
    return DOMPurify.sanitize(html, config)
  } catch (error) {
    console.error('HTML sanitization failed:', error)
    // Fallback: return text only if sanitization fails
    return stripHTML(html)
  }
}

/**
 * Strip all HTML tags (fallback for when sanitization fails)
 * 
 * @param html - HTML string
 * @returns Text content only
 */
function stripHTML(html: string): string {
  const div = document.createElement('div')
  div.innerHTML = html
  return div.textContent || div.innerText || ''
}

/**
 * Validate that sanitized content is safe
 * (Additional defense in depth check)
 * 
 * @param html - HTML to validate
 * @returns true if safe, false if suspicious
 */
export function isHTMLSafe(html: string): boolean {
  // Block if contains script tags (shouldn't happen after sanitize, but double-check)
  if (/<script/i.test(html)) {
    return false
  }

  // Block if contains on* event handlers
  if (/on\w+\s*=/i.test(html)) {
    return false
  }

  // Block if contains javascript: protocol
  if (/javascript:/i.test(html)) {
    return false
  }

  // Block if contains data: protocol (can embed scripts)
  if (/data:text\/html/i.test(html)) {
    return false
  }

  return true
}

