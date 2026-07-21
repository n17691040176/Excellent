<template>
  <view class="confirm-page">
    <view class="page-header">
      <view class="icon-button" @click="goBack">←</view>
      <text class="header-title">确认订单</text>
      <view class="icon-button placeholder" />
    </view>

    <view v-if="loading" class="loading-state">
      <view class="skeleton block" />
      <view class="skeleton block tall" />
      <view class="skeleton block" />
    </view>
    <view v-else-if="failed" class="error-state">
      <text class="error-mark">!</text>
      <text class="error-title">订单信息加载失败</text>
      <text class="error-description">{{ errorMessage }}</text>
      <button class="retry-button" @click="loadData">重新加载</button>
    </view>
    <template v-else>
      <view class="content-stack">
      <view v-if="requiresShipping" class="section-card address-card" @click="openAddresses">
        <view class="section-head">
          <text class="section-title">收货地址</text>
          <text class="section-arrow">›</text>
        </view>
        <template v-if="selectedAddress">
          <view class="address-contact">
            <text>{{ selectedAddress.receiver_name }}</text>
            <text class="contact-phone">{{ selectedAddress.receiver_phone }}</text>
          </view>
          <text class="address-detail">{{ selectedAddress.full_address || fullAddress(selectedAddress) }}</text>
        </template>
        <text v-else class="empty-text">请选择收货地址</text>
      </view>

      <view class="section-card">
        <view class="section-head">
          <text class="section-title">商品</text>
          <text class="section-meta">共 {{ items.length }} 种</text>
        </view>
        <view v-for="item in items" :key="`${item.product_id}-${item.cart_item_id || ''}`" class="goods-row">
          <image v-if="item.image" class="goods-image" :src="item.image" mode="aspectFill" />
          <view v-else class="goods-image goods-placeholder">{{ item.title?.slice(0, 1) || '商' }}</view>
          <view class="goods-info">
            <text class="goods-title">{{ item.title }}</text>
            <text class="goods-meta">¥{{ money(item.price) }} × {{ item.quantity }}</text>
          </view>
          <text class="goods-price">¥{{ money(item.subtotal) }}</text>
        </view>
      </view>

      <view class="section-card">
        <text class="section-title">支付方式</text>
        <view class="payment-list">
          <view
            v-for="option in paymentOptions"
            :key="option.key"
            class="payment-item"
            :class="{ active: selectedPayKey === option.key, disabled: option.available === false }"
            @click="selectPayment(option)"
          >
            <view class="payment-copy">
              <text class="payment-name">{{ option.label }}</text>
              <text class="payment-desc">{{ option.desc }}</text>
            </view>
            <view class="payment-radio" :class="{ checked: selectedPayKey === option.key }">
              <view v-if="selectedPayKey === option.key" class="radio-dot" />
            </view>
          </view>
        </view>
        <view v-if="selectedPayment?.purchase_mode !== 'CASH_ONLY'" class="points-row">
          <view>
            <text class="points-label">积分抵扣</text>
            <text class="points-balance">可用 {{ money(assetSummary.POINTS || 0) }}</text>
          </view>
          <view class="points-control">
            <input v-model="pointsAmount" class="points-input" type="digit" placeholder="0" @blur="refreshPreview" />
            <text>积分</text>
          </view>
        </view>
      </view>

      <view class="section-card amount-card">
        <text class="section-title">金额明细</text>
        <view class="amount-row"><text>商品总额</text><text>¥{{ money(totalAmount) }}</text></view>
        <view v-if="Number(preview.discount_amount || 0) > 0" class="amount-row discount"><text>资产抵扣</text><text>-¥{{ money(preview.discount_amount) }}</text></view>
        <view class="amount-row strong"><text>应付金额</text><text>¥{{ money(preview.cash_due) }}</text></view>
      </view>
      </view>

      <view class="submit-bar">
        <view class="submit-total">
          <text class="submit-label">合计</text>
          <text class="submit-price">¥{{ money(preview.cash_due) }}</text>
        </view>
        <button class="submit-btn" :disabled="submitting" @click="submitOrder">
          {{ submitting ? '提交中...' : '提交订单' }}
        </button>
      </view>
    </template>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue';
import { onLoad, onShow } from '@dcloudio/uni-app';
import { addressApi, assetApi, commerceApi, orderApi, packageApi } from '@/api/modules';
import { pickListPayload } from '@/utils/adapters';
import { requestPayment as requestPlatformPayment } from '@/utils/payment';
import { commonPaymentOptions } from '@/utils/payment-options';

