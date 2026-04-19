import { Page, Locator } from '@playwright/test'

export class WeChatAccountsPage {
  readonly page: Page
  readonly addButton: Locator
  readonly accountList: Locator
  readonly modal: Locator
  readonly modalInput: Locator
  readonly modalSubmitButton: Locator
  readonly modalCloseButton: Locator
  readonly accountCard: Locator
  readonly deleteButtons: Locator
  readonly muteButtons: Locator
  readonly updateButtons: Locator
  readonly sidebar: Locator
  readonly mainContent: Locator

  constructor(page: Page) {
    this.page = page
    this.addButton = page.getByRole('button', { name: /add|添加/i })
    this.accountList = page.locator('[data-testid="account-list"]')
    this.modal = page.locator('[role="dialog"]')
    this.modalInput = page.locator('input[placeholder*="account" i]')
    this.modalSubmitButton = page.getByRole('button', { name: /submit|确认|添加/i })
    this.modalCloseButton = page.locator('button[aria-label="close"]')
    this.accountCard = page.locator('[data-testid="account-card"]')
    this.deleteButtons = page.locator('button[aria-label*="delete" i]')
    this.muteButtons = page.locator('button[aria-label*="mute" i]')
    this.updateButtons = page.locator('button[aria-label*="update" i]')
    this.sidebar = page.locator('[data-testid="wechat-sidebar"]')
    this.mainContent = page.locator('main')
  }

  async goto() {
    await this.page.goto('/wechat/accounts')
    await this.page.waitForLoadState('networkidle')
  }

  async clickAddButton() {
    await this.addButton.click()
  }

  async isModalOpen(): Promise<boolean> {
    return this.modal.isVisible()
  }

  async fillAccountId(accountId: string) {
    await this.modalInput.fill(accountId)
  }

  async submitAddForm() {
    await this.modalSubmitButton.click()
  }

  async closeModal() {
    await this.modalCloseButton.click()
  }

  async getAccountCount(): Promise<number> {
    return this.accountCard.count()
  }

  async getFirstAccountName(): Promise<string | null> {
    return this.accountCard.first().locator('text=/[A-Za-z0-9_-]+/').first().textContent()
  }

  async clickDeleteButton(index: number = 0) {
    await this.deleteButtons.nth(index).click()
  }

  async clickMuteButton(index: number = 0) {
    await this.muteButtons.nth(index).click()
  }

  async clickUpdateButton(index: number = 0) {
    await this.updateButtons.nth(index).click()
  }

  async selectAccount(index: number = 0) {
    await this.accountCard.nth(index).click()
  }

  async getLastSyncTime(): Promise<string | null> {
    return this.mainContent.locator('text=/sync|更新/i').first().textContent()
  }
}
