<template>
  <view class="cart-page">
    <!-- Header -->
    <view class="page-header">
      <view class="header-content">
        <AppBackButton @click="goBack" />
        <view class="logo-mark">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
            <circle cx="9" cy="21" r="1" stroke="white" stroke-width="2"/>
            <circle cx="20" cy="21" r="1" stroke="white" stroke-width="2"/>
            <path d="M1 1H5L7.68 14.39C7.77 14.83 8.01 15.22 8.37 15.47C8.73 15.72 9.17 15.84 9.62 15.83H20" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </view>
        <text class="page-title">购物车</text>
        <view class="header-badge">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" fill="currentColor"/>
          </svg>
          实时
        </view>
      </view>
    </view>

    <!-- Loading -->
    <view v-if="loading" class="loading-state">
      <view v-for="i in 3" :key="i" class="skeleton-item">
        <view class="skeleton skeleton-checkbox" />
        <view class="skeleton skeleton-image" />
        <view class="skeleton-info">
          <view class="skeleton skeleton-title" />
          <view class="skeleton skeleton-price" />
        </view>
      </view>
    </view>

    <!-- Error -->
    <view v-else-if="failed" class="error-state">
      <text class="error-icon">⚠</text>
      <text class="error-text">购物车加载失败</text>
      <view class="retry-btn" @click="loadData">点击重试</view>
    </view>

    <!-- Empty -->
    <view v-else-if="!items.length" class="empty-state">
      <text class="empty-icon">◇</text>
      <text class="empty-title">购物车还是空的</text>
      <text class="empty-desc">去商品详情页加入购物车</text>
      <view class="empty-btn" @click="goShopping">去逛逛</view>
    </view>

    <!-- Cart Items -->
    <template v-else>
      <view class="cart-list">
        <view v-for="item in items" :key="item.id" class="cart-item">
          <view class="select-box" :class="{ active: item.selected }" @click="toggleSelected(item)">
            <text v-if="item.selected">✓</text>
          </view>
          <view class="goods-image" @click="goDetail(item.product_id)">
            <image v-if="item.image || item.product?.image" class="image" :src="item.image || item.product?.image" mode="aspectFill" />
            <view v-else class="image-placeholder" />
          </view>
          <view class="goods-info">
            <text class="goods-title" @click="goDetail(item.product_id)">{{ item.title || item.product?.title }}</text>
            <text class="goods-desc">{{ item.product?.desc || '购物车商品' }}</text>
            <text class="goods-zone">{{ zoneText(item.zone_type || item.product?.zone_type) }}</text>
            <view class="goods-footer">
              <text class="goods-price">¥{{ money(item.price) }}</text>
              <view class="stepper">
                <view class="step-btn" @click="changeQuantity(item, -1)">−</view>
                <text class="step-value">{{ item.quantity }}</text>
                <view class="step-btn" @click="changeQuantity(item, 1)">+</view>
              </view>
            </view>
            <view class="goods-sub">
              <text class="subtotal">小计 ¥{{ money(item.subtotal_amount) }}</text>
              <view class="remove-btn" @click="removeItem(item.id)">移除</view>
            </view>
          </view>
        </view>
      </view>

      <!-- Payment Options -->
      <view class="pay-card">
        <text class="section-title">结算方式</text>
        <view class="pay-options">
          <view
            v-for="item in paymentOptions"
            :key="item.key"
            class="pay-option"
            :class="{ active: selectedPayKey === item.key, disabled: item.available === false }"
            @click="selectPaymentOption(item)"
          >
            <text class="pay-title">{{ item.label }}</text>
            <text class="pay-desc">{{ item.desc }}</text>
          </view>
        </view>

        <view class="points-box">
          <view class="points-info">
            <text class="points-title">积分抵扣</text>
            <text class="points-desc">积分可与余额、消费金组合使用</text>
          </view>
          <input class="points-input" v-model="pointsAmount" type="digit" placeholder="0" />
        </view>

        <view class="summary-list">
          <view class="summary-line">
            <text>已选商品</text>
            <text>{{ selectedCount }} 件</text>
          </view>
          <view class="summary-line">
            <text>商品金额</text>
            <text>¥{{ totalAmount }}</text>
          </view>
          <view class="summary-line">
            <text>积分抵扣</text>
            <text>-¥{{ normalizedPoints }}</text>
          </view>
          <view class="summary-line strong">
            <text>{{ cashLabel }}</text>
            <text>¥{{ cashAmount }}</text>
          </view>
        </view>
      </view>

      <!-- Submit Bar -->
      <view class="submit-bar">
        <view class="submit-info">
          <text class="submit-label">已选 {{ selectedCount }} 件</text>
          <text class="submit-price">¥{{ cashAmount }}</text>
        </view>
        <view class="submit-btn" :class="{ disabled: checkingOut }" @click="checkout">
          {{ checkingOut ? '支付中...' : '支付结算' }}
        </view>
      </view>
    </template>
  </view>
