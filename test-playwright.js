const { chromium } = require('playwright');

async function test() {
  console.log('Testing Playwright...');
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  await page.goto('https://www.baidu.com');
  const title = await page.title();
  console.log('Page title:', title);
  await browser.close();
  console.log('Test completed successfully!');
}

test().catch(console.error);