# WeChat Integration E2E Tests

This directory contains comprehensive end-to-end tests for the WeChat integration in GEB using Playwright.

## Structure

```
tests/
├── e2e/
│   └── wechat-integration.e2e.ts     # Main test suite with 6 scenarios
├── pages/
│   ├── WeChatLoginPage.ts            # Page Object Model for login page
│   ├── WeChatAccountsPage.ts         # Page Object Model for accounts page
│   └── WeChatArticlesPage.ts         # Page Object Model for articles page
├── fixtures/
│   ├── auth.ts                       # Authentication fixture with test utilities
│   └── data.ts                       # Mock data generators
└── README.md                          # This file
```

## Setup

### 1. Install Dependencies

```bash
cd frontend
npm install
```

This installs `@playwright/test` and related dependencies configured in `package.json`.

### 2. Ensure Backend is Running (or Mocked)

The E2E tests mock API endpoints, so you don't need a backend running. However, the Next.js frontend dev server must be running:

```bash
npm run dev
```

The server will start on `http://localhost:3000`.

## Running Tests

### Run All Tests

```bash
npm run test:e2e
```

### Run Specific Test File

```bash
npx playwright test tests/e2e/wechat-integration.e2e.ts
```

### Run Specific Test

```bash
npx playwright test -g "WeChat login flow"
```

### Debug Mode (opens inspector)

```bash
npm run test:e2e:debug
```

### Headed Mode (see browser)

```bash
npm run test:e2e:headed
```

### UI Mode (interactive)

```bash
npm run test:e2e:ui
```

### View Test Report

```bash
npm run test:e2e:report
```

This opens an HTML report in your default browser showing test results, traces, and artifacts.

## Test Scenarios

### 1. WeChat Login Flow ✓
**Purpose:** Verify OAuth authentication process

**Steps:**
- Navigate to `/wechat/login`
- Click "登录 WeChat" button
- Mock OAuth callback with auth code
- Verify JWT token stored in localStorage
- Verify redirect to `/wechat/accounts`

**Expected Outcome:** User is authenticated and redirected to accounts page

---

### 2. Add WeChat Account ✓
**Purpose:** Verify account subscription workflow

**Steps:**
- Navigate to `/wechat/accounts`
- Click "Add Account" button
- Enter WeChat account ID (e.g., `test_account_004`)
- Submit form
- Verify account appears in list

**Expected Outcome:** New account is added and displayed in sidebar

---

### 3. Manual Update Account ✓
**Purpose:** Verify manual sync/update functionality

**Steps:**
- Navigate to `/wechat/accounts`
- Click "Update" button on first account
- Wait for sync to complete
- Reload page
- Verify `last_sync_time` is updated

**Expected Outcome:** Account sync time is updated after manual trigger

---

### 4. View Articles ✓
**Purpose:** Verify article feed display and detail modal

**Steps:**
- Navigate to `/wechat/articles`
- Verify articles grid loads with cards
- Click on first article
- Verify detail modal opens with full content
- Close modal

**Expected Outcome:** Articles display correctly and detail modal works

---

### 5. Delete Account ✓
**Purpose:** Verify account removal workflow

**Steps:**
- Navigate to `/wechat/accounts`
- Record initial account count
- Click "Delete" button on first account
- Confirm deletion
- Reload page
- Verify account count decreased

**Expected Outcome:** Account is removed from the list

---

### 6. Search Articles ✓
**Purpose:** Verify search filtering

**Steps:**
- Navigate to `/wechat/articles`
- Record initial article count
- Enter search query (e.g., "Test Article")
- Verify filtered results shown
- Clear search
- Verify all articles shown again

**Expected Outcome:** Search filters articles correctly and can be cleared

---

## Mock Strategy

The tests use `page.route()` to intercept API calls and return mock responses:

### Authentication Endpoints
- `GET /api/wechat/auth/start` → Returns login URL
- `POST /api/wechat/auth/callback` → Returns JWT token + user info

### Account Endpoints
- `GET /api/wechat/accounts` → Returns list of subscribed accounts
- `POST /api/wechat/accounts` → Creates new subscription
- `DELETE /api/wechat/accounts/{id}` → Removes subscription
- `POST /api/wechat/accounts/{id}/update` → Manually syncs account

### Article Endpoints
- `GET /api/wechat/articles` → Returns paginated article list
- `GET /api/wechat/articles/{id}` → Returns article details
- `POST /api/wechat/articles/{id}/bookmark` → Adds bookmark
- `DELETE /api/wechat/articles/{id}/bookmark` → Removes bookmark

## Fixtures

### Authentication Fixture (`fixtures/auth.ts`)

Provides two fixtures:

**`authenticatedPage`** - Pre-authenticated with JWT token
```typescript
test('my test', async ({ authenticatedPage }) => {
  // Already logged in, has token in localStorage
  await authenticatedPage.goto('/wechat/accounts')
})
```

**`unauthenticatedPage`** - Fresh browser with no authentication
```typescript
test('login test', async ({ unauthenticatedPage }) => {
  // No token, localStorage cleared
  await unauthenticatedPage.goto('/wechat/login')
})
```

### Mock Data (`fixtures/data.ts`)

Provides mock objects:
- `mockWeChatAccount` - Single account
- `mockWeChatAccounts` - Array of 3 test accounts
- `mockWeChatArticle` - Single article
- `mockWeChatArticles` - Array of 3 test articles
- `mockAuthStartResponse` - OAuth start response
- `mockAuthCallbackResponse` - OAuth callback response
- `mockAccountsResponse` - Accounts list response
- `mockArticleListResponse` - Articles list response

## Page Objects

### `WeChatLoginPage`
```typescript
const loginPage = new WeChatLoginPage(page)
await loginPage.goto()
await loginPage.clickLoginButton()
```

### `WeChatAccountsPage`
```typescript
const accountsPage = new WeChatAccountsPage(page)
await accountsPage.goto()
await accountsPage.clickAddButton()
await accountsPage.fillAccountId('test_account')
```

### `WeChatArticlesPage`
```typescript
const articlesPage = new WeChatArticlesPage(page)
await articlesPage.goto()
await articlesPage.searchArticles('test')
await articlesPage.clickArticle(0)
```

## Configuration

### `playwright.config.ts` Settings

- **Test Directory:** `./tests/e2e`
- **Timeout per test:** 30 seconds
- **Timeout per action:** 10 seconds
- **Retries on failure:** 2 (dev), 0 (CI)
- **Browsers:** Chromium, Firefox
- **Screenshots:** On failure
- **Videos:** On failure
- **Traces:** On first retry
- **Reporters:** HTML, JUnit, JSON
- **Web Server:** Starts `npm run dev` automatically

### Reports Location

- **HTML Report:** `playwright-report/`
- **JUnit XML:** `test-results/`
- **JSON Report:** `test-results/`
- **Videos:** `test-results/` (on failure)
- **Traces:** `test-results/` (on retry)

## Debugging Failed Tests

### 1. Check HTML Report
```bash
npm run test:e2e:report
```

### 2. Enable Debug Mode
```bash
npm run test:e2e:debug
```

This opens the Playwright Inspector. Use:
- `Step over` (F10) to execute next action
- `Resume` (F8) to continue
- `Pause` to stop at breakpoint

### 3. Run with Screenshots
```bash
npx playwright test tests/e2e/wechat-integration.e2e.ts --screenshot=on
```

### 4. Check Video Recording
Videos of failed tests are saved to `test-results/`. Open in any video player.

### 5. View Trace Files
```bash
npx playwright show-trace test-results/trace.zip
```

## CI/CD Integration

### GitHub Actions

Create `.github/workflows/e2e-tests.yml`:

```yaml
name: E2E Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '18'
      - run: cd frontend && npm install
      - run: cd frontend && npm run build
      - run: cd frontend && npx playwright install --with-deps
      - run: cd frontend && npm run test:e2e
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: playwright-report
          path: frontend/playwright-report/
```

## Troubleshooting

### Tests timeout
- Increase timeout in `playwright.config.ts`
- Check if Next.js dev server is running
- Try running with `--headed` to see what's happening

### Mock routes not working
- Verify route patterns match exactly
- Check network tab in debug mode
- Try more specific URL matching

### Flaky tests
- Add more specific waits (don't use fixed timeouts)
- Use `waitForLoadState('networkidle')`
- Add retry logic in test.beforeEach

### Port 3000 already in use
```bash
lsof -i :3000  # Find process using port
kill -9 <PID>  # Kill process
```

## Best Practices

1. **Use Page Objects** - Encapsulate DOM queries
2. **Mock Early** - Mock routes in `test.beforeEach`
3. **Wait for Conditions** - Use `waitForLoadState`, `waitForTimeout`, `expect().toBeVisible()`
4. **Isolate Tests** - Each test should be independent
5. **Clear Selectors** - Use `data-testid` attributes for reliability
6. **Check Artifacts** - Always check logs, traces, and videos on failure

## Related Files

- **Playwright Config:** `playwright.config.ts`
- **Frontend Pages:** `pages/wechat/*.tsx`
- **Frontend Components:** `components/WeChat*.tsx`
- **Frontend Services:** `services/wechatApi.ts`, `services/wechatArticleApi.ts`
- **Frontend Store:** `store/wechat.ts`, `store/wechatArticles.ts`

## Next Steps

- [ ] Add visual regression tests
- [ ] Add performance tests
- [ ] Add accessibility tests
- [ ] Integrate into CI/CD pipeline
- [ ] Add cross-browser testing (Safari, mobile)
- [ ] Add load testing scenarios
- [ ] Parallel test execution optimization
