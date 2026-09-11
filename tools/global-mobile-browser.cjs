const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const assert = require('node:assert/strict');
const { chromium } = require(require.resolve('playwright-core', { paths: [path.join(os.tmpdir(), 'excellent-browser-test')] }));
const out = path.resolve(__dirname, '../logs/local-test');
const fixture = JSON.parse(fs.readFileSync(path.join(out, 'order-mode-fixture.json'), 'utf8'));
const base = 'http://127.0.0.1:5174/#';
const api = 'http://127.0.0.1:8000/api/v1';

(async () => {
  const browser = await chromium.launch({ executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: true });
  const errors = [], failures = [], visited = [];
  try {
    const mobile = await browser.newPage({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
    mobile.on('pageerror', error => errors.push(error.message));
    mobile.on('response', response => { if (response.status() >= 400) failures.push({ url: response.url(), status: response.status() }); });
    const login = await (await mobile.request.post(api + '/auth/login', { data: { phone: fixture.phone, password: 'LocalTest123' } })).json();
    assert.equal(login.code, 0);
    const headers = { Authorization: 'Bearer ' + login.data.access_token };
    const summary = (await (await mobile.request.get(api + '/app/assets/summary', { headers })).json()).data;
    assert.deepEqual(Object.keys(summary).sort(), ['BALANCE', 'COMMISSION', 'POINTS', 'balance', 'commission', 'points', 'total_amount'].sort());
    await mobile.goto(base + '/pages/login/index');
    await mobile.locator('input.uni-input-input').first().waitFor();
    // uni-h5 stores string values directly in localStorage.
    await mobile.evaluate(token => localStorage.setItem('excellent_token', token), login.data.access_token);
    await mobile.goto(base + '/pages/profile/index');
    await mobile.locator('.user-name').filter({ hasText: 'order-mode-beneficiary-' }).waitFor();
    assert.deepEqual((await mobile.locator('.asset-label').allTextContents()).map(x => x.trim()), ['余额', '佣金', '积分']);
    await mobile.screenshot({ path: path.join(out, 'final-profile-currencies.png') });
    await mobile.locator('.asset-item').filter({ hasText: '积分' }).click();
    await mobile.waitForURL('**/subpackages/assets/index?type=points');
    await mobile.locator('.tab-item.active').filter({ hasText: '积分' }).waitFor();
    assert.deepEqual((await mobile.locator('.tab-item').allTextContents()).map(x => x.trim()), ['余额', '佣金', '积分']);
    assert.doesNotMatch(await mobile.locator('body').innerText(), /消费金|兑换券|AI 券|充电宝/);
    await mobile.locator('.tab-item').filter({ hasText: '余额' }).click();
    await mobile.locator('.tab-item.active').filter({ hasText: '余额' }).waitFor();
    await mobile.waitForLoadState('networkidle');
    await mobile.screenshot({ path: path.join(out, 'final-assets-currencies.png') });
    for (const width of [360, 390, 430]) {
      await mobile.setViewportSize({ width, height: 844 });
      assert.equal(await mobile.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1), false);
    }
    await mobile.locator('.tab-item').filter({ hasText: '佣金' }).click();
    await mobile.waitForURL('**/subpackages/commission/index');
    await mobile.locator('.record-desc').filter({ hasText: '新分润' }).waitFor();
    const routes = ['/pages/home/index', '/pages/packages/list', '/pages/cart/index', '/pages/orders/list',
      '/subpackages/life/index', '/subpackages/life/orders', '/subpackages/team/index',
      '/subpackages/assets/index', '/subpackages/commission/index', '/subpackages/commission/withdraw',
      '/subpackages/invite/index', '/subpackages/profile/favorites', '/subpackages/profile/footprints',
      '/subpackages/profile/cart', '/subpackages/profile/addresses', '/subpackages/profile/bank',
      '/subpackages/profile/shipping', '/subpackages/profile/settings', '/subpackages/profile/app-download'];
    for (const route of routes) {
      await mobile.goto(base + route);
      await mobile.reload({ waitUntil: 'networkidle' });
      assert.ok(!mobile.url().includes('/pages/login/'), route);
      assert.doesNotMatch(await mobile.locator('body').innerText(), /页面不存在|页面未找到/);
      visited.push(route);
    }
    const products = (await (await mobile.request.get(api + '/app/products?page=1&page_size=1', { headers })).json()).data;
    const product = Array.isArray(products) ? products[0] : products.items?.[0];
    assert.ok(product?.id);
    await mobile.goto(base + '/subpackages/package/detail?id=' + product.id);
    await mobile.reload({ waitUntil: 'networkidle' });
    visited.push('/subpackages/package/detail');
    assert.doesNotMatch(await mobile.locator('body').innerText(), /消费金/);
    const privateOrder = await mobile.request.get(api + '/app/orders/' + fixture.order_ids.CITY_PARTNER, { headers });
    assert.equal(privateOrder.status(), 404, 'A beneficiary cannot read the buyer order');

    const admin = await browser.newPage({ viewport: { width: 1500, height: 1000 } });
    admin.on('pageerror', error => errors.push(error.message));
    await admin.goto('http://127.0.0.1:5173/login');
    await admin.getByPlaceholder('请输入管理员手机号').fill('18800000000');
    await admin.getByPlaceholder('请输入密码', { exact: true }).fill('Admin@123');
    await admin.getByRole('button', { name: '进入后台' }).click();
    await admin.waitForURL('**/dashboard');
    await admin.goto('http://127.0.0.1:5173/users');
    await admin.getByPlaceholder('搜索手机号、昵称、邀请码').fill(fixture.phone);
    await admin.getByRole('button', { name: '查询', exact: true }).click();
    await admin.locator('.el-table__row').filter({ hasText: fixture.phone }).getByRole('button', { name: '详情', exact: true }).click();
    const drawer = admin.getByRole('dialog', { name: '用户详情', exact: true });
    await drawer.getByRole('tab', { name: '资产摘要', exact: true }).click();
    const panel = drawer.getByRole('tabpanel', { name: '资产摘要' });
    const assetNames = await panel.locator('.el-table__body').first().locator('.el-table__row td:first-child').allTextContents();
    assert.deepEqual(assetNames.map(x => x.trim()), ['余额', '佣金', '积分']);
    await drawer.screenshot({ path: path.join(out, 'final-admin-user-currencies.png') });
    assert.deepEqual(errors, []);
    assert.deepEqual(failures, []);
    const result = { visible_currencies: ['余额', '佣金', '积分'], mobile_routes: visited,
      points_entry_selects_points: true, commission_entry_works: true, admin_user_assets_verified: true,
      cross_user_order_access_blocked: true,
      widths: [360, 390, 430], errors, failures };
    fs.writeFileSync(path.join(out, 'final-global-browser-results.json'), JSON.stringify(result, null, 2));
    console.log(JSON.stringify(result));
  } catch (error) {
    console.error(JSON.stringify({ visited, errors, failures }));
    throw error;
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
