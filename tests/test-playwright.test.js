const { test, expect } = require('@playwright/test');

test('Check if Playwright works', async ({ page }) => {
  // 访问一个简单的网站
  await page.goto('https://example.com');
  
  // 验证页面标题
  await expect(page).toHaveTitle('Example Domain');
  
  // 验证页面内容
  const content = await page.textContent('h1');
  expect(content).toBe('Example Domain');
  
  console.log('Playwright test passed successfully!');
});