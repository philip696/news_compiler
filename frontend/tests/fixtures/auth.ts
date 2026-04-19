import { test as base, Page } from '@playwright/test'

type AuthFixtures = {
  authenticatedPage: Page
  unauthenticatedPage: Page
}

export const test = base.extend<AuthFixtures>({
  authenticatedPage: async ({ page, context }, use) => {
    // Set up localStorage with auth token
    const token = 'test-wechat-token-' + Date.now()
    const user = {
      id: 'test-user-123',
      nickname: 'Test User',
      avatar: 'https://example.com/avatar.jpg',
      openid: 'test-openid-123',
    }

    // Set localStorage before navigating
    await context.addInitScript(
      (token, user) => {
        const authStorage = {
          state: {
            token: token,
            user: user,
          },
          version: 0,
        }
        localStorage.setItem('auth-storage', JSON.stringify(authStorage))

        const wechatStorage = {
          state: {
            wechatAuthToken: token,
            wechatUser: user,
            isWeChatLogged: true,
          },
          version: 0,
        }
        localStorage.setItem('wechat-storage', JSON.stringify(wechatStorage))
      },
      token,
      user
    )

    // Navigate to a page to apply localStorage
    await page.goto('/')

    // Set up API route mocks
    await page.route('**/api/wewe-rss/feeds', (route) =>
      route.abort('blockedbyresponse')
    )
    await page.route('**/api/wewe-rss/feeds/all', (route) =>
      route.abort('blockedbyresponse')
    )

    // Use the page for the test
    await use(page)
  },

  unauthenticatedPage: async ({ page }, use) => {
    // Clear any auth data
    await page.evaluate(() => {
      localStorage.clear()
      sessionStorage.clear()
    })

    await use(page)
  },
})

export { expect } from '@playwright/test'
