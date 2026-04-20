<template>
  <view class="container cart-page">
    <StateView v-if="loading" title="购物车加载中..." />
    <StateView v-else-if="failed" title="购物车加载失败" :show-retry="true" @retry="loadData" />
    <StateView
      v-else-if="!items.length"
      title="购物车还是空的"
      description="去商品详情页加入购物车后，就可以在这里统一结算。"
    />

    <template v-else>
      <view class="card-list">
        <view v-for="item in items" :key="item.id" class="card cart-card">
          <view class="select-box interactive" :class="{ active: item.selected }" @click="toggleSelected(item)">
            {{ item.selected ? '选' : '' }}
          </view>
          <image v-if="item.image || item.product?.image" class="goods-cover" :src="item.image || item.product?.image" mode="aspectFill" />
          <view v-else class="goods-cover goods-fallback" />

          <view class="goods-main">
            <view class="goods-title">{{ item.title || item.product?.title }}</view>
            <view class="goods-desc">{{ item.product?.desc || '购物车商品' }}</view>
            <view class="goods-meta">{{ zoneText(item.zone_type || item.product?.zone_type) }}</view>
            <view class="row-between mt-16">
              <view class="price">¥{{ money(item.price) }}</view>
              <view class="stepper">
                <view class="step-btn interactive" @click="changeQuantity(item, -1)">-</view>
                <view class="step-value">{{ item.quantity }}</view>
                <view class="step-btn interactive" @click="changeQuantity(item, 1)">+</view>
              </view>
            </view>
            <view class="row-between mt-12">
              <view class="subtotal">小计 ¥{{ money(item.subtotal_amount) }}</view>
              <button class="btn btn-ghost mini-btn" @click="removeItem(item.id)">移除</button>
            </view>
          </view>
        </view>
      </view>

      <view class="card mt-20 pay-card">
        <view class="section-title">结算方式</view>
        <view class="pay-options">
          <view
            v-for="item in paymentOptions"
            :key="item.value"
            class="pay-option interactive"
            :class="{ active: payChannel === item.value }"
            @click="payChannel = item.value"
          >
            <view class="pay-title">{{ item.label }}</view>
            <view class="pay-desc">{{ item.desc }}</view>
          </view>
        </view>

        <view class="points-box">
          <view>
            <view class="setting-title">积分抵扣</view>
            <view class="setting-desc">积分可与余额、消费金、微信、支付宝组合使用</view>
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

      <view class="safe-space" />
      <view class="submit-bar">
        <view>
          <view class="submit-label">已选 {{ selectedCount }} 件</view>
          <view class="submit-price">¥{{ cashAmount }}</view>
        </view>
        <button class="btn btn-primary submit-btn" @click="checkout">{{ checkingOut ? '支付中...' : '支付结算' }}</button>
      </view>
    </template>
  </view>
</template>

<script setup>
import { computed, ref, watch } from 'vue';
import { onShow } from '@dcloudio/uni-app';
import StateView from '@/components/StateView.vue';
import { commerceApi } from '@/api/modules';
import { pickListPayload } from '@/utils/adapters';

const PAYMENT_LABEL_MAP = {
  BALANCE: '余额',
  VOUCHER: '消费金',
  WECHAT: '微信支付',
  ALIPAY: '支付宝'
};

const PAYMENT_DESC_MAP = {
  BALANCE: '使用余额支付剩余金额',
  VOUCHER: '使用消费金支付剩余金额',
  WECHAT: '已预留微信支付接口',
  ALIPAY: '已预留支付宝接口'
};

const loading = ref(false);
const failed = ref(false);
const checkingOut = ref(false);
const items = ref([]);
const pointsAmount = ref('');
const payChannel = ref('BALANCE');

const selectedItems = computed(() => items.value.filter((item) => item.selected));
const selectedProducts = computed(() => selectedItems.value.map((item) => item.product || {}).filter(Boolean));
const selectedZones = computed(() => Array.from(new Set(selectedProducts.value.map((item) => item.zone_type).filter(Boolean))));
const supportsPoints = computed(() => {
  if (!selectedProducts.value.length) return true;
  return selectedProducts.value.every((item) => item.points_purchase_enabled !== false);
});
const paymentOptions = computed(() => {
  if (!selectedProducts.value.length) return [];
  if (selectedZones.value.length > 1) return [];
  const channelSets = selectedProducts.value.map((item) => new Set(item.supported_pay_channels || []));
  const channels = [...channelSets[0]].filter((channel) => channelSets.every((set) => set.has(channel)));
  return channels.map((value) => ({
    value,
    label: `${PAYMENT_LABEL_MAP[value] || value}${supportsPoints.value ? ' + 积分' : ''}`,
    desc: PAYMENT_DESC_MAP[value] || '按当前渠道支付'
  }));
});
const selectedCount = computed(() => selectedItems.value.length);
const totalAmount = computed(() => selectedItems.value.reduce((sum, item) => sum + Number(item.subtotal_amount || 0), 0).toFixed(2));
const normalizedPoints = computed(() => {
  if (!supportsPoints.value) return '0.00';
  const amount = Math.max(0, Number(pointsAmount.value || 0));
  return Math.min(amount, Number(totalAmount.value)).toFixed(2);
});
const cashAmount = computed(() => Math.max(0, Number(totalAmount.value) - Number(normalizedPoints.value)).toFixed(2));
const cashLabel = computed(() => ({
  BALANCE: '余额支付',
  VOUCHER: '消费金支付',
  WECHAT: '微信支付',
  ALIPAY: '支付宝支付'
}[payChannel.value] || '现金支付'));

