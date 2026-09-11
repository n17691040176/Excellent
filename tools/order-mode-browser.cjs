const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const assert = require('node:assert/strict');
const { chromium } = require(require.resolve('playwright-core', { paths: [path.join(os.tmpdir(), 'excellent-browser-test')] }));
const out = path.resolve(__dirname, '../logs/local-test');
const fixture = JSON.parse(fs.readFileSync(path.join(out, 'order-mode-fixture.json'), 'utf8'));
const api = 'http://127.0.0.1:8000/api/v1';

(async () => {
  const browser = await chromium.launch({ executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: true });
  const errors = [];
  try {
    const page = await browser.newPage({ viewport: { width: 1500, height: 1000 } });
    page.on('pageerror', error => errors.push(error.message));
    const login = await (await page.request.post(api + '/auth/admin-login', { data: { phone: '18800000000', password: 'Admin@123' } })).json();
    const headers = { Authorization: 'Bearer ' + login.data.access_token };
    const invalid = await page.request.get(api + '/admin/orders?commission_mode=INVALID', { headers });
    assert.equal(invalid.status(), 422);
    await page.goto('http://127.0.0.1:5173/login');
    await page.getByPlaceholder('请输入管理员手机号').fill('18800000000');
    await page.getByPlaceholder('请输入密码', { exact: true }).fill('Admin@123');
    await page.getByRole('button', { name: '进入后台' }).click();
    await page.waitForURL('**/dashboard');
    await page.goto('http://127.0.0.1:5173/orders');
    await page.getByPlaceholder('搜索订单号 / 用户昵称 / 手机号').fill(fixture.keyword);
    const modeField = page.locator('.filter-field--select').filter({ hasText: '分润模式' });
    for (const [mode, label] of [['ORIGINAL', '原分润'], ['CITY_PARTNER', '新分润'], ['UNLOCKED', '未锁定']]) {
      await modeField.locator('.el-select').click();
      await page.getByRole('option', { name: label, exact: true }).click();
      const response = page.waitForResponse(r => r.url().includes('/admin/orders?') && new URL(r.url()).searchParams.get('commission_mode') === mode);
      await page.getByRole('button', { name: '查询', exact: true }).click();
      const result = (await (await response).json()).data;
      assert.equal(result.total, 1);
      assert.equal(result.items[0].id, fixture.order_ids[mode]);
      const row = page.locator('.el-table__row').filter({ hasText: `ORDERMODE-${mode}-${fixture.keyword}` });
      await row.getByText(mode === 'UNLOCKED' ? '待锁定' : label, { exact: true }).waitFor();
      await row.getByRole('button', { name: '详情', exact: true }).click();
      const drawer = page.locator('.el-drawer');
      await drawer.getByText('规则版本', { exact: true }).waitFor();
      const detailResponse = await page.request.get(api + '/admin/orders/' + fixture.order_ids[mode], { headers });
      const detail = (await detailResponse.json()).data;
      assert.equal(detail.commission_mode, mode);
      const modeCell = drawer.locator('.el-descriptions__cell').filter({ hasText: detail.commission_mode_text });
      assert.ok(await modeCell.count());
      if (detail.commission_rule_version) await drawer.getByText(detail.commission_rule_version === 'legacy' ? '历史规则' : detail.commission_rule_version, { exact: true }).waitFor();
      await drawer.screenshot({ path: path.join(out, `order-mode-${mode.toLowerCase()}-detail.png`) });
      await drawer.getByRole('button', { name: 'Close this dialog' }).click();
      await drawer.waitFor({ state: 'hidden' });
    }
    // Delay the reset response so it returns after the subsequent filtered query.
    let resetReturned;
    const staleReset = new Promise(resolve => { resetReturned = resolve; });
    await page.route('**/api/v1/admin/orders?**', async route => {
      if (new URL(route.request().url()).searchParams.has('keyword')) return route.continue();
      const response = await route.fetch();
      await new Promise(resolve => setTimeout(resolve, 1000));
      await route.fulfill({ response });
      resetReturned();
    });
    await page.getByRole('button', { name: '重置筛选', exact: true }).click();
    await page.getByPlaceholder('搜索订单号 / 用户昵称 / 手机号').fill(fixture.keyword);
    const allResponse = page.waitForResponse(r => r.url().includes('/admin/orders?') && new URL(r.url()).searchParams.get('keyword') === fixture.keyword && !new URL(r.url()).searchParams.has('commission_mode'));
    await page.getByRole('button', { name: '查询', exact: true }).click();
    assert.equal((await (await allResponse).json()).data.total, 3);
    await staleReset;
    await page.waitForLoadState('networkidle');
    assert.match(await page.locator('.el-pagination__total').innerText(), /\b3\b/);
    assert.equal(await page.locator('.el-table__body').first().locator('.el-table__row').count(), 3);
    await page.locator('.el-table__row').filter({ hasText: 'ORDERMODE-UNLOCKED-' }).waitFor();
    await page.locator('.el-loading-mask:visible').waitFor({ state: 'hidden' });
    for (const label of ['待锁定', '原分润', '新分润']) await page.locator('.el-table__body').getByText(label, { exact: true }).first().waitFor();
    await page.screenshot({ path: path.join(out, 'order-mode-admin-list.png') });
    const typeField = page.locator('.filter-field--select').filter({ hasText: '订单类型' });
    await typeField.locator('.el-select').click();
    await page.getByRole('option', { name: '城市合伙人席位', exact: true }).waitFor();
    await page.keyboard.press('Escape');

    const mobile = await browser.newPage({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
    mobile.on('pageerror', error => errors.push(error.message));
    await mobile.goto('http://127.0.0.1:5174/#/pages/login/index');
    await mobile.locator('input.uni-input-input').nth(0).fill(fixture.phone);
    const codeResponse = mobile.waitForResponse(r => r.url().includes('/auth/send-login-code'));
    await mobile.getByText('获取验证码', { exact: true }).click();
    const code = (await (await codeResponse).json()).data.debug_code;
    assert.ok(code);
    await mobile.locator('input.uni-input-input').nth(1).fill(code);
    if (!(await mobile.locator('.agreement-check').getAttribute('class')).includes('checked')) await mobile.locator('.agreement-check').click();
    await mobile.locator('.login-btn').click();
    await mobile.waitForURL('**/pages/home/index');
    await mobile.goto('http://127.0.0.1:5174/#/subpackages/commission/index');
    await mobile.locator('.record-desc').filter({ hasText: '原分润' }).waitFor();
    await mobile.locator('.record-desc').filter({ hasText: '新分润' }).waitFor();
    assert.deepEqual(await mobile.locator('.record-status').allTextContents().then(values => values.map(value => value.trim())), ['待结算', '待结算']);
    await mobile.getByText(`订单 ${fixture.order_ids.ORIGINAL} 佣金`, { exact: true }).waitFor();
    await mobile.screenshot({ path: path.join(out, 'order-mode-mobile-commissions.png') });
    assert.deepEqual(errors, []);
    const result = { filters: ['ORIGINAL', 'CITY_PARTNER', 'UNLOCKED'], invalid_filter_rejected: true,
      detail_versions_verified: true, reset_verified: true, stale_response_cannot_overwrite_filter: true, seat_order_type_available: true,
      mobile_mixed_modes_from_local_orders: true, errors };
    fs.writeFileSync(path.join(out, 'order-mode-browser-results.json'), JSON.stringify(result, null, 2));
    console.log(JSON.stringify(result));
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