const ORDER_TYPE_MAP = {
  HOT_SALE: 'HOT_SALE_ORDER',
  SELF_OPERATED: 'SELF_OPERATED_ORDER',
  REPURCHASE: 'REPURCHASE_ORDER'
};

const loading = ref(false);
const failed = ref(false);
const errorMessage = ref('');
const submitting = ref(false);
const mode = ref('product');
const productId = ref('');
const quantity = ref(1);
const cartItemIds = ref([]);
const items = ref([]);
const addresses = ref([]);
const assetSummary = ref({});
const selectedAddressId = ref(null);
const selectedPayKey = ref('');
const preferredPayChannel = ref('');
const preferredPurchaseMode = ref('');
const pointsAmount = ref('');
const preview = ref({ total_amount: 0, discount_amount: 0, cash_due: 0 });

const selectedAddress = computed(() => addresses.value.find((item) => Number(item.id) === Number(selectedAddressId.value)) || null);
const selectedProducts = computed(() => items.value.map((item) => item.product || {}));
const zoneType = computed(() => selectedProducts.value[0]?.zone_type || '');
const requiresShipping = computed(() => selectedProducts.value.some((item) => Boolean(item.requires_shipping)));
const totalAmount = computed(() => items.value.reduce((sum, item) => sum + Number(item.subtotal || 0), 0));

const paymentOptions = computed(() => {
  if (!selectedProducts.value.length) return [];
  return commonPaymentOptions(selectedProducts.value).map((item) => {
    const balanceSufficient = item.value !== 'BALANCE'
      || Number(assetSummary.value.BALANCE || 0) >= Number(totalAmount.value || 0);
    return {
      ...item,
      desc: !balanceSufficient ? `${item.desc}（余额不足）` : item.desc,
      available: item.available !== false && balanceSufficient,
      unavailable_reason: !balanceSufficient ? '账户余额不足' : item.unavailable_reason
    };
  });
});

const selectedPayment = computed(() => paymentOptions.value.find((item) => item.key === selectedPayKey.value) || null);

function money(value) {
  return Number(value || 0).toFixed(2);
}

function fullAddress(address) {
  return [address.province, address.city, address.district, address.detail_address].filter(Boolean).join(' ');
}

function normalizeProduct(product, count = 1, cartItemId = null) {
  const price = Number(product.price ?? product.sale_price ?? 0);
  return {
    cart_item_id: cartItemId,
    product_id: product.id || product.product_id,
    quantity: Number(count || 1),
    title: product.title || product.name || product.product_name || '未命名商品',
    image: product.image || product.main_image || product.cover || '',
    price,
    subtotal: price * Number(count || 1),
    product
  };
}

function normalizeCartItem(item) {
  const product = item.product || item;
  const row = normalizeProduct(product, item.quantity, item.id || item.cart_item_id);
  row.product_id = item.product_id || row.product_id;
  row.title = item.title || row.title;
  row.image = item.image || row.image;
  row.subtotal = Number(item.subtotal_amount ?? row.subtotal);
  return row;
}

function buildDeductions() {
  const payment = selectedPayment.value;
  if (!payment) return [];
  const total = Number(totalAmount.value || 0);
  let points = Math.max(0, Number(pointsAmount.value || 0));
  if (payment.purchase_mode === 'CASH_ONLY') points = 0;
  if (payment.purchase_mode === 'POINTS_ONLY') points = total;
  points = Math.min(points, total);
  const rows = [];
  if (points > 0) rows.push({ asset_type: 'POINTS', amount: points });
  const remaining = Math.max(total - points, 0);
  if (payment.value === 'BALANCE' && remaining > 0) rows.push({ asset_type: 'BALANCE', amount: remaining });
  return rows;
}

function buildOrderPayload() {
  const orderType = ORDER_TYPE_MAP[zoneType.value];
  if (!orderType) throw new Error('当前专区暂不支持下单');
  if (!selectedPayment.value || selectedPayment.value.available === false) throw new Error('当前商品没有可用支付方式');
  return {
    order_type: orderType,
    zone_type: zoneType.value,
    address_id: requiresShipping.value ? selectedAddressId.value : null,
    pay_channel: selectedPayment.value.value,
    items: items.value.map((item) => ({ product_id: Number(item.product_id), quantity: Number(item.quantity) })),
    asset_deductions: buildDeductions()
  };
}