watch(
  paymentOptions,
  (options) => {
    if (!options.length) return;
    if (!options.some((item) => item.value === payChannel.value)) {
      payChannel.value = options[0].value;
    }
  },
  { immediate: true }
);

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
  const updated = await commerceApi.updateCartItem(item.id, { selected: !item.selected });
  items.value = items.value.map((row) => (row.id === item.id ? updated : row));
}

async function changeQuantity(item, delta) {
  const quantity = Math.max(1, Number(item.quantity || 1) + delta);
  const updated = await commerceApi.updateCartItem(item.id, { quantity });
  items.value = items.value.map((row) => (row.id === item.id ? updated : row));
}

async function removeItem(itemId) {
  await commerceApi.removeCartItem(itemId);
  items.value = items.value.filter((item) => item.id !== itemId);
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
  checkingOut.value = true;
  try {
    const res = await commerceApi.checkoutCart({
      item_ids: selectedItems.value.map((item) => item.id),
      points_amount: Number(normalizedPoints.value),
      pay_channel: payChannel.value,
      auto_complete: true
    });
    await loadData();
    uni.showToast({ title: '支付完成', icon: 'success' });
    setTimeout(() => {
      uni.navigateTo({ url: `/subpackages/order/detail?id=${res.order_id}` });
    }, 500);
  } finally {
    checkingOut.value = false;
  }
}

onShow(loadData);
</script>

<style scoped>
@import '@/styles/common.css';

.cart-page { padding-bottom: 190rpx; }
.card-list { display: flex; flex-direction: column; gap: 16rpx; }
.cart-card { display: flex; gap: 16rpx; align-items: flex-start; }
.select-box {
  width: 40rpx;
  height: 40rpx;
  margin-top: 68rpx;
  border-radius: 50%;
  flex-shrink: 0;
  border: 2rpx solid rgba(201, 106, 20, 0.28);
  display: flex;
  align-items: center;
  justify-content: center;
  color: transparent;
  font-size: 18rpx;
  font-weight: 700;
}
.select-box.active {
  background: linear-gradient(120deg, #ff6f00, #ff9f2f);
  border-color: transparent;
  color: #fff;
}
.goods-cover {
  width: 170rpx;
  height: 170rpx;
  border-radius: 20rpx;
  flex-shrink: 0;
  background: #f3eadf;
}
.goods-fallback { background: linear-gradient(135deg, #f1dec9, #e7c8a4 46%, #d8af83); }
.goods-main { flex: 1; min-width: 0; }
.goods-title { font-size: 28rpx; font-weight: 700; color: #4f321a; line-height: 1.35; }
.goods-desc { margin-top: 10rpx; font-size: 22rpx; color: #8b7158; line-height: 1.45; }
.goods-meta { margin-top: 10rpx; font-size: 20rpx; color: #a08469; }
.price { font-size: 32rpx; color: #c96a14; font-weight: 800; }
.subtotal { font-size: 22rpx; color: #8b7158; }
.stepper { display: flex; align-items: center; gap: 10rpx; }
.step-btn, .step-value {
  width: 48rpx;
  height: 48rpx;
  border-radius: 14rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fbf3ea;
  color: #9f6736;
  font-size: 24rpx;
}
.step-value { width: 60rpx; color: #4f321a; font-weight: 700; }
.mini-btn { width: 120rpx; height: 54rpx; line-height: 54rpx; padding: 0; font-size: 22rpx; }
.pay-options { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14rpx; }
.pay-option {
  padding: 18rpx;
  border-radius: 20rpx;
  border: 2rpx solid rgba(198, 161, 124, 0.14);
  background: #fffdf9;
}
.pay-option.active {
  border-color: #ff8b24;
  background: linear-gradient(180deg, #fff4e8, #ffe8d3);
}
.pay-title { font-size: 26rpx; font-weight: 800; color: #4f321a; }
.pay-desc { margin-top: 8rpx; font-size: 20rpx; line-height: 1.4; color: #8b7158; }
.points-box {
  margin-top: 18rpx;
  padding: 18rpx;
  border-radius: 20rpx;
  background: #fbf5ef;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20rpx;
}
.setting-title { font-size: 28rpx; font-weight: 800; color: #4f321a; }
.setting-desc { margin-top: 6rpx; font-size: 22rpx; color: #8b7158; }
.points-input {
  width: 180rpx;
  height: 64rpx;
  border-radius: 16rpx;
  padding: 0 18rpx;
  text-align: right;
  background: #fff;
  color: #4f321a;
  font-size: 28rpx;
  box-sizing: border-box;
}
.summary-list { margin-top: 18rpx; display: flex; flex-direction: column; gap: 12rpx; }
.summary-line { display: flex; justify-content: space-between; color: #7f6650; font-size: 24rpx; }
.summary-line.strong { color: #c96a14; font-weight: 800; font-size: 30rpx; }
.safe-space { height: 24rpx; }
.submit-bar {
  position: fixed;
  left: 20rpx;
  right: 20rpx;
  bottom: calc(env(safe-area-inset-bottom) + 12rpx);
  z-index: 20;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16rpx;
  padding: 18rpx 22rpx;
  border-radius: 28rpx;
  background: rgba(255, 251, 246, 0.94);
  border: 1rpx solid rgba(198, 161, 124, 0.18);
  box-shadow: 0 18rpx 40rpx rgba(120, 76, 40, 0.12);
}
.submit-label { font-size: 22rpx; color: #8b7158; }
.submit-price { margin-top: 6rpx; font-size: 36rpx; color: #c96a14; font-weight: 800; }
.submit-btn { width: 240rpx; }
.interactive { transition: transform 180ms ease, opacity 180ms ease; }
.interactive:active { transform: scale(0.98); opacity: 0.92; }
</style>