</template>

<script setup>
import { computed, ref, watch } from 'vue';
import { onShow } from '@dcloudio/uni-app';
import { commerceApi } from '@/api/modules';
import { pickListPayload } from '@/utils/adapters';
import { commonPaymentOptions } from '@/utils/payment-options';

const loading = ref(false);
const failed = ref(false);
const checkingOut = ref(false);
const items = ref([]);
const pointsAmount = ref('');
const payChannel = ref('BALANCE');
const purchaseMode = ref('CASH_ONLY');
const selectedPayKey = ref('');

const selectedItems = computed(() => items.value.filter((item) => item.selected));
const selectedProducts = computed(() => selectedItems.value.map((item) => item.product || {}).filter(Boolean));
const selectedZones = computed(() => Array.from(new Set(selectedProducts.value.map((item) => item.zone_type).filter(Boolean))));

const paymentOptions = computed(() => {
  if (!selectedProducts.value.length) return [];
  if (selectedZones.value.length > 1) return [];
  return commonPaymentOptions(selectedProducts.value);
});

const selectedPaymentOption = computed(() => paymentOptions.value.find((item) => item.key === selectedPayKey.value) || paymentOptions.value[0] || null);
const selectedCount = computed(() => selectedItems.value.length);
const totalAmount = computed(() => selectedItems.value.reduce((sum, item) => sum + Number(item.subtotal_amount || 0), 0).toFixed(2));
const normalizedPoints = computed(() => {
  const option = selectedPaymentOption.value;
  if (!option || option.purchase_mode === 'CASH_ONLY') return '0.00';
  if (option.purchase_mode === 'POINTS_ONLY') return Number(totalAmount.value).toFixed(2);
  const amount = Math.max(0, Number(pointsAmount.value || 0));
  const maxPoints = Math.max(0, Number(totalAmount.value) - 0.01);
  return Math.min(amount, maxPoints).toFixed(2);
});
const cashAmount = computed(() => Math.max(0, Number(totalAmount.value) - Number(normalizedPoints.value)).toFixed(2));
const cashLabel = computed(() => ({
  BALANCE: '余额支付',
  WECHAT: '微信支付',
  ALIPAY: '支付宝支付'
}[payChannel.value] || '现金支付'));

watch(
  paymentOptions,
  (options) => {
    if (!options.length) return;
    if (!options.some((item) => item.key === selectedPayKey.value)) {
      selectPaymentOption(options.find((item) => item.available !== false) || options[0]);
    }
  },
  { immediate: true }
);

function selectPaymentOption(option) {
  if (option.available === false) {
    uni.showToast({ title: option.unavailable_reason || '该支付方式暂不可用', icon: 'none' });
    return;
  }
  selectedPayKey.value = option.key;
  payChannel.value = option.value;
  purchaseMode.value = option.purchase_mode;
  if (option.purchase_mode !== 'POINTS_CASH') {
    pointsAmount.value = '';
  }
}

