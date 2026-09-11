const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const { chromium } = require(require.resolve('playwright-core', { paths: [path.join(os.tmpdir(), 'excellent-browser-test')] }));
const out = path.resolve(__dirname, '../logs/local-test');
const api = 'http://127.0.0.1:8000/api/v1';
(async () => {
  const browser = await chromium.launch({ executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: true });
  const errors = [], failures = [];
  function observe(page) {
    page.on('pageerror', e => errors.push(e.message));
    page.on('response', r => { if (r.status() >= 400) failures.push({ url: r.url(), status: r.status() }); });
  }
  try {
    const page = await browser.newPage({ viewport: { width: 1500, height: 1000 } });
    observe(page);
    const login = await (await page.request.post(api + '/auth/admin-login', { data: { phone: '18800000000', password: 'Admin@123' } })).json();
    const headers = { Authorization: 'Bearer ' + login.data.access_token };
    async function call(method, route, data, expected = 200, auth = headers) {
      const response = await page.request[method](api + route, { headers: auth, data });
      const body = await response.json();
      if (response.status() !== expected) throw new Error(route + ': ' + JSON.stringify(body));
      return body.data;
    }
    const suffix = Date.now().toString();
    const category = await call('post', '/admin/categories', { name: '隔离验收-' + suffix, slug: 'isolation-' + suffix });
    const product = await call('post', '/admin/products', { product_name: 'isolation-ui-' + suffix, product_type: 'PHYSICAL',
      zone_type: 'SELF_OPERATED', owner_type: 'SELF_OPERATED', category_id: category.id, sale_price: '1700.00', cost_price: '710.00', stock: 10, requires_shipping: true });
    const ruleUrl = `/admin/products/${product.id}/zone-config`;
    let rules = await call('put', ruleUrl, { city_partner_commission_enabled: true, city_partner_amount: '100', city_partner_direct_reward_amount: '300',
      custom_commission_enabled: true, custom_commission_method: 'FIXED_AMOUNT', custom_commission_level1_enabled: true, custom_commission_level1_amount: 8 });
    if (rules.city_partner_upline_initial_amount !== 150 || rules.city_partner_upline_max_levels !== 7 || rules.city_partner_upline_decay_rate !== 50) throw new Error('Derived rule mismatch');
    await call('put', ruleUrl, { city_partner_upline_initial_amount: 999 }, 422);
    await call('put', ruleUrl, { city_partner_direct_reward_amount: 800 }, 409);

    await page.goto('http://127.0.0.1:5173/login');
    await page.getByPlaceholder('请输入管理员手机号').fill('18800000000');
    await page.getByPlaceholder('请输入密码', { exact: true }).fill('Admin@123');
    await page.getByRole('button', { name: '进入后台' }).click();
    await page.waitForURL('**/dashboard');
    await page.goto('http://127.0.0.1:5173/products');
    await page.getByPlaceholder('搜索商品名称 / 品牌').fill(product.product_name);
    await page.getByPlaceholder('搜索商品名称 / 品牌').press('Enter');
    const row = page.locator('.el-table__row').filter({ hasText: product.product_name });
    await row.first().getByRole('button', { name: '编辑', exact: true }).click();
    const editor = page.locator('.el-drawer').filter({ hasText: '编辑商品' });
    await editor.locator('.el-form-item').filter({ hasText: '售价' }).getByRole('spinbutton').fill('1600');
    const costInput = editor.locator('.el-form-item').filter({ hasText: '成本价' }).getByRole('spinbutton');
    await costInput.fill('700');
    await costInput.press('Tab');
    const productSaved = page.waitForResponse(r => r.url().endsWith(`/admin/products/${product.id}`) && r.request().method() === 'PUT');
    await editor.getByRole('button', { name: '保存商品', exact: true }).click();
    const productSaveResponse = await productSaved;
    if (productSaveResponse.status() !== 200) throw new Error('Manual product prices UI save failed');
    await editor.waitFor({ state: 'hidden' });
    const pricedProduct = (await productSaveResponse.json()).data;
    if (Number(pricedProduct.sale_price) !== 1600 || Number(pricedProduct.cost_price) !== 700) throw new Error('Manual prices did not persist');
    await row.first().getByRole('button', { name: '更多' }).click();
    await page.getByRole('menuitem', { name: '规则配置', exact: true }).click();
    const drawer = page.locator('.el-drawer').filter({ hasText: '直推奖金额' });
    await drawer.getByText('七层分润明细', { exact: true }).waitFor();
    for (const label of ['上级第 1 层金额', '上级层数', '层级递减比例']) {
      if (await drawer.locator('.el-form-item').filter({ hasText: label }).getByRole('spinbutton').count()) throw new Error(label + ' is still editable');
    }
    const direct = drawer.locator('.el-form-item').filter({ hasText: '直推奖金额' }).getByRole('spinbutton');
    const cityAmount = drawer.locator('.el-form-item').filter({ hasText: '城市合伙人金额' }).getByRole('spinbutton');
    await cityAmount.fill('100');
    await cityAmount.press('Tab');
    await direct.fill('400');
    await direct.press('Tab');
    await drawer.locator('summary').filter({ hasText: '七层分润明细' }).click();
    if (JSON.stringify(await drawer.locator('.layer-row strong').allTextContents()) !== JSON.stringify(['¥200.00', '¥100.00', '¥50.00', '¥25.00', '¥12.50', '¥6.25', '¥3.12'])) throw new Error('Seven layer preview mismatch');
    await drawer.locator('summary').filter({ hasText: '七层分润明细' }).click();
    await drawer.locator('.config-head h3').click();
    await drawer.screenshot({ path: path.join(out, 'isolation-product-rules.png') });
    // Another administrator edits the old rule while this drawer stays open.
    await call('put', ruleUrl, { custom_commission_level1_amount: 11 });
    const saved = page.waitForResponse(r => r.url().endsWith(ruleUrl) && r.request().method() === 'PUT');
    await drawer.getByRole('button', { name: '保存规则' }).click();
    if ((await saved).status() !== 200) throw new Error('Rule UI save failed');
    rules = await call('get', ruleUrl);
    if (rules.city_partner_direct_reward_amount !== 400 || rules.custom_commission_level1_amount !== 11) throw new Error('Stale drawer overwrote concurrent old-rule edit');
    await drawer.waitFor({ state: 'hidden' });
    await row.first().getByRole('button', { name: '更多' }).click();
    await page.getByRole('menuitem', { name: '规则配置', exact: true }).click();
    const oldAmount = drawer.locator('.member-commission-row').filter({ hasText: '普通会员' }).getByRole('spinbutton');
    await oldAmount.fill('9');
    await oldAmount.press('Tab');
    // Verify the reverse direction: saving the old rule preserves a new-rule edit.
    await call('put', ruleUrl, { city_partner_direct_reward_amount: 350 });
    const oldSaved = page.waitForResponse(r => r.url().endsWith(ruleUrl) && r.request().method() === 'PUT');
    await drawer.getByRole('button', { name: '保存规则' }).click();
    if ((await oldSaved).status() !== 200) throw new Error('Old rule UI save failed');
    rules = await call('get', ruleUrl);
    if (rules.custom_commission_level1_amount !== 9 || rules.city_partner_direct_reward_amount !== 350) throw new Error('Stale drawer overwrote concurrent new-rule edit');
    rules = await call('put', ruleUrl, { city_partner_direct_reward_amount: 400 });
    if (rules.custom_commission_level1_amount !== 9) throw new Error('New rule patch reset old rule');
    const mode = await call('get', '/admin/commission/mode');
    const opposite = mode.mode === 'ORIGINAL' ? 'CITY_PARTNER' : 'ORIGINAL';
    try {
      await call('put', '/admin/commission/mode', { mode: opposite, reason: '本地隔离验收' });
      const switchedRules = await call('get', ruleUrl);
      if (switchedRules.custom_commission_level1_amount !== 9 || switchedRules.city_partner_direct_reward_amount !== 400) throw new Error('Switch rewrote product rules');
    } finally { await call('put', '/admin/commission/mode', { mode: mode.mode, reason: '恢复验收前模式' }); }

    const adminRoutes = ['/dashboard', '/users', '/teams', '/products', '/categories', '/orders', '/region-stats', '/commission', '/withdraws', '/decorations/home', '/local-life', '/invites', '/shipments', '/system/earning-rules', '/system/admins', '/system/roles', '/profile'];
    for (const route of adminRoutes) {
      await page.goto('http://127.0.0.1:5173' + route);
      await page.waitForLoadState('networkidle');
      if (page.url().includes('/403') || page.url().includes('/login')) throw new Error('Admin route unavailable: ' + route);
    }
    await page.goto('http://127.0.0.1:5173/commission');
    await page.waitForLoadState('networkidle');
    await page.screenshot({ path: path.join(out, 'simple-admin-commission.png') });
    await page.getByRole('tab', { name: '城市合伙人', exact: true }).click();
    await page.locator('.province-card').filter({ hasText: '陕西省' }).click();
    await page.getByPlaceholder('搜索省内城市或合伙人').fill('西安市');
    await page.waitForTimeout(250);
    await page.screenshot({ path: path.join(out, 'simple-admin-cities.png') });
    await page.getByRole('tab', { name: '待处理订单', exact: true }).click();
    await page.getByRole('heading', { name: '商品订单待处理', exact: true }).waitFor();
    await page.getByRole('button', { name: '模式设置', exact: true }).click();
    await page.locator('.el-drawer').filter({ hasText: '分润模式设置' }).getByText('配置检查', { exact: true }).waitFor();
    await page.locator('.el-drawer').filter({ hasText: '分润模式设置' }).screenshot({ path: path.join(out, 'simple-admin-mode-settings.png') });
    await page.locator('.el-drawer').filter({ hasText: '分润模式设置' }).getByRole('button', { name: '取消', exact: true }).click();

    const ordinary = await call('post', '/auth/login', { phone: '19900134224', password: 'LocalTest123' });
    const userHeaders = { Authorization: 'Bearer ' + ordinary.access_token };
    const seats = (await call('get', '/city-partners/seats', undefined, 200, userHeaders)).items;
    const own = seats.find(s => s.is_current_holder);
    if (!own || own.purchasable) throw new Error('Owned seat is purchasable');
    await call('post', `/city-partners/seats/${own.id}/orders`, { price_version: own.price_version }, 409, userHeaders);
    const standardSeat = { province: '陕西省', city: '西安市', initial_price: 1000 };
    const existingStandardSeat = seats.find(s => s.province === standardSeat.province && s.city === standardSeat.city);
    if (!existingStandardSeat) await call('post', '/admin/city-partners', standardSeat);
    await call('post', '/admin/city-partners', standardSeat, 409);

    const mobile = await browser.newPage({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
    observe(mobile);
    await mobile.goto('http://127.0.0.1:5174/#/pages/login/index');
    await mobile.locator('input.uni-input-input').nth(0).fill('19900134224');
    const codeResponse = mobile.waitForResponse(r => r.url().includes('/auth/send-login-code'));
    await mobile.getByText('获取验证码', { exact: true }).click();
    const code = (await (await codeResponse).json()).data.debug_code;
    if (!code) throw new Error('Local mock SMS required');
    await mobile.locator('input.uni-input-input').nth(1).fill(code);
    if (!(await mobile.locator('.agreement-check').getAttribute('class')).includes('checked')) await mobile.locator('.agreement-check').click();
    await mobile.locator('.login-btn').click();
    await mobile.waitForURL('**/pages/home/index');
    await mobile.goto('http://127.0.0.1:5174/#/subpackages/profile/city-partners');
    await mobile.locator('.province-card').filter({ hasText: own.province }).click();
    const card = mobile.locator('.seat-card').filter({ hasText: own.city }).first();
    await card.waitFor();
    const ownButton = card.locator('uni-button').filter({ hasText: '已持有' });
    await ownButton.waitFor();
    if (await ownButton.getAttribute('disabled') !== 'true') throw new Error('Self replacement UI not disabled');
    await ownButton.click();
    if (await mobile.getByText('确认购买', { exact: true }).count()) throw new Error('Disabled seat opened purchase confirmation');
    await card.screenshot({ path: path.join(out, 'isolation-owned-seat.png') });
    await mobile.getByText('我的城市', { exact: true }).click();
    await mobile.locator('.province-card').filter({ hasText: own.province }).click();
    await mobile.locator('.seat-card').first().waitFor();
    if (await mobile.locator('.buy-button:not([disabled])').count()) throw new Error('Owned city filter contains purchasable seats');
    await mobile.screenshot({ path: path.join(out, 'simple-mobile-my-cities.png') });
    await mobile.getByText('规则', { exact: true }).click();
    await mobile.locator('.uni-modal__title').filter({ hasText: '城市合伙人规则' }).waitFor();
    await mobile.getByText('确定', { exact: true }).click();
    await mobile.getByText('全部城市', { exact: true }).click();
    await mobile.locator('.province-card').filter({ hasText: '陕西省' }).click();
    await mobile.locator('input').fill('西安市');
    await mobile.screenshot({ path: path.join(out, 'simple-mobile-cities.png') });
    for (const width of [360, 390, 430]) {
      await mobile.setViewportSize({ width, height: 844 });
      const overflow = await mobile.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
      if (overflow) throw new Error('City page overflows at ' + width);
    }
    for (const [route, name] of [['/subpackages/commission/index', 'commission'], ['/subpackages/assets/index', 'assets'], ['/pages/profile/index', 'profile'], ['/pages/orders/list', 'orders']]) {
      await mobile.goto('http://127.0.0.1:5174/#' + route);
      await mobile.waitForLoadState('networkidle');
      await mobile.screenshot({ path: path.join(out, 'simple-mobile-' + name + '.png') });
    }
    if (errors.length || failures.length) throw new Error(JSON.stringify({ errors, failures }));
    const result = { product_id: product.id, manual_prices_saved: true, derived_layers_readonly: true, rule_ui_save: true,
      tampering_rejected: true, overpayment_rule_rejected: true, partial_updates_isolated: true, stale_drawer_both_directions_isolated: true, mode_restored: mode.mode,
      self_replacement_blocked: true, duplicate_city_blocked: true, own_seat_button_disabled: true,
      admin_routes_verified: adminRoutes.length, mobile_finance_routes_verified: 5, mobile_widths_verified: [360, 390, 430], errors, failures };
    fs.writeFileSync(path.join(out, 'isolation-browser-results.json'), JSON.stringify(result, null, 2));
    console.log(JSON.stringify(result));
  } finally { await browser.close(); }
})().catch(e => { console.error(e); process.exit(1); });