function selectInitialPayment() {
  const preferred = paymentOptions.value.find((item) => item.available !== false && (
    item.value === preferredPayChannel.value
    && (!preferredPurchaseMode.value || item.purchase_mode === preferredPurchaseMode.value)
  ));
  const target = preferred || paymentOptions.value.find((item) => item.available !== false);
  selectedPayKey.value = target?.key || '';
}

async function loadAddresses() {
  addresses.value = pickListPayload(await addressApi.list());
  const currentExists = addresses.value.some((item) => Number(item.id) === Number(selectedAddressId.value));
  if (!currentExists) {
    const defaultAddress = addresses.value.find((item) => item.is_default) || addresses.value[0];
    selectedAddressId.value = defaultAddress?.id || null;
  }
}

async function loadAssets() {
  assetSummary.value = await assetApi.summary();
}

async function loadItems() {
  if (mode.value === 'cart') {
    const rows = pickListPayload(await commerceApi.cart());
    items.value = rows.filter((item) => cartItemIds.value.includes(Number(item.id))).map(normalizeCartItem);
  } else {
    const product = await packageApi.detail(productId.value);
    items.value = [normalizeProduct(product, quantity.value)];
  }
  if (!items.value.length) throw new Error('待结算商品不存在');
  const zones = new Set(selectedProducts.value.map((item) => item.zone_type).filter(Boolean));
  if (zones.size !== 1) throw new Error('不支持跨专区合并结算');
  if (!paymentOptions.value.some((item) => item.available !== false)) throw new Error('当前商品没有可用支付方式');
  selectInitialPayment();
}

async function refreshPreview() {
  if (!items.value.length || !selectedPayment.value) return false;
  if (requiresShipping.value && !selectedAddressId.value) {
    preview.value = { total_amount: totalAmount.value, discount_amount: 0, cash_due: totalAmount.value };
    return false;
  }
  try {
    preview.value = await orderApi.preview(buildOrderPayload());
    errorMessage.value = '';
    return true;
  } catch (error) {
    errorMessage.value = error?.message || '订单金额校验失败';
    return false;
  }
}

async function loadData() {
  loading.value = true;
  failed.value = false;
  errorMessage.value = '';
  try {
    await Promise.all([loadAddresses(), loadAssets()]);
    await loadItems();
    await refreshPreview();
  } catch (error) {
    failed.value = true;
    errorMessage.value = error?.message || '订单信息加载失败';
  } finally {
    loading.value = false;
  }
}

async function selectPayment(option) {
  if (option.available === false) {
    uni.showToast({ title: option.unavailable_reason || '该支付方式暂不可用', icon: 'none' });
    return;
  }
  selectedPayKey.value = option.key;
  if (option.purchase_mode === 'CASH_ONLY') pointsAmount.value = '';
  await refreshPreview();
}

function openAddresses() {
  uni.navigateTo({ url: '/subpackages/profile/addresses?select=1' });
}

function goBack() {
  uni.navigateBack();
}

async function submitOrder() {
  if (submitting.value) return;
  if (requiresShipping.value && !selectedAddressId.value) {
    uni.showToast({ title: '请先添加收货地址', icon: 'none' });
    return;
  }
  if (!(await refreshPreview())) {
    uni.showToast({ title: errorMessage.value || '订单校验失败', icon: 'none' });
    return;
  }
  submitting.value = true;
  let createdOrderId = null;
  try {
    const payload = buildOrderPayload();
    let orderId;
    let payment;
    if (mode.value === 'cart') {
      const pointsDeduction = payload.asset_deductions.find((item) => item.asset_type === 'POINTS');
      const result = await commerceApi.checkoutCart({
        item_ids: cartItemIds.value,
        address_id: payload.address_id,
        points_amount: Number(pointsDeduction?.amount || 0),
        pay_channel: payload.pay_channel,
        auto_complete: true
      });
      orderId = result.order_id;
      createdOrderId = orderId;
      payment = result.payment;
    } else {
      const order = await orderApi.create(payload);
      orderId = order.id || order.order_id;
      createdOrderId = orderId;
      if (['WECHAT', 'ALIPAY'].includes(payload.pay_channel)) {
        const result = await orderApi.pay(orderId, { pay_channel: payload.pay_channel, auto_complete: true });
        payment = result?.payment;
      }
    }

    if (payment?.status === 'FAILED') {
      throw new Error(payment.message || '支付参数创建失败');
    }
    if (payment && payment.status !== 'PAID') {
      await requestPlatformPayment(payment);
    }
    uni.showToast({ title: '订单提交成功', icon: 'success' });
    setTimeout(() => uni.redirectTo({ url: `/subpackages/order/detail?id=${orderId}` }), 400);
  } catch (error) {
    const message = String(error?.message || error?.errMsg || '订单提交失败');
    if (createdOrderId) {
      uni.showToast({ title: message.includes('cancel') ? '已取消支付' : '订单已创建，请继续支付', icon: 'none' });
      setTimeout(() => uni.redirectTo({ url: `/subpackages/order/detail?id=${createdOrderId}` }), 400);
    } else {
      uni.showToast({ title: message, icon: 'none' });
    }
  } finally {
    submitting.value = false;
  }
}