function money(value) {
  return Number(value || 0).toFixed(2);
}

function zoneText(value) {
  return {
    HOT_SALE: '爆款专区',
    SELF_OPERATED: '自营专区',
    REPURCHASE: '复购专区',
    LOCAL_LIFE: '本地生活'
  }[value] || '商品专区';
}

function goBack() {
  uni.navigateBack();
}

function goShopping() {
  uni.switchTab({ url: '/pages/packages/list' });
}

function goDetail(productId) {
  uni.navigateTo({ url: `/subpackages/package/detail?id=${productId}` });
}

async function loadData() {
  loading.value = true;
  failed.value = false;
  try {
    const res = await commerceApi.cart();
    items.value = pickListPayload(res);
  } catch (error) {
    failed.value = true;
  } finally {
    loading.value = false;
  }
}

async function toggleSelected(item) {
  try {
    const updated = await commerceApi.updateCartItem(item.id, { selected: !item.selected });
    items.value = items.value.map((row) => (row.id === item.id ? updated : row));
  } catch (error) {
    uni.showToast({ title: '更新失败，请稍后重试', icon: 'none' });
  }
}

async function changeQuantity(item, delta) {
  const quantity = Math.max(1, Number(item.quantity || 1) + delta);
  try {
    const updated = await commerceApi.updateCartItem(item.id, { quantity });
    items.value = items.value.map((row) => (row.id === item.id ? updated : row));
  } catch (error) {
    uni.showToast({ title: '数量更新失败', icon: 'none' });
  }
}

async function removeItem(itemId) {
  try {
    await commerceApi.removeCartItem(itemId);
    items.value = items.value.filter((item) => item.id !== itemId);
    uni.showToast({ title: '已移除', icon: 'none' });
  } catch (error) {
    uni.showToast({ title: '移除失败，请稍后重试', icon: 'none' });
  }
}

async function checkout() {
  if (!selectedItems.value.length) {
    uni.showToast({ title: '请选择要下单的商品', icon: 'none' });
    return;
  }
  if (selectedZones.value.length > 1) {
    uni.showToast({ title: '暂不支持跨专区一起结算', icon: 'none' });
    return;
  }
  if (!paymentOptions.value.length) {
    uni.showToast({ title: '当前商品暂无可用支付方式', icon: 'none' });
    return;
  }
  const ids = selectedItems.value.map((item) => item.id).join(',');
  const params = [
    `cart_item_ids=${encodeURIComponent(ids)}`,
    `pay_channel=${encodeURIComponent(payChannel.value)}`,
    `purchase_mode=${encodeURIComponent(purchaseMode.value)}`,
    `points_amount=${encodeURIComponent(normalizedPoints.value)}`
  ].join('&');
  uni.navigateTo({ url: `/subpackages/order/confirm?${params}` });
}

onShow(loadData);
</script>

<style scoped>
@import '@/styles/elegant.css';

.cart-page {
  min-height: 100vh;
  background: var(--bg);
  padding-bottom: 180rpx;
}

/* Header */
.page-header {
  padding: 24rpx 32rpx;
  padding-top: calc(24rpx + env(safe-area-inset-top));
  background: var(--card);
  border-bottom: 1rpx solid var(--border);
}

.header-content {
  display: flex;
  align-items: center;
  gap: 16rpx;
}

.logo-mark {
  width: 56rpx;
  height: 56rpx;
  border-radius: var(--radius-md);
  background: linear-gradient(135deg, var(--primary), var(--primary-dark));
  display: flex;
  align-items: center;
  justify-content: center;
}

.back-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 56rpx;
  height: 56rpx;
  color: var(--text);
  transition: opacity var(--duration-fast);
}

.back-btn:active {
  opacity: 0.6;
}

