import { test, expect } from '@playwright/test';

const TOKEN = 'e2e-test-token-1234567890';
const QUOTE = '减数分裂将染色体数目减半，形成单倍体细胞。';
const BACK = '形成单倍体细胞，染色体数目减半。';
const FRONT = '减数分裂对染色体数目产生什么影响？';

test('flashcards: create → front-only → reveal → review → course isolation → mobile', async ({ page, browser }) => {
  const courseName = '闪卡回归-' + Date.now() + '-' + test.info().retry;
  const secondName = '另一门闪卡课程-' + Date.now() + '-' + test.info().retry;
  const auth = { Authorization: 'Bearer ' + TOKEN };
  const created = await page.request.post('/api/courses', { headers: auth, data: { name: courseName } });
  expect(created.ok(), await created.text()).toBeTruthy();
  const imported = await page.request.post(
    '/api/courses/' + encodeURIComponent(courseName) + '/book',
    { headers: auth, data: { content: '# 遗传学\n## 减数分裂\n' + QUOTE + '\n' } },
  );
  expect(imported.ok(), await imported.text()).toBeTruthy();

  await page.goto('/');
  await page.getByPlaceholder('服务令牌（仅保存在此页面内存）').fill(TOKEN);
  await page.getByRole('button', { name: '连接并刷新' }).click();
  await page.getByRole('combobox', { name: '选择当前课程' }).click();
  await page.locator('.ant-select-item-option-content').getByText(courseName, { exact: true }).click();
  await page.getByRole('menuitem', { name: '记忆闪卡' }).click();
  await expect(page.getByText('记忆闪卡 · 主动回忆')).toBeVisible();
  await page.getByText('新建教材闪卡（人工核对答案）').click();
  await page.getByPlaceholder('例如：减数分裂为什么使染色体数目减半？').fill(FRONT);
  await page.getByPlaceholder('简洁解释关键机制').fill(BACK);
  await page.getByPlaceholder('从当前教材复制一段可核对的原文').fill(QUOTE);
  await page.getByRole('button', { name: '保存闪卡' }).click();
  await expect(page.getByText(FRONT)).toBeVisible();
  await expect(page.getByText(BACK)).toHaveCount(0);
  await page.getByRole('button', { name: '显示答案' }).click();
  await expect(page.getByText(BACK)).toBeVisible();
  await expect(page.getByText(QUOTE)).toBeVisible();
  await page.getByRole('button', { name: '记得 · 间隔复习' }).click();
  await expect(page.getByText('本次推荐闪卡已复习完成，可以休息或下次继续。')).toBeVisible();
  await expect(page.getByText(/本次自评已保存/)).toBeVisible();

  const other = await page.request.post('/api/courses', { headers: auth, data: { name: secondName } });
  expect(other.ok(), await other.text()).toBeTruthy();
  await page.getByRole('button', { name: '连接并刷新' }).click();
  await page.getByRole('combobox', { name: '选择当前课程' }).click();
  await page.locator('.ant-select-item-option-content').getByText(secondName, { exact: true }).click();
  await expect(page.getByText(FRONT)).toHaveCount(0);

  const mobile = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
  const mobilePage = await mobile.newPage();
  try {
    await mobilePage.goto('/');
    await mobilePage.getByPlaceholder('服务令牌（仅保存在此页面内存）').fill(TOKEN);
    await mobilePage.getByRole('button', { name: '连接并刷新' }).click();
    await mobilePage.getByRole('combobox', { name: '选择当前课程' }).click();
    await mobilePage.locator('.ant-select-item-option-content').getByText(courseName, { exact: true }).click();
    await mobilePage.locator('.mobile-tabbar').getByText('闪卡', { exact: true }).click();
    await expect(mobilePage.getByText('记忆闪卡 · 主动回忆')).toBeVisible();
    await expect(mobilePage.getByText(FRONT)).toHaveCount(0);
    await expect(mobilePage.getByText('本次推荐闪卡已复习完成，可以休息或下次继续。')).toBeVisible();
  } finally {
    await mobile.close();
  }
});
