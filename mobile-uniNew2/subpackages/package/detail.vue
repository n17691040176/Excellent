<template>
  <view class="container detail-page">
    <view v-if="loading" class="card state-card">商品加载中...</view>
    <view v-else-if="failed" class="card state-card">
      <view>商品加载失败</view>
      <button class="btn btn-ghost retry-btn mt-16" @click="loadDetail">重新加载</button>
    </view>

    <template v-else>
      <view class="media-card">
        <swiper
          v-if="detail.gallery.length"
          class="media-swiper"
          circular
          :indicator-dots="detail.gallery.length > 1"
          indicator-color="rgba(255,255,255,0.35)"
          indicator-active-color="#ffffff"
        >
          <swiper-item v-for="(item, index) in detail.gallery" :key="`${item}-${index}`">
            <image class="hero-image" :src="item" mode="aspectFill" />
          </swiper-item>
        </swiper>
        <view v-else class="media-fallback" />
        <view class="media-mask">
          <view class="badge badge-orange">{{ zoneLabel }}</view>
          <view class="media-count" v-if="detail.gallery.length > 1">{{ detail.gallery.length }} 图</view>
        </view>
      </view>

      <view class="card intro-card">
        <view class="title">{{ detail.title }}</view>
        <view class="desc">{{ detail.desc }}</view>
        <view class="tag-row">
          <text v-for="item in detail.highlights" :key="item" class="highlight-chip">{{ item }}</text>
        </view>
        <view class="price-row">
          <view class="price-main-wrap">
            <text class="price-symbol">¥</text>
            <text class="price-main">{{ detail.price }}</text>
            <text v-if="detail.originPrice" class="price-origin">¥{{ detail.originPrice }}</text>
          </view>
          <view class="mini-tip">{{ detail.stockText }}</view>
        </view>
      </view>

      <view class="card mt-20 pay-card">
        <view class="section-title">支付设置</view>
        <view class="row-between quantity-row">
          <view>
            <view class="setting-title">购买数量</view>
            <view class="setting-desc">小计 ¥{{ subtotal }}</view>
          </view>
          <view class="stepper">
            <view class="step-btn interactive" @click="changeQuantity(-1)">-</view>
            <view class="step-value">{{ quantity }}</view>
            <view class="step-btn interactive" @click="changeQuantity(1)">+</view>
          </view>
        </view>

        <view class="pay-options">
          <view
            v-for="item in paymentOptions"
            :key="item.key"
            class="pay-option interactive"
            :class="{ active: selectedPayKey === item.key }"
            @click="selectPaymentOption(item)"
          >
            <view class="pay-title">{{ item.label }}</view>
            <view class="pay-desc">{{ item.desc }}</view>
          </view>
        </view>

        <view class="points-box">
          <view>
            <view class="setting-title">积分抵扣</view>
            <view class="setting-desc">可填 0，剩余部分走当前支付方式</view>
          </view>
          <input class="points-input" v-model="pointsAmount" type="digit" placeholder="0" />
        </view>

        <view class="pay-summary">
          <view class="summary-line">
            <text>商品金额</text>
            <text>¥{{ subtotal }}</text>
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

      <view class="card mt-20">
        <view class="section-title">商品亮点</view>
        <view class="feature-grid">
          <view v-for="item in detail.features" :key="item" class="feature-item">{{ item }}</view>
        </view>
      </view>

      <view class="card mt-20">
        <view class="section-title">图文说明</view>
        <view v-for="item in detail.items" :key="item" class="content-line">{{ item }}</view>
      </view>

      <view class="safe-space" />
    </template>

    <view v-if="!loading && !failed" class="action-bar">
      <view class="action-tools">
        <view class="tool-action interactive" @click="toggleFavorite">
          <view class="tool-icon">{{ isFavorite ? '藏' : '收' }}</view>
          <view class="tool-text">{{ isFavorite ? '已收藏' : '收藏' }}</view>
        </view>
        <view class="tool-action interactive" @click="goCart">
          <view class="tool-icon">车</view>
          <view class="tool-text">购物车</view>
        </view>
      </view>
      <view class="action-buttons">
        <button class="btn btn-ghost action-btn secondary-btn" @click="addToCart">加入购物车</button>
        <button class="btn btn-primary action-btn" @click="createAndPay">{{ ordering ? '处理中...' : '立即支付' }}</button>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed, ref, watch } from 'vue';