.page-title {
  font-size: var(--text-xl);
  font-weight: var(--font-bold);
  color: var(--text);
  flex: 1;
}

.header-badge {
  display: flex;
  align-items: center;
  gap: 6rpx;
  padding: 8rpx 16rpx;
  background: linear-gradient(135deg, var(--primary), var(--primary-dark));
  color: white;
  font-size: 20rpx;
  font-weight: var(--font-semibold);
  border-radius: var(--radius-full);
}

/* Loading */
.loading-state {
  padding: 24rpx;
  display: flex;
  flex-direction: column;
  gap: 24rpx;
}

.skeleton-item {
  display: flex;
  gap: 20rpx;
  padding: 24rpx;
  background: var(--card);
  border-radius: var(--radius-xl);
}

.skeleton {
  background: linear-gradient(90deg, var(--border-light) 25%, var(--bg) 50%, var(--border-light) 75%);
  background-size: 200% 100%;
  animation: skeleton-shimmer 1.5s infinite;
  border-radius: var(--radius-md);
}

.skeleton-checkbox {
  width: 40rpx;
  height: 40rpx;
  flex-shrink: 0;
  margin-top: 60rpx;
}

.skeleton-image {
  width: 160rpx;
  height: 160rpx;
  flex-shrink: 0;
}

.skeleton-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}

.skeleton-title {
  height: 40rpx;
  width: 80%;
}

.skeleton-price {
  height: 36rpx;
  width: 40%;
}

@keyframes skeleton-shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* Error */
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 120rpx 32rpx;
}

.error-icon {
  font-size: 80rpx;
  color: var(--error);
  margin-bottom: 24rpx;
}

.error-text {
  font-size: 28rpx;
  color: var(--text-muted);
  margin-bottom: 32rpx;
}

.retry-btn {
  padding: 16rpx 40rpx;
  background: linear-gradient(135deg, var(--primary), var(--primary-dark));
  color: white;
  font-size: 26rpx;
  font-weight: 600;
  border-radius: 40rpx;
}

/* Empty */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 120rpx 32rpx;
}

.empty-icon {
  font-size: 120rpx;
  color: var(--border);
  margin-bottom: 32rpx;
}

.empty-title {
  font-size: 32rpx;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 8rpx;
}

.empty-desc {
  font-size: 26rpx;
  color: var(--text-muted);
  margin-bottom: 48rpx;
}

.empty-btn {
  padding: 16rpx 48rpx;
  background: linear-gradient(135deg, var(--primary), var(--primary-dark));
  color: white;
  font-size: 28rpx;
  font-weight: 600;
  border-radius: 40rpx;
}

/* Cart List */
.cart-list {
  padding: 24rpx;
  display: flex;
  flex-direction: column;
  gap: 20rpx;
}

.cart-item {
  display: flex;
  gap: 20rpx;
  padding: 24rpx;
  background: var(--card);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-sm);
}

.select-box {
  width: 44rpx;
  height: 44rpx;
  border-radius: 50%;
  border: 2rpx solid var(--border);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-top: 60rpx;
  color: transparent;
  font-size: 20rpx;
  font-weight: 700;
}

.select-box.active {
  background: linear-gradient(135deg, var(--primary), var(--primary-dark));
  border-color: transparent;
  color: white;
}

.goods-image {
  width: 160rpx;
  height: 160rpx;
  border-radius: var(--radius-lg);
  overflow: hidden;
  flex-shrink: 0;
}

.image {
  width: 100%;
  height: 100%;
}

.image-placeholder {
  width: 100%;
  height: 100%;
  background: linear-gradient(135deg, var(--primary-bg), var(--primary));
}

.goods-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.goods-title {
  font-size: 28rpx;
  font-weight: 600;
  color: var(--text);
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin-bottom: 8rpx;
}