onLoad((query) => {
  productId.value = query?.product_id || '';
  quantity.value = Math.max(1, Number(query?.quantity || 1));
  cartItemIds.value = String(query?.cart_item_ids || '').split(',').map(Number).filter(Boolean);
  mode.value = cartItemIds.value.length ? 'cart' : 'product';
  preferredPayChannel.value = query?.pay_channel || '';
  preferredPurchaseMode.value = query?.purchase_mode || '';
  pointsAmount.value = query?.points_amount || '';
  loadData();
});

onShow(() => {
  if (!loading.value && items.value.length) {
    loadAddresses().then(refreshPreview).catch(() => {});
  }
});
</script>

<style scoped>
@import '@/styles/common.css';

.confirm-page {
  min-height: 100vh;
  padding-bottom: calc(144rpx + env(safe-area-inset-bottom));
  background: #F6F7F8;
}

.page-header {
  display: grid;
  grid-template-columns: 64rpx 1fr 64rpx;
  align-items: center;
  min-height: 88rpx;
  padding: env(safe-area-inset-top) 24rpx 0;
  background: #FFFFFF;
  border-bottom: 1rpx solid #ECEEF0;
  box-sizing: content-box;
}

.icon-button {
  width: 64rpx;
  height: 64rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #27272A;
  font-size: 38rpx;
}

.icon-button.placeholder { visibility: hidden; }

.header-title {
  color: #18181B;
  text-align: center;
  font-size: 32rpx;
  font-weight: 700;
}

.content-stack {
  display: flex;
  flex-direction: column;
  gap: 20rpx;
  padding: 20rpx;
}

.section-card {
  padding: 28rpx;
  background: #FFFFFF;
  border: 1rpx solid #E5E7EB;
  border-radius: 16rpx;
  box-sizing: border-box;
}

.section-head,
.amount-row,
.points-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20rpx;
}

.section-head { margin-bottom: 22rpx; }

.section-title {
  display: block;
  color: #18181B;
  font-size: 29rpx;
  font-weight: 700;
}

