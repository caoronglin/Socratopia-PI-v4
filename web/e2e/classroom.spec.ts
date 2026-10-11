import { test, expect } from '@playwright/test';

const TOKEN = 'e2e-test-token-1234567890';
const NAME = '自动化遗传学';
const QUOTE = '减数分裂将染色体数目减半，形成单倍体细胞。';

test('desktop onboarding → textbook → live classroom quiz → AntV → mobile controls', async ({ page, browser }) => {
  await page.goto('/');
  await page.getByPlaceholder('服务令牌（仅保存在此页面内存）').fill(TOKEN);
  await page.getByRole('button', { name: '连接并刷新' }).click();
  await page.getByPlaceholder('课程名称', { exact: true }).fill(NAME);
  await page.getByRole('button', { name: '创建课程' }).click();
  await expect(page.getByText('当前课程没有可用主教材')).toBeVisible();

  await page.getByText('教材证据', { exact: true }).click();
  await expect(page.getByText('尚无主教材')).toBeVisible();
  await page.locator('.import-form textarea').fill('# 遗传学\n## 第一节 减数分裂\n' + QUOTE);
  await page.getByRole('button', { name: '确认导入（只创建，不覆盖）' }).click();
  await expect(page.getByText('主教材已载入')).toBeVisible();
  await expect(page.getByText('第一节 减数分裂')).toBeVisible();
  await page.getByText('章节备课', { exact: true }).first().click();
  await expect(page.getByText('章节备课与正式课堂分离')).toBeVisible();
  await page.getByRole('combobox', { name: '选择备课章节' }).click();
  await page.locator('.ant-select-item-option-content').getByText('遗传学', { exact: true }).click();
  await page.getByRole('button', { name: '预览备课草稿' }).click();
  await expect(page.getByText('仅预览，尚未保存')).toBeVisible();
  await page.getByRole('button', { name: '保存草稿（不覆盖）' }).click();
  await expect(page.getByText('草稿已保存')).toBeVisible();
  await page.getByRole('button', { name: '检查', exact: true }).click();
  await expect(page.getByText('尚未通过 ready 门禁')).toBeVisible();

  // Browser integration: history GET restores a server-provided transcript.
  // Actual SQLite persistence is verified by the Python API tests.
  await page.route('**/api/courses/**/chat/history', async route => {
    await route.fulfill({ status: 200, contentType: 'application/json',
      body: JSON.stringify({ course: NAME, exchanges: 1, turns: [
        { speaker: 'student', text: '历史对话恢复测试：减数分裂' },
        { speaker: 'pi', text: '已保存的课堂解释', grounding: 'citation_checked',
          citations: [{ source_id: 'S1', section: '减数分裂', quote: QUOTE }],
          source_current: false, fact_verified: false },
      ] }),
    });
  });
  await page.getByText('课堂与对话', { exact: true }).click();
  await page.getByRole('button', { name: '刷新状态' }).click();
  await expect(page.getByText('历史对话恢复测试：减数分裂')).toBeVisible();
  await expect(page.getByText('原教材已更改，引用可能过期')).toBeVisible();
  await expect(page.getByText('课堂互动练习')).toBeVisible();
  await page.getByText('录入已核对的课堂题目').click();
  await page.getByPlaceholder('明确、可客观判分的问题').fill('减数分裂的染色体数目如何变化？');
  const options = page.getByPlaceholder('填写一个候选答案');
  for (const [index, value] of ['减半', '加倍', '不变', '随机变化'].entries()) {
    await options.nth(index).fill(value);
  }
  await page.getByPlaceholder('说明正确答案及其他选项不成立的原因').fill('根据教材，减数分裂形成单倍体细胞。');
  await page.getByPlaceholder('从当前课程的 book.md 复制对应的原始证据').fill(QUOTE);
  await page.getByRole('button', { name: '保存题目' }).click();
  const practice = page.locator('.practice-question').first();
  await expect(practice.getByText('减数分裂的染色体数目如何变化？')).toBeVisible();
  await practice.locator('.desktop-practice-options .ant-radio-wrapper').first().click();
  await practice.getByRole('button', { name: '提交答案' }).click();
  await expect(practice.getByText('回答正确')).toBeVisible();
  await expect(page.locator('.practice-chart')).toBeVisible();
  await expect(page.getByText('练习表现')).toBeVisible();

  await page.reload();
  await page.getByPlaceholder('服务令牌（仅保存在此页面内存）').fill(TOKEN);
  await page.getByRole('button', { name: '连接并刷新' }).click();
  await expect(page.getByText('课堂互动练习')).toBeVisible();
  await expect(page.locator('.practice-question')).toHaveCount(1);
  await expect(page.getByText('历史对话恢复测试：减数分裂')).toBeVisible();

  const mobile = await browser.newContext({
    viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true,
  });
  const mobilePage = await mobile.newPage();
  try {
    await mobilePage.goto('/');
    await mobilePage.getByPlaceholder('服务令牌（仅保存在此页面内存）').fill(TOKEN);
    await mobilePage.getByRole('button', { name: '连接并刷新' }).click();
    await expect(mobilePage.locator('.mobile-tabbar')).toBeVisible();
    await expect(mobilePage.locator('.desktop-sidebar')).toBeHidden();
    await expect(mobilePage.locator('.mobile-practice-options')).toBeVisible();
    const item = mobilePage.locator('.practice-question').first();
    await item.locator('.mobile-practice-options .adm-radio').first().click();
    await item.locator('.mobile-submit').click();
    await expect(item.getByText('回答正确')).toBeVisible();
    await mobilePage.locator('.mobile-tabbar').getByText('教材').click();
    await expect(mobilePage.getByText('主教材已载入')).toBeVisible();
  } finally {
    await mobile.close();
  }
});
