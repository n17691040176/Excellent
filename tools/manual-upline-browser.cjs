const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const assert = require('node:assert/strict');
const { chromium } = require(require.resolve('playwright-core', { paths: [path.join(os.tmpdir(), 'excellent-browser-test')] }));
const api = 'http://127.0.0.1:8000/api/v1';
const output = path.resolve(__dirname, '../logs/local-test');

(async () => {
  const browser = await chromium.launch({ executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: true });
  const errors = [], failures = [];
  try {
    const page = await browser.newPage({ viewport: { width: 1500, height: 1000 } });
    page.on('pageerror', error => errors.push(error.message));
    page.on('response', response => { if (response.status() >= 400) failures.push({ url: response.url(), status: response.status() }); });
    const login = await (await page.request.post(api + '/auth/admin-login', { data: { phone: '18800000000', password: 'Admin@123' } })).json();
    const headers = { Authorization: 'Bearer ' + login.data.access_token };
    async function call(method, route, data) {
      const response = await page.request[method](api + route, { headers, data });
      assert.equal(response.status(), 200, await response.text());
      return (await response.json()).data;
    }
    const suffix = Date.now().toString();
    const category = await call('post', '/admin/categories', { name: '七级手动测试-' + suffix, slug: 'manual-upline-' + suffix });
    const product = await call('post', '/admin/products', { product_name: 'manual-upline-ui-' + suffix, product_type: 'PHYSICAL',
      zone_type: 'SELF_OPERATED', owner_type: 'SELF_OPERATED', category_id: category.id, sale_price: '10', cost_price: '5', stock: 10 });
    const ruleUrl = `/admin/products/${product.id}/zone-config`;
    await call('put', ruleUrl, { city_partner_commission_enabled: true, city_partner_amount: '0', city_partner_direct_reward_amount: '1' });
    await page.goto('http://127.0.0.1:5173/login');
    await page.getByPlaceholder('请输入管理员手机号').fill('18800000000');
    await page.getByPlaceholder('请输入密码', { exact: true }).fill('Admin@123');
    await page.getByRole('button', { name: '进入后台' }).click();
    await page.waitForURL('**/dashboard');
    await page.goto('http://127.0.0.1:5173/products');
    await page.getByPlaceholder('搜索商品名称 / 品牌').fill(product.product_name);
    await page.getByPlaceholder('搜索商品名称 / 品牌').press('Enter');
    const row = page.locator('.el-table__row').filter({ hasText: product.product_name });
    const drawer = page.locator('.el-drawer').filter({ hasText: '规则 - ' + product.product_name });
    async function openRules() {
      await row.first().getByRole('button', { name: '更多' }).click();
      await page.getByRole('menuitem', { name: '规则配置', exact: true }).click();
      await drawer.getByText('七级分润', { exact: true }).waitFor();
    }
    async function save() {
      const saved = page.waitForResponse(response => response.url().endsWith(ruleUrl) && response.request().method() === 'PUT');
      await drawer.getByRole('button', { name: '保存规则' }).click();
      assert.equal((await saved).status(), 200);
      await drawer.waitFor({ state: 'hidden' });
      return call('get', ruleUrl);
    }
    const input = level => drawer.locator('.el-form-item').filter({ hasText: `第 ${level} 级` }).getByRole('spinbutton');
    await openRules();
    await drawer.getByText('手动设置', { exact: true }).click();
    for (let level = 1; level <= 7; level++) {
      await input(level).fill('0.2');
      await input(level).press('Tab');
    }
    assert.match(await drawer.locator('.city-partner-rule-summary').innerText(), /2\.40/);
    let rules = await save();
    assert.equal(rules.city_partner_upline_mode, 'MANUAL');
    assert.deepEqual(rules.city_partner_upline_amounts, Array(7).fill('0.20'));
    await openRules();
    await input(1).fill('0.37');
    await input(1).press('Tab');
    rules = await save();
    assert.equal(rules.city_partner_upline_amounts[0], '0.37');
    await openRules();
    await drawer.getByText('按 50% 递减', { exact: true }).click();
    rules = await save();
    assert.equal(rules.city_partner_calculation_policy, 'DIRECT_HALVING_7_V2');
    assert.equal(rules.city_partner_upline_amounts[0], '0.37');
    await openRules();
    await drawer.getByText('手动设置', { exact: true }).click();
    assert.equal(Number(await input(1).inputValue()), 0.37);
    await input(1).fill('0.2');
    await input(1).press('Tab');
    await drawer.screenshot({ path: path.join(output, 'manual-upline-admin.png') });
    rules = await save();
    assert.deepEqual(rules.city_partner_upline_amounts, Array(7).fill('0.20'));
    assert.deepEqual(errors, []);
    assert.deepEqual(failures, []);
    const result = { product_id: product.id, manual_amounts: rules.city_partner_upline_amounts, save_reload: true,
      individual_edit: true, auto_manual_switch: true, errors, failures };
    fs.writeFileSync(path.join(output, 'manual-upline-browser-results.json'), JSON.stringify(result, null, 2));
    console.log(JSON.stringify(result));
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