.goods-desc {
  font-size: 22rpx;
  color: var(--text-muted);
  margin-bottom: 6rpx;
}

.goods-zone {
  font-size: 20rpx;
  color: var(--text-muted);
  margin-bottom: auto;
}

.goods-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 12rpx;
}

.goods-price {
  font-size: 32rpx;
  font-weight: 700;
  color: var(--secondary);
}

.stepper {
  display: flex;
  align-items: center;
  gap: 8rpx;
}

.step-btn {
  width: 48rpx;
  height: 48rpx;
  border-radius: var(--radius-md);
  background: var(--bg);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24rpx;
  color: var(--text);
}

.step-value {
  min-width: 56rpx;
  text-align: center;
  font-size: 26rpx;
  font-weight: 700;
  color: var(--text);
}

.goods-sub {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 12rpx;
}

.subtotal {
  font-size: 22rpx;
  color: var(--text-muted);
}

.remove-btn {
  font-size: 22rpx;
  color: var(--text-muted);
  padding: 8rpx 16rpx;
  background: var(--bg);
  border-radius: var(--radius-md);
  border: 1rpx solid var(--border);
}

/* Payment Card */
.pay-card {
  margin: 0 24rpx;
  padding: 32rpx;
  background: var(--card);
  border-radius: var(--radius-xl);
}

.section-title {
  font-size: 30rpx;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 20rpx;
}

.pay-options {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16rpx;
  margin-bottom: 24rpx;
}

.pay-option {
  padding: 20rpx;
  border-radius: var(--radius-lg);
  border: 2rpx solid var(--border-light);
  background: var(--bg);
  display: flex;
  flex-direction: column;
  gap: 8rpx;
}

.pay-option.active {
  border-color: var(--primary);
  background: var(--primary-bg);
}

.pay-option.disabled {
  opacity: 0.55;
}

.pay-title {
  font-size: 26rpx;
  font-weight: 700;
  color: var(--text);
}

.pay-desc {
  font-size: 20rpx;
  color: var(--text-muted);
  line-height: 1.4;
}

.points-box {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20rpx;
  background: var(--bg);
  border-radius: var(--radius-lg);
  margin-bottom: 24rpx;
  gap: 20rpx;
}

.points-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6rpx;
}

.points-title {
  font-size: 28rpx;
  font-weight: 700;
  color: var(--text);
}

.points-desc {
  font-size: 20rpx;
  color: var(--text-muted);
}

.points-input {
  width: 160rpx;
  height: 64rpx;
  border-radius: var(--radius-md);
  padding: 0 20rpx;
  text-align: right;
  background: var(--card);
  color: var(--text);
  font-size: 28rpx;
}

.summary-list {
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}

.summary-line {
  display: flex;
  justify-content: space-between;
  font-size: 24rpx;
  color: var(--text-muted);
}

.summary-line.strong {
  font-size: 32rpx;
  font-weight: 700;
  color: var(--secondary);
  margin-top: 8rpx;
  padding-top: 16rpx;
  border-top: 1rpx solid var(--border-light);
}

/* Submit Bar */
.submit-bar {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  padding: 24rpx 32rpx;
  padding-bottom: calc(24rpx + env(safe-area-inset-bottom));
  background: var(--card);
  border-top: 1rpx solid var(--border-light);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24rpx;
  z-index: 100;
}

.submit-info {
  display: flex;
  flex-direction: column;
  gap: 4rpx;
}

.submit-label {
  font-size: 22rpx;
  color: var(--text-muted);
}

.submit-price {
  font-size: 40rpx;
  font-weight: 800;
  color: var(--secondary);
}

.submit-btn {
  padding: 24rpx 56rpx;
  background: linear-gradient(135deg, var(--primary), var(--primary-dark));
  color: white;
  font-size: 30rpx;
  font-weight: 700;
  border-radius: 44rpx;
}

.submit-btn.disabled {
  opacity: 0.6;
}
</style>
