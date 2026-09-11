const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const assert = require('node:assert/strict');
const { chromium } = require(require.resolve('playwright-core', { paths: [path.join(os.tmpdir(), 'excellent-browser-test')] }));
const api = 'http://127.0.0.1:8000/api/v1';
const mobileUrl = 'http://127.0.0.1:5174/#';
const out = path.resolve(__dirname, '../logs/local-test');

(async () => {
  const browser = await chromium.launch({ executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: true });
  const page = await browser.newPage({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  let initialMode, headers;
  async function call(method, route, data, auth = headers, expected = 200) {
    const response = await page.request[method](api + route, { data, headers: auth });
    const body = await response.json();
    assert.equal(response.status(), expected, route + ': ' + JSON.stringify(body));
    return body.data;
  }
  async function mode(value) {
    await call('put', '/admin/commission/mode', { mode: value, reason: '本地验证移动端城市合伙人开关' });
  }
  try {
    const admin = await call('post', '/auth/admin-login', { phone: '18800000000', password: 'Admin@123' }, {});
    headers = { Authorization: 'Bearer ' + admin.access_token };
    initialMode = (await call('get', '/admin/commission/mode')).mode;
    const user = await call('post', '/auth/login', { phone: '19900134224', password: 'LocalTest123' }, {});
    const userHeaders = { Authorization: 'Bearer ' + user.access_token };
    await mode('CITY_PARTNER');
    const seats = (await call('get', '/city-partners/seats', undefined, userHeaders)).items;
    assert.ok(seats.length);

    await page.goto(mobileUrl + '/pages/login/index');
    await page.locator('input.uni-input-input').nth(0).fill('19900134224');
    const codeResponse = page.waitForResponse(r => r.url().includes('/auth/send-login-code'));
    await page.getByText('获取验证码', { exact: true }).click();
    const code = (await (await codeResponse).json()).data.debug_code;
    assert.ok(code, 'Local mock SMS required');
    await page.locator('input.uni-input-input').nth(1).fill(code);
    if (!(await page.locator('.agreement-check').getAttribute('class')).includes('checked')) await page.locator('.agreement-check').click();
    await page.locator('.login-btn').click();
    await page.waitForURL('**/pages/home/index');
    await page.goto(mobileUrl + '/pages/profile/index');
    const entry = page.locator('.menu-item').filter({ hasText: '城市合伙人' });
    await entry.waitFor();

    await mode('ORIGINAL');
    await entry.waitFor({ state: 'hidden', timeout: 22000 });
    const availability = await page.request.get(api + '/city-partners/availability');
    assert.equal(availability.headers()['cache-control'], 'no-store');
    assert.equal((await availability.json()).data.enabled, false);
    assert.deepEqual(await call('get', '/city-partners/seats', undefined, userHeaders), { enabled: false, items: [], total: 0 });
    await call('post', `/city-partners/seats/${seats[0].id}/orders`, { price_version: seats[0].price_version }, userHeaders, 409);
    await page.screenshot({ path: path.join(out, 'availability-original-profile.png') });

    await page.goto(mobileUrl + '/subpackages/profile/city-partners');
    await page.getByText('暂未开放', { exact: true }).waitFor();
    await page.waitForLoadState('networkidle');
    assert.equal(await page.locator('.seat-card, .seat-toolbar, .header-action').count(), 0);
    await page.screenshot({ path: path.join(out, 'availability-closed-page.png') });

    await mode('CITY_PARTNER');
    await page.locator('.seat-card').first().waitFor({ timeout: 22000 });
    await mode('ORIGINAL');
    await page.getByText('暂未开放', { exact: true }).waitFor({ timeout: 22000 });
    assert.equal(await page.locator('.seat-card, .seat-toolbar, .header-action').count(), 0);

    await mode('CITY_PARTNER');
    await page.goto(mobileUrl + '/pages/profile/index');
    await entry.waitFor();
    await entry.click();
    await page.locator('.seat-card').first().waitFor();
    assert.deepEqual(errors, []);
    const result = { profile_follows_mode_without_reload: true, direct_page_closed: true,
      visible_seat_page_closes_and_reopens: true, seat_api_hides_content: true,
      new_orders_blocked: true, reenabled_entry_works: true, original_mode: initialMode, errors };
    fs.writeFileSync(path.join(out, 'availability-browser-results.json'), JSON.stringify(result, null, 2));
    console.log(JSON.stringify(result));
  } finally {
    try { if (initialMode) await mode(initialMode); }
    finally { await browser.close(); }
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
