import { Page, Locator } from '@playwright/test'

export class WeChatLoginPage {
  readonly page: Page
  readonly loginButton: Locator
  readonly errorMessage: Locator
  readonly loadingSpinner: Locator

  constructor(page: Page) {
    this.page = page
    this.loginButton = page.getByRole('button', { name: /登录|login/i })
    this.errorMessage = page.locator('[role="alert"]')
    this.loadingSpinner = page.locator('[data-testid="loading-spinner"]')
  }

  async goto() {
    await this.page.goto('/wechat/login')
    await this.page.waitForLoadState('networkidle')
  }

  async clickLoginButton() {
    await this.loginButton.click()
  }

  async getErrorMessage(): Promise<string | null> {
    const error = await this.errorMessage.textContent()
    return error ? error.trim() : null
  }

  async isErrorDisplayed(): Promise<boolean> {
    return this.errorMessage.isVisible()
  }
}
