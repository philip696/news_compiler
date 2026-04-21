// Minimal test harness for WeWe-RSS API integration
// Usage: node test/wechat.ts

import { WeWeRSSApi } from './wechat-api';

async function main() {
	const api = new WeWeRSSApi();

	// 1. Get WeChat login QR
	const { uuid, scanUrl } = await api.createLoginUrl();
	console.log('Scan this QR:', scanUrl);

	// 2. Poll login status (simulate polling)
	let loginResult;
	for (let i = 0; i < 30; i++) {
		loginResult = await api.getLoginResult(uuid);
		console.log('Login status:', loginResult.message);
		if (loginResult.token && loginResult.vid) {
			api.setAuth(String(loginResult.vid), loginResult.token);
			break;
		}
		await new Promise((r) => setTimeout(r, 2000));
	}
	if (!loginResult?.token) {
		console.error('Login failed or timed out');
		return;
	}

	// 3. Get accounts list
	const accounts = await api.getAccounts();
	console.log('Accounts:', accounts);

	// 4. Get articles for a given mpId (replace with real mpId)
	// const articles = await api.getMpArticles('mpId_here');
	// console.log('Articles:', articles);
}

main().catch(console.error);