.section-meta { color: #85858D; font-size: 23rpx; }
.section-arrow { color: #85858D; font-size: 38rpx; line-height: 1; }

.address-contact {
  display: flex;
  align-items: baseline;
  gap: 16rpx;
  color: #27272A;
  font-size: 28rpx;
  font-weight: 700;
}

.contact-phone { color: #71717A; font-size: 25rpx; font-weight: 400; }

.address-detail,
.empty-text {
  display: block;
  margin-top: 10rpx;
  color: #71717A;
  font-size: 25rpx;
  line-height: 1.55;
}

.goods-row {
  display: grid;
  grid-template-columns: 104rpx minmax(0, 1fr) auto;
  align-items: center;
  gap: 18rpx;
  padding: 20rpx 0;
  border-top: 1rpx solid #ECEEF0;
}

.section-head + .goods-row { padding-top: 0; border-top: 0; }
.goods-row:last-child { padding-bottom: 0; }

.goods-image {
  width: 104rpx;
  height: 104rpx;
  background: #F0F2F3;
  border-radius: 12rpx;
}

.goods-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #6B7280;
  font-size: 32rpx;
  font-weight: 700;
}

.goods-info { min-width: 0; }

.goods-title {
  display: -webkit-box;
  overflow: hidden;
  color: #27272A;
  font-size: 27rpx;
  font-weight: 600;
  line-height: 1.4;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.goods-meta { display: block; margin-top: 8rpx; color: #85858D; font-size: 23rpx; }
.goods-price { align-self: start; color: #27272A; font-size: 26rpx; font-weight: 700; }
.section-card > .section-title { margin-bottom: 20rpx; }

.payment-list { border-top: 1rpx solid #ECEEF0; }

.payment-item {
  min-height: 96rpx;
  padding: 18rpx 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20rpx;
  border-bottom: 1rpx solid #ECEEF0;
  box-sizing: border-box;
}

.payment-item.disabled { opacity: 0.48; }
.payment-copy { min-width: 0; display: flex; flex-direction: column; gap: 5rpx; }
.payment-name { color: #27272A; font-size: 27rpx; font-weight: 600; }
.payment-desc { color: #85858D; font-size: 22rpx; }

.payment-radio {
  width: 36rpx;
  height: 36rpx;
  flex: 0 0 36rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2rpx solid #C4C4C8;
  border-radius: 50%;
  box-sizing: border-box;
}

.payment-radio.checked { border-color: #07845D; }
.radio-dot { width: 20rpx; height: 20rpx; background: #07845D; border-radius: 50%; }
.points-row { min-height: 88rpx; padding-top: 16rpx; }
.points-label, .points-balance { display: block; }
.points-label { color: #27272A; font-size: 26rpx; font-weight: 600; }
.points-balance { margin-top: 4rpx; color: #85858D; font-size: 21rpx; }
.points-control { display: flex; align-items: center; gap: 8rpx; color: #71717A; font-size: 23rpx; }

.points-input {
  width: 156rpx;
  height: 64rpx;
  padding: 0 14rpx;
  color: #27272A;
  background: #F5F6F7;
  border: 1rpx solid #E4E4E7;
  border-radius: 10rpx;
  text-align: right;
  box-sizing: border-box;
}

.amount-card { display: flex; flex-direction: column; }
.amount-row { min-height: 64rpx; color: #71717A; font-size: 25rpx; }
.amount-row > text:last-child { color: #27272A; }
.amount-row.discount > text:last-child { color: #047857; }

.amount-row.strong {
  min-height: 80rpx;
  margin-top: 8rpx;
  padding-top: 14rpx;
  border-top: 1rpx solid #E5E7EB;
  color: #18181B;
  font-weight: 700;
}

.amount-row.strong > text:last-child { color: #D55312; font-size: 34rpx; font-weight: 800; }

.submit-bar {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 100;
  min-height: 108rpx;
  padding: 18rpx 24rpx calc(18rpx + env(safe-area-inset-bottom));
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24rpx;
  background: rgba(255, 255, 255, 0.97);
  border-top: 1rpx solid #E5E7EB;
  box-sizing: content-box;
}

.submit-total { display: flex; align-items: baseline; gap: 10rpx; }
.submit-label { color: #71717A; font-size: 23rpx; }
.submit-price { color: #D55312; font-size: 36rpx; font-weight: 800; }

.submit-btn,
.retry-button {
  height: 76rpx;
  margin: 0;
  padding: 0 34rpx;
  color: #FFFFFF;
  background: #07845D;
  border-radius: 12rpx;
  font-size: 27rpx;
  font-weight: 700;
  line-height: 1;
}

.submit-btn { min-width: 224rpx; }
.submit-btn::after, .retry-button::after { border: 0; }
.submit-btn[disabled] { opacity: 0.55; }

.loading-state { padding: 20rpx; }
.skeleton { background: #E9EBED; border-radius: 16rpx; animation: pulse 1.4s ease-in-out infinite; }
.skeleton.block { height: 180rpx; margin-bottom: 20rpx; }
.skeleton.block.tall { height: 320rpx; }

.error-state {
  min-height: 70vh;
  padding: 48rpx;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
}

.error-mark {
  width: 72rpx;
  height: 72rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #A33A34;
  background: #FBE9E7;
  border-radius: 50%;
  font-size: 38rpx;
  font-weight: 800;
}

.error-title { margin-top: 24rpx; color: #27272A; font-size: 30rpx; font-weight: 700; }
.error-description { margin-top: 10rpx; color: #71717A; font-size: 25rpx; }
.retry-button { margin-top: 28rpx; }

@keyframes pulse {
  0%, 100% { opacity: 0.65; }
  50% { opacity: 1; }
}

@media (prefers-reduced-motion: reduce) {
  .skeleton { animation: none; }
}
</style>