import { onLoad } from '@dcloudio/uni-app';
import { commerceApi, orderApi, packageApi } from '@/api/modules';
import { getApiBaseUrl } from '@/config/index';
import { requestPayment as requestPlatformPayment } from '@/utils/payment';
import { trackEvent, trackPageView } from '@/utils/track';

const LEGACY_FILE_BASE_URL = 'https://file.hoh516.com/huohonghuo';
const ORDER_TYPE_MAP = {
  HOT_SALE: 'HOT_SALE_ORDER',
  SELF_OPERATED: 'SELF_OPERATED_ORDER',
  REPURCHASE: 'REPURCHASE_ORDER',
  LOCAL_LIFE: 'LOCAL_LIFE_ORDER'
};

const PAYMENT_LABEL_MAP = {
  POINTS: '纯积分',
  BALANCE: '余额',
  VOUCHER: '消费金',
  WECHAT: '微信支付',
  ALIPAY: '支付宝'
};

const PAYMENT_DESC_MAP = {
  POINTS: '全部使用积分完成支付',
  BALANCE: '使用余额支付剩余金额',
  VOUCHER: '使用消费金支付剩余金额',
  WECHAT: '已预留微信支付接口',
  ALIPAY: '已预留支付宝接口'
};

const loading = ref(false);
const failed = ref(false);
const id = ref('');
const isFavorite = ref(false);
const ordering = ref(false);
const quantity = ref(1);
const pointsAmount = ref('');
const payChannel = ref('BALANCE');
const purchaseMode = ref('CASH_ONLY');
const selectedPayKey = ref('');
const detail = ref({
  title: '',
  desc: '',
  tag: '精选商品',
  category: '精选商品',
  image: '',
  gallery: [],
  price: '0.00',
  originPrice: '',
  stock: 0,
  stockText: '库存充足',
  zoneType: '',
  highlights: [],
  features: [],
  items: [],
  paymentOptions: [],
  supportsPoints: true,
  defaultPayChannel: 'BALANCE'
});

function optionKey(item) {
  return `${item.value || ''}|${item.purchase_mode || (item.supports_points ? 'POINTS_CASH' : 'CASH_ONLY')}`;
}

function paymentLabel(item, mode) {
  if (item.label) return item.label;
  if (item.value === 'BALANCE' && mode === 'POINTS_CASH') return '余额+积分支付';
  if (item.value === 'BALANCE' && mode === 'CASH_ONLY') return '余额纯支付';
  return `${PAYMENT_LABEL_MAP[item.value] || item.value}${item.supports_points ? ' + 积分' : ''}`;
}

function paymentDesc(item) {
  if (item.desc) return item.desc;
  return PAYMENT_DESC_MAP[item.value] || '按当前渠道支付';
}

const paymentOptions = computed(() => (
  Array.isArray(detail.value.paymentOptions) ? detail.value.paymentOptions : []
).map((item) => {
  const mode = item.purchase_mode || (item.supports_points ? 'POINTS_CASH' : 'CASH_ONLY');
  return {
    key: optionKey({ ...item, purchase_mode: mode }),
    value: item.value,
    purchase_mode: mode,
    supports_points: Boolean(item.supports_points),
    label: paymentLabel(item, mode),
    desc: paymentDesc(item)
  };
}));

const selectedPaymentOption = computed(() => paymentOptions.value.find((item) => item.key === selectedPayKey.value) || paymentOptions.value[0] || null);

const zoneLabel = computed(() => ({
  HOT_SALE: '爆款区',
  SELF_OPERATED: '自营商城',
  REPURCHASE: '复购区',
  LOCAL_LIFE: '本地生活'
}[detail.value.zoneType] || '商品专区'));

const subtotal = computed(() => {
  return (Number(detail.value.price || 0) * Number(quantity.value || 1)).toFixed(2);
});

const normalizedPoints = computed(() => {
  const option = selectedPaymentOption.value;
  if (!option || option.purchase_mode === 'CASH_ONLY') return '0.00';
  if (option.purchase_mode === 'POINTS_ONLY') return Number(subtotal.value).toFixed(2);
  const amount = Math.max(0, Number(pointsAmount.value || 0));
  const maxPoints = Math.max(0, Number(subtotal.value) - 0.01);
  return Math.min(amount, maxPoints).toFixed(2);
});

