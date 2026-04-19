import { Page, Locator } from '@playwright/test'

export class WeChatArticlesPage {
  readonly page: Page
  readonly searchInput: Locator
  readonly accountFilter: Locator
  readonly articleCard: Locator
  readonly detailModal: Locator
  readonly detailCloseButton: Locator
  readonly detailTitle: Locator
  readonly detailContent: Locator
  readonly bookmarkButton: Locator
  readonly shareButton: Locator
  readonly readButton: Locator
  readonly gridContainer: Locator
  readonly emptyState: Locator
  readonly loadingSpinner: Locator
  readonly errorMessage: Locator

  constructor(page: Page) {
    this.page = page
    this.searchInput = page.locator('input[placeholder*="search" i]')
    this.accountFilter = page.locator('select, [data-testid="account-filter"]')
    this.articleCard = page.locator('[data-testid="article-card"]')
    this.detailModal = page.locator('[role="dialog"]')
    this.detailCloseButton = page.locator('button[aria-label="close"]')
    this.detailTitle = page.locator('[data-testid="article-detail-title"]')
    this.detailContent = page.locator('[data-testid="article-detail-content"]')
    this.bookmarkButton = page.locator('button[aria-label*="bookmark" i]')
    this.shareButton = page.locator('button[aria-label*="share" i]')
    this.readButton = page.locator('button[aria-label*="read" i]')
    this.gridContainer = page.locator('[data-testid="articles-grid"]')
    this.emptyState = page.locator('text=/no articles|没有文章/i')
    this.loadingSpinner = page.locator('[data-testid="loading-spinner"]')
    this.errorMessage = page.locator('[role="alert"]')
  }

  async goto() {
    await this.page.goto('/wechat/articles')
    await this.page.waitForLoadState('networkidle')
  }

  async searchArticles(query: string) {
    await this.searchInput.fill(query)
    await this.page.waitForTimeout(500) // Wait for debounce
  }

  async clearSearch() {
    await this.searchInput.clear()
    await this.page.waitForTimeout(500)
  }

  async selectAccount(accountId: string) {
    await this.accountFilter.selectOption(accountId)
    await this.page.waitForLoadState('networkidle')
  }

  async getArticleCount(): Promise<number> {
    return this.articleCard.count()
  }

  async clickArticle(index: number = 0) {
    await this.articleCard.nth(index).click()
  }

  async isDetailModalOpen(): Promise<boolean> {
    return this.detailModal.isVisible()
  }

  async closeDetailModal() {
    await this.detailCloseButton.click()
  }

  async getArticleTitle(index: number = 0): Promise<string | null> {
    return this.articleCard.nth(index).locator('h3, h2').first().textContent()
  }

  async clickBookmark(index: number = 0) {
    await this.articleCard.nth(index).locator('button[aria-label*="bookmark" i]').click()
  }

  async clickShare(index: number = 0) {
    await this.articleCard.nth(index).locator('button[aria-label*="share" i]').click()
  }

  async getDetailTitle(): Promise<string | null> {
    return this.detailTitle.textContent()
  }

  async getDetailContent(): Promise<string | null> {
    return this.detailContent.innerHTML()
  }

  async isEmptyStateShown(): Promise<boolean> {
    return this.emptyState.isVisible()
  }

  async isLoadingShown(): Promise<boolean> {
    return this.loadingSpinner.isVisible()
  }

  async getErrorMessage(): Promise<string | null> {
    return this.errorMessage.textContent()
  }

  async scrollToBottom() {
    await this.page.evaluate(() => {
      window.scrollBy(0, window.innerHeight)
    })
  }
}
