// Requires playwright-core installed in the existing local browser test runtime.
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const { chromium } = require(require.resolve('playwright-core', { paths: [path.join(os.tmpdir(), 'excellent-browser-test')] }));
const out = path.resolve(__dirname, '../logs/local-test');
const input = JSON.parse(fs.readFileSync(path.join(out, 'recovery-smoke-input.json'), 'utf8').replace(/^\uFEFF/, ''));
(async () => {
  const browser = await chromium.launch({ executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: true });
  const errors = [], failures = [];
  const observe = p => {
    p.on('pageerror', e => errors.push(e.message));
    p.on('response', r => { if (r.status() >= 400) failures.push({ url: r.url(), status: r.status() }); });
  };
  try {
    const admin = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
    observe(admin);
    await admin.goto('http://127.0.0.1:5173/login');
    await admin.getByPlaceholder('请输入管理员手机号').fill('18800000000');
    await admin.getByPlaceholder('请输入密码', { exact: true }).fill('Admin@123');
    await admin.getByRole('button', { name: '进入后台' }).click();
    await admin.waitForURL('**/dashboard');
    await admin.goto('http://127.0.0.1:5173/commission');
    await admin.getByRole('tab', { name: '待处理订单', exact: true }).click();
    const panel = admin.locator('.panel-card').filter({ has: admin.getByRole('heading', { name: '商品订单待处理', exact: true }) });
    const row = panel.locator('.el-table__row').filter({ hasText: input.order_no });
    await row.waitFor();
    await panel.scrollIntoViewIfNeeded();
    await panel.screenshot({ path: path.join(out, 'recovery-admin-pending.png') });

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
    const detailUrl = `http://127.0.0.1:5174/#/subpackages/order/detail?id=${input.order_id}`;
    await mobile.goto(detailUrl);
    await mobile.getByText('订单待平台处理', { exact: true }).waitFor();
    await mobile.getByText('申请退款', { exact: true }).waitFor();
    await mobile.screenshot({ path: path.join(out, 'recovery-mobile-pending.png') });

    await row.getByRole('button', { name: '申请退款', exact: true }).click();
    const refundResponse = admin.waitForResponse(r => r.url().includes(`/orders/${input.order_id}/refund`) && r.request().method() === 'POST');
    await admin.locator('.el-message-box__btns button').last().click();
    const result = await (await refundResponse).json();
    if (!result.data?.completed) throw new Error('Refund not completed: ' + JSON.stringify(result));
    await row.waitFor({ state: 'hidden' });
    await mobile.reload();
    await mobile.getByText('已退款', { exact: true }).first().waitFor();
    if (await mobile.getByText('订单待平台处理', { exact: true }).count()) throw new Error('Pending notice survived refund');

    const api = 'http://127.0.0.1:8000/api/v1';
    const login = await (await mobile.request.post(api + '/auth/login', { data: { phone: '19900134224', password: 'LocalTest123' } })).json();
    const headers = { Authorization: 'Bearer ' + login.data.access_token };
    const denied = await mobile.request.get(api + '/admin/commission/failed-settlements', { headers });
    if (denied.status() !== 403) throw new Error('Ordinary user could inspect failed settlements');
    const seats = (await (await mobile.request.get(api + '/city-partners/seats', { headers })).json()).data.items;
    const city = seats.find(s => s.id === input.seat_id);
    if (!city?.purchasable || city.current_price !== 1320) throw new Error('Reopened quote incorrect');
    const quoted = await (await mobile.request.post(api + `/city-partners/seats/${city.id}/orders`, { headers, data: { price_version: city.price_version } })).json();
    const paid = await (await mobile.request.post(api + `/app/orders/${quoted.data.id}/pay-demo`, { headers })).json();
    if (paid.data?.order_status !== 'COMPLETED' && paid.data?.status !== 'COMPLETED') throw new Error('Reopened seat payment failed: ' + JSON.stringify(paid));
    if (errors.length || failures.length) throw new Error(JSON.stringify({ errors, failures }));
    const output = { failed_order_id: input.order_id, admin_pending_visible: true, mobile_pending_visible: true,
      refund_completed: true, refunded_notice_cleared: true, ordinary_user_denied: true,
      reopened_seat_order_id: quoted.data.id, reopened_seat_purchase_completed: true, errors, failures };
    fs.writeFileSync(path.join(out, 'recovery-browser-results.json'), JSON.stringify(output, null, 2));
    console.log(JSON.stringify(output));
  } finally { await browser.close(); }
})().catch(e => { console.error(e); process.exit(1); });
