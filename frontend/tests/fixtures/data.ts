/**
 * Mock data generators for E2E tests
 */

export const mockWeChatAccount = {
  id: '1',
  wechat_account_id: 'test_account_001',
  wechat_account_name: 'Test WeChat Account',
  avatar: 'https://example.com/avatar.jpg',
  is_muted: false,
  last_sync_time: new Date().toISOString(),
}

export const mockWeChatAccounts = [
  mockWeChatAccount,
  {
    id: '2',
    wechat_account_id: 'test_account_002',
    wechat_account_name: 'Tech News',
    avatar: 'https://example.com/avatar2.jpg',
    is_muted: false,
    last_sync_time: new Date(Date.now() - 3600000).toISOString(),
  },
  {
    id: '3',
    wechat_account_id: 'test_account_003',
    wechat_account_name: 'Business Updates',
    avatar: 'https://example.com/avatar3.jpg',
    is_muted: true,
    last_sync_time: new Date(Date.now() - 86400000).toISOString(),
  },
]

export const mockWeChatArticle = {
  id: 'article-001',
  account_info: {
    id: '1',
    wechat_account_name: 'Test Account',
    wechat_account_id: 'test_account_001',
    avatar: 'https://example.com/avatar.jpg',
  },
  title: 'Test Article Title',
  content: '<p>This is a test article content.</p>',
  summary: 'This is a brief summary of the test article.',
  main_image: 'https://example.com/image.jpg',
  publish_time: new Date().toISOString(),
  update_time: new Date().toISOString(),
  url: 'https://mp.weixin.qq.com/s/test123',
  views: 1200,
  likes: 45,
}

export const mockWeChatArticles = [
  mockWeChatArticle,
  {
    id: 'article-002',
    account_info: {
      id: '1',
      wechat_account_name: 'Test Account',
      wechat_account_id: 'test_account_001',
      avatar: 'https://example.com/avatar.jpg',
    },
    title: 'Second Article Title',
    content: '<p>Content of second article.</p>',
    summary: 'Summary of second article.',
    main_image: 'https://example.com/image2.jpg',
    publish_time: new Date(Date.now() - 3600000).toISOString(),
    update_time: new Date(Date.now() - 3600000).toISOString(),
    url: 'https://mp.weixin.qq.com/s/test456',
    views: 890,
    likes: 32,
  },
  {
    id: 'article-003',
    account_info: {
      id: '2',
      wechat_account_name: 'Tech News',
      wechat_account_id: 'test_account_002',
      avatar: 'https://example.com/avatar2.jpg',
    },
    title: 'Technology Update',
    content: '<p>Tech content here.</p>',
    summary: 'Latest technology news.',
    main_image: 'https://example.com/image3.jpg',
    publish_time: new Date(Date.now() - 7200000).toISOString(),
    update_time: new Date(Date.now() - 7200000).toISOString(),
    url: 'https://mp.weixin.qq.com/s/test789',
    views: 2100,
    likes: 156,
  },
]

export const mockAuthStartResponse = {
  login_url: 'https://open.weixin.qq.com/connect/oauth2/authorize?appid=test&redirect_uri=http://localhost:3000/wechat/callback',
}

export const mockAuthCallbackResponse = {
  access_token: 'test-wechat-token-' + Date.now(),
  user: {
    id: 'test-user-123',
    nickname: 'Test User',
    avatar: 'https://example.com/avatar.jpg',
    openid: 'test-openid-123',
  },
}

export const mockAccountsResponse = {
  accounts: mockWeChatAccounts,
  total: mockWeChatAccounts.length,
}

export const mockArticleListResponse = {
  articles: mockWeChatArticles,
  total: mockWeChatArticles.length,
  page: 1,
  limit: 20,
  has_more: false,
}

export const mockArticleDetailResponse = {
  ...mockWeChatArticle,
  content: '<p>This is a full HTML content of the test article.</p><p>It includes multiple paragraphs.</p>',
}

export const mockSearchResponse = {
  articles: [mockWeChatArticles[0]],
  total: 1,
  page: 1,
  limit: 20,
  has_more: false,
}
