<template>
  <view class="confirm-page">
    <view class="page-header">
      <view class="back-btn" @click="goBack">←</view>
      <text class="header-title">确认订单</text>
      <view class="header-spacer" />
    </view>

    <view v-if="loading" class="state-card">订单信息加载中...</view>
    <view v-else-if="failed" class="state-card">
      <text>{{ errorMessage || '订单信息加载失败' }}</text>
      <button class="text-btn" @click="loadData">重新加载</button>
    </view>
    <template v-else>
      <view v-if="requiresShipping" class="section-card address-card" @click="openAddresses">
        <view class="section-head">
          <text class="section-title">收货地址</text>
          <text class="section-link">{{ selectedAddress ? '管理地址' : '添加地址' }}</text>
        </view>
        <template v-if="selectedAddress">
          <text class="address-contact">{{ selectedAddress.receiver_name }} {{ selectedAddress.receiver_phone }}</text>
          <text class="address-detail">{{ selectedAddress.full_address || fullAddress(selectedAddress) }}</text>
        </template>
        <text v-else class="empty-text">请先添加收货地址</text>
      </view>

      <view class="section-card">
        <text class="section-title">商品清单</text>
        <view v-for="item in items" :key="`${item.product_id}-${item.cart_item_id || ''}`" class="goods-row">
          <image v-if="item.image" class="goods-image" :src="item.image" mode="aspectFill" />
          <view v-else class="goods-image placeholder" />
          <view class="goods-info">
            <text class="goods-title">{{ item.title }}</text>
            <text class="goods-meta">数量 {{ item.quantity }}</text>
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
            <view>
              <text class="payment-name">{{ option.label }}</text>
              <text class="payment-desc">{{ option.desc }}</text>
            </view>
            <text class="payment-check">{{ selectedPayKey === option.key ? '✓' : '' }}</text>
          </view>
        </view>
        <view v-if="selectedPayment?.purchase_mode !== 'CASH_ONLY'" class="points-row">
          <text>积分抵扣</text>
          <input v-model="pointsAmount" class="points-input" type="digit" placeholder="0" @blur="refreshPreview" />
        </view>
      </view>

      <view class="section-card amount-card">
        <view class="amount-row"><text>商品总额</text><text>¥{{ money(totalAmount) }}</text></view>
        <view class="amount-row"><text>资产抵扣</text><text>-¥{{ money(preview.discount_amount) }}</text></view>
        <view class="amount-row strong"><text>应付金额</text><text>¥{{ money(preview.cash_due) }}</text></view>
      </view>

      <view class="submit-space" />
      <view class="submit-bar">
        <view class="submit-total">
          <text>应付：</text>
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
@import '@/styles/elegant.css';

.confirm-page { min-height: 100vh; background: var(--bg); padding-bottom: 140rpx; }
.page-header { display: flex; align-items: center; justify-content: space-between; padding: 24rpx 32rpx; padding-top: calc(24rpx + env(safe-area-inset-top)); background: var(--card); border-bottom: 1rpx solid var(--border-light); }
.back-btn, .header-spacer { width: 64rpx; }
.header-title { font-size: 32rpx; font-weight: 700; color: var(--text); }
.state-card, .section-card { margin: 24rpx; padding: 28rpx; background: var(--card); border-radius: var(--radius-xl); border: 1rpx solid var(--border-light); }
.state-card { text-align: center; color: var(--text-muted); }
.text-btn { margin-top: 20rpx; color: var(--primary); background: transparent; }
.section-head, .amount-row, .points-row { display: flex; align-items: center; justify-content: space-between; gap: 20rpx; }
.section-title { display: block; margin-bottom: 22rpx; font-size: 28rpx; font-weight: 700; color: var(--text); }
.section-head .section-title { margin-bottom: 0; }
.section-link { color: var(--primary); font-size: 24rpx; }
.address-contact { display: block; margin-top: 20rpx; font-weight: 700; color: var(--text); }
.address-detail, .empty-text { display: block; margin-top: 10rpx; color: var(--text-muted); line-height: 1.6; }
.goods-row { display: flex; align-items: center; gap: 20rpx; padding: 18rpx 0; border-bottom: 1rpx solid var(--border-light); }
.goods-row:last-child { border-bottom: 0; }
.goods-image { width: 96rpx; height: 96rpx; border-radius: var(--radius-lg); background: var(--bg); }
.goods-info { flex: 1; min-width: 0; }
.goods-title { display: block; color: var(--text); font-weight: 600; }
.goods-meta { display: block; margin-top: 10rpx; color: var(--text-muted); font-size: 24rpx; }
.goods-price { color: var(--error); font-weight: 700; }
.payment-list { display: grid; gap: 16rpx; }
.payment-item { display: flex; justify-content: space-between; align-items: center; padding: 20rpx; border: 1rpx solid var(--border-light); border-radius: var(--radius-lg); }
.payment-item.active { border-color: var(--primary); background: var(--primary-bg); }
.payment-item.disabled { opacity: 0.55; }
.payment-name, .payment-desc { display: block; }
.payment-name { color: var(--text); font-weight: 600; }
.payment-desc { margin-top: 8rpx; color: var(--text-muted); font-size: 22rpx; }
.payment-check { color: var(--primary); font-weight: 700; }
.points-row { margin-top: 20rpx; padding-top: 20rpx; border-top: 1rpx solid var(--border-light); }
.points-input { width: 200rpx; text-align: right; }
.amount-card { display: grid; gap: 18rpx; }
.amount-row { color: var(--text-muted); }
.amount-row.strong { color: var(--text); font-weight: 700; }
.submit-space { height: 120rpx; }
.submit-bar { position: fixed; left: 0; right: 0; bottom: 0; display: flex; align-items: center; justify-content: space-between; gap: 24rpx; padding: 20rpx 32rpx calc(20rpx + env(safe-area-inset-bottom)); background: var(--card); border-top: 1rpx solid var(--border-light); z-index: 50; }
.submit-total { color: var(--text-muted); }
.submit-price { color: var(--error); font-size: 34rpx; font-weight: 800; }
.submit-btn { min-width: 240rpx; margin: 0; color: white; background: var(--primary); border-radius: 999rpx; }
</style>