const cashAmount = computed(() => {
  return Math.max(0, Number(subtotal.value) - Number(normalizedPoints.value)).toFixed(2);
});

const cashLabel = computed(() => ({
  BALANCE: '余额支付',
  VOUCHER: '消费金支付',
  WECHAT: '微信支付',
  ALIPAY: '支付宝支付'
}[payChannel.value] || '现金支付'));

const resolveImage = (value) => {
  if (!value) return '';
  if (/^https?:\/\//i.test(value)) return value;
  if (value.startsWith('/profile/')) return `${LEGACY_FILE_BASE_URL}${value}`;
  if (value.startsWith('/')) return `${getApiBaseUrl()}${value}`;
  return value;
};

const resolveGallery = (res) => {
  const gallery = Array.isArray(res?.gallery) ? res.gallery : [];
  const rows = gallery.map((item) => resolveImage(item)).filter(Boolean);
  const cover = resolveImage(res?.image || res?.main_image || res?.cover);
  if (cover && !rows.includes(cover)) {
    rows.unshift(cover);
  }
  return rows;
};

const normalizePrice = (value) => {
  const amount = Number(value || 0);
  return amount > 0 ? amount.toFixed(2) : '0.00';
};

const normalize = (res) => {
  const price = Number(res?.price ?? res?.sale_price ?? 0);
  const marketPrice = Number(res?.market_price ?? 0);
  const soldCount = Number(res?.sold_count ?? res?.sales_volume ?? 0);
  const stock = Number(res?.stock ?? 0);
  const gallery = resolveGallery(res);
  const features = Array.isArray(res?.features) && res.features.length
    ? res.features
    : ['官方精选', '品质保障', '支持支付'];
  const items = Array.isArray(res?.items) && res.items.length
    ? res.items
    : (Array.isArray(res?.content) && res.content.length ? res.content : ['暂无更多说明']);

  return {
    title: res?.name || res?.title || '未命名商品',
    desc: res?.description || res?.desc || '暂无描述',
    tag: res?.tag || '精选商品',
    category: res?.category_name || res?.tag || '精选商品',
    image: gallery[0] || '',
    gallery,
    price: normalizePrice(price),
    originPrice: marketPrice > price ? normalizePrice(marketPrice) : '',
    stock,
    stockText: stock > 0 ? `库存 ${stock}` : '库存需确认',
    zoneType: res?.zone_type || '',
    highlights: [res?.tag, res?.category_name, soldCount > 0 ? `销量 ${soldCount}` : '新品上架'].filter(Boolean),
    features: features.slice(0, 6),
    items: items.slice(0, 6),
    paymentOptions: Array.isArray(res?.payment_options) ? res.payment_options : [],
    supportsPoints: Boolean(res?.points_purchase_enabled),
    defaultPayChannel: res?.default_pay_channel || 'BALANCE'
  };
};

const loadProductStatus = async () => {
  if (!id.value) return;
  try {
    const res = await commerceApi.productStatus(id.value);
    isFavorite.value = Boolean(res?.is_favorite);
  } catch (error) {
    // Request layer handles toast when needed.
  }
};

watch(
  () => detail.value.defaultPayChannel,
  (value) => {
    if (!value || selectedPayKey.value) return;
    const option = paymentOptions.value.find((item) => item.value === value) || paymentOptions.value[0];
    if (option) selectPaymentOption(option);
  },
  { immediate: true }
);

watch(
  paymentOptions,
  (options) => {
    if (!options.length) return;
    if (!options.some((item) => item.key === selectedPayKey.value)) {
      selectPaymentOption(options[0]);
    }
  },
  { immediate: true }
);

const loadDetail = async () => {
  if (!id.value) return;
  loading.value = true;
  failed.value = false;
  try {
    const res = await packageApi.detail(id.value);
    detail.value = normalize(res || {});
    await Promise.allSettled([
      loadProductStatus(),
      commerceApi.recordFootprint(id.value)
    ]);
  } catch (error) {
    failed.value = true;
  } finally {
    loading.value = false;
  }
};

onLoad((query) => {
  id.value = query?.id || '';
  trackPageView('package_detail_view', { id: id.value });
  loadDetail();
});

function changeQuantity(delta) {
  const next = Math.max(1, Number(quantity.value || 1) + delta);
  if (detail.value.stock > 0 && next > detail.value.stock) {
    uni.showToast({ title: '库存不足', icon: 'none' });
    return;
  }
  quantity.value = next;
}

function selectPaymentOption(option) {
  selectedPayKey.value = option.key;
  payChannel.value = option.value;
  purchaseMode.value = option.purchase_mode;
  if (option.purchase_mode !== 'POINTS_CASH') {
    pointsAmount.value = '';
  }
}

function buildDeductions() {
  const rows = [];
  const points = Number(normalizedPoints.value);
  const cash = Number(cashAmount.value);
  if (points > 0) {
    rows.push({ asset_type: 'POINTS', amount: points });
  }
  if (payChannel.value === 'BALANCE' && cash > 0) {
    rows.push({ asset_type: 'BALANCE', amount: cash });
  }
  if (payChannel.value === 'VOUCHER' && cash > 0) {
    rows.push({ asset_type: 'VOUCHER', amount: cash });
  }
  return rows;
}

const toggleFavorite = async () => {
  if (isFavorite.value) {
    await commerceApi.unfavorite(id.value);
    isFavorite.value = false;
    uni.showToast({ title: '已取消收藏', icon: 'none' });
    return;
  }
  await commerceApi.favorite(id.value);
  isFavorite.value = true;
  uni.showToast({ title: '收藏成功', icon: 'none' });
};

const addToCart = async () => {
  await commerceApi.addCartItem({ product_id: Number(id.value), quantity: Number(quantity.value || 1) });
  uni.showToast({ title: '已加入购物车', icon: 'none' });
};

const goCart = () => {
  uni.navigateTo({ url: '/subpackages/profile/cart' });
};

const createAndPay = async () => {
  const orderType = ORDER_TYPE_MAP[detail.value.zoneType];
  if (!orderType) {
    uni.showToast({ title: '当前商品暂不支持下单', icon: 'none' });
    return;
  }
  if (!paymentOptions.value.length) {
    uni.showToast({ title: '当前商品暂不支持支付', icon: 'none' });
    return;
  }
  ordering.value = true;
  try {
    trackEvent('package_detail_pay', { id: id.value, zone_type: detail.value.zoneType, pay_channel: payChannel.value, purchase_mode: purchaseMode.value });
    const order = await orderApi.create({
      order_type: orderType,
      zone_type: detail.value.zoneType,
      pay_channel: payChannel.value,
      items: [{ product_id: Number(id.value), quantity: Number(quantity.value || 1) }],
      asset_deductions: buildDeductions()
    });

    let toastTitle = '支付完成';
    let toastIcon = 'success';
    if (['WECHAT', 'ALIPAY'].includes(payChannel.value)) {
      const payResult = await orderApi.pay(order.id || order.order_id, {
        pay_channel: payChannel.value,
        auto_complete: true
      });
      const payment = payResult?.payment;
      if (payment?.status !== 'PAID') {
        try {
          const platformResult = await requestPlatformPayment(payment);
          toastTitle = platformResult?.mocked ? '支付单已创建' : '支付已提交';
          toastIcon = platformResult?.mocked ? 'none' : 'success';
        } catch (error) {
          const errMsg = String(error?.errMsg || error?.message || '');
          toastTitle = errMsg.includes('cancel') ? '已取消支付' : '支付失败';
          toastIcon = 'none';
        }
      }
    }

    uni.showToast({ title: toastTitle, icon: toastIcon });
    setTimeout(() => {
      uni.navigateTo({ url: `/subpackages/order/detail?id=${order.id || order.order_id}` });
    }, 500);
  } finally {
    ordering.value = false;
  }
};
</script>

<style scoped>
@import '@/styles/common.css';

.detail-page { padding-bottom: 190rpx; }
.state-card { text-align: center; }
.retry-btn { width: 220rpx; }
.media-card {
  position: relative;
  overflow: hidden;
  border-radius: 34rpx;
  background: linear-gradient(160deg, #fff2e2, #ffd2a9 48%, #ff9f62);
  box-shadow: 0 20rpx 40rpx rgba(152, 93, 42, 0.14);
}
.media-swiper, .hero-image, .media-fallback { width: 100%; height: 560rpx; }
.hero-image, .media-fallback { display: block; }
.media-fallback { background: linear-gradient(160deg, #f7e0c7, #f0c892 48%, #e09d67); }
.media-mask {
  position: absolute;
  left: 18rpx;
  right: 18rpx;
  top: 18rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.media-count {
  padding: 8rpx 14rpx;
  border-radius: 999rpx;
  background: rgba(40, 26, 15, 0.28);
  color: #fffdf8;
  font-size: 22rpx;
}
.intro-card { margin-top: 20rpx; }
.title { font-size: 40rpx; line-height: 1.3; font-weight: 900; color: #4a2b13; }
.desc { margin-top: 12rpx; font-size: 24rpx; line-height: 1.55; color: #7f6650; }
.tag-row { display: flex; flex-wrap: wrap; gap: 10rpx; margin-top: 18rpx; }
.highlight-chip {
  padding: 8rpx 16rpx;
  border-radius: 999rpx;
  background: rgba(255, 122, 0, 0.1);
  color: #ff6a00;
  font-size: 22rpx;
  font-weight: 700;
}
.price-row {
  margin-top: 22rpx;
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16rpx;
}
.price-main-wrap { display: flex; align-items: baseline; gap: 6rpx; }
.price-symbol { font-size: 26rpx; font-weight: 800; color: var(--brand-accent); }
.price-main { font-size: 52rpx; line-height: 1; font-weight: 900; color: var(--brand-accent); }
.price-origin { font-size: 22rpx; color: #b9a393; text-decoration: line-through; }
.mini-tip { font-size: 22rpx; color: #9a7e67; }
.pay-card { overflow: hidden; }
.quantity-row {
  padding: 20rpx;
  border-radius: 24rpx;
  background: #fff8ef;
  border: 1rpx solid rgba(198, 161, 124, 0.14);
}
.setting-title { font-size: 28rpx; font-weight: 800; color: #4f321a; }
.setting-desc { margin-top: 6rpx; font-size: 22rpx; color: #8b7158; }
.stepper { display: flex; align-items: center; gap: 10rpx; }
.step-btn, .step-value {
  width: 52rpx;
  height: 52rpx;
  border-radius: 16rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fbf3ea;
  color: #9f6736;
  font-size: 26rpx;
}
.step-value { width: 68rpx; color: #4f321a; font-weight: 800; }
.pay-options { margin-top: 18rpx; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14rpx; }
.pay-option {
  padding: 18rpx;
  border-radius: 22rpx;
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
  border-radius: 22rpx;
  background: #fbf5ef;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20rpx;
}
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
.pay-summary { margin-top: 18rpx; display: flex; flex-direction: column; gap: 12rpx; }
.summary-line { display: flex; justify-content: space-between; color: #7f6650; font-size: 24rpx; }
.summary-line.strong { color: #ff6a00; font-weight: 900; font-size: 30rpx; }
.feature-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12rpx; }
.feature-item {
  padding: 18rpx 16rpx;
  border-radius: 18rpx;
  background: linear-gradient(180deg, #fff7ef 0%, #fff1e4 100%);
  color: #8f5c2a;
  font-size: 24rpx;
  line-height: 1.45;
}
.content-line {
  margin-top: 12rpx;
  padding: 18rpx;
  border-radius: 18rpx;
  background: #fdf8f2;
  color: #65452a;
  font-size: 24rpx;
  line-height: 1.55;
}
.safe-space { height: 24rpx; }
.action-bar {
  position: fixed;
  left: 20rpx;
  right: 20rpx;
  bottom: calc(env(safe-area-inset-bottom) + 12rpx);
  z-index: 40;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16rpx;
  padding: 18rpx;
  border-radius: 28rpx;
  background: rgba(255, 251, 246, 0.94);
  border: 1rpx solid rgba(198, 161, 124, 0.18);
  box-shadow: 0 18rpx 40rpx rgba(120, 76, 40, 0.12);
  backdrop-filter: blur(18rpx);
}
.action-tools { display: flex; gap: 18rpx; flex-shrink: 0; }
.tool-action { display: flex; flex-direction: column; align-items: center; gap: 6rpx; }
.tool-icon {
  width: 58rpx;
  height: 58rpx;
  border-radius: 18rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fff2e6;
  color: #c96a14;
  font-size: 24rpx;
  font-weight: 800;
}
.tool-text { font-size: 20rpx; color: #8b7158; }
.action-buttons { flex: 1; display: flex; gap: 12rpx; }
.action-btn { flex: 1; min-width: 0; padding: 0; }
.secondary-btn { box-shadow: none; }
.interactive { transition: transform 180ms ease, opacity 180ms ease; }
.interactive:active { transform: scale(0.98); opacity: 0.92; }
</style>
