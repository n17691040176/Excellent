<template>
  <view class="detail-page">
    <!-- Header -->
    <view class="page-header">
      <AppBackButton @click="goBack" />
      <text class="header-title">商品详情</text>
      <view class="share-btn" @click="shareProduct">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
          <circle cx="18" cy="5" r="3" stroke="currentColor" stroke-width="2"/>
          <circle cx="6" cy="12" r="3" stroke="currentColor" stroke-width="2"/>
          <circle cx="18" cy="19" r="3" stroke="currentColor" stroke-width="2"/>
          <path d="M8.59 13.51L15.42 17.49M15.41 6.51L8.59 10.49" stroke="currentColor" stroke-width="2"/>
        </svg>
      </view>
    </view>

    <!-- Loading -->
    <view v-if="loading" class="loading-state">
      <view class="skeleton skeleton-hero" />
      <view class="skeleton-content">
        <view class="skeleton skeleton-price" />
        <view class="skeleton skeleton-title" />
        <view class="skeleton skeleton-title short" />
        <view class="skeleton-actions">
          <view class="skeleton skeleton-action" />
          <view class="skeleton skeleton-action" />
        </view>
      </view>
    </view>

    <!-- Error -->
    <view v-else-if="failed" class="state-view">
      <svg class="state-icon error" width="120" height="120" viewBox="0 0 24 24" fill="none">
        <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="1.5"/>
        <path d="M12 8V12M12 16H12.01" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
      </svg>
      <text class="state-title">加载失败</text>
      <text class="state-desc">商品信息加载失败，请稍后重试</text>
      <view class="state-action" @click="loadDetail">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
          <path d="M1 4V10H7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          <path d="M3.51 15C4.15839 16.8404 5.38734 18.4202 7.01166 19.5014C8.63598 20.5826 10.5677 21.1066 12.5157 20.9945C14.4637 20.8824 16.3226 20.1397 17.8121 18.8798C19.3016 17.6198 20.3413 15.9089 20.7741 14.0064C21.2068 12.1039 21.0107 10.1157 20.2127 8.33153C19.4148 6.54734 18.0551 5.06235 16.3288 4.10187C14.6025 3.14139 12.6009 2.75431 10.6223 3.00104C8.64365 3.24778 6.79194 4.11503 5.34 5.47" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        <text>重新加载</text>
      </view>
    </view>

    <!-- Content -->
    <template v-else>
      <!-- Gallery -->
      <view class="gallery-section">
        <swiper
          v-if="detail.gallery.length"
          class="gallery-swiper"
          circular
          :indicator-dots="false"
          @change="onGalleryChange"
        >
          <swiper-item v-for="(item, index) in detail.gallery" :key="`${item}-${index}`">
            <image class="gallery-image" :src="item" mode="aspectFill" />
          </swiper-item>
        </swiper>
        <view v-else class="gallery-placeholder">
          <svg width="80" height="80" viewBox="0 0 24 24" fill="none">
            <rect x="3" y="3" width="18" height="18" rx="2" stroke="currentColor" stroke-width="1.5" opacity="0.3"/>
            <circle cx="8.5" cy="8.5" r="1.5" fill="currentColor" opacity="0.3"/>
            <path d="M21 15L16 10.5V10C16 8.89543 15.1046 8 14 8H10C8.89543 8 8 8.89543 8 10V10.5L3 15" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" opacity="0.3"/>
          </svg>
        </view>
        <view v-if="detail.gallery.length > 1" class="gallery-indicator">
          <view
            v-for="(_, index) in detail.gallery"
            :key="index"
            class="indicator-dot"
            :class="{ active: currentGalleryIndex === index }"
          />
        </view>
        <view class="gallery-counter">{{ currentGalleryIndex + 1 }}/{{ detail.gallery.length }}</view>
      </view>

      <!-- Product Info -->
      <view class="product-card">
        <view class="price-wrap">
          <text class="price-symbol">¥</text>
          <text class="price-value">{{ detail.price }}</text>
          <view v-if="detail.originPrice" class="price-tag">
            <text class="price-tag-text">限时特惠</text>
          </view>
        </view>
        <view v-if="detail.originPrice" class="price-original">
          <text>原价 ¥{{ detail.originPrice }}</text>
          <view class="discount-badge">
            <text>{{ Math.round(Number(detail.price) / Number(detail.originPrice) * 10) }}折</text>
          </view>
        </view>
        <text class="product-title">{{ detail.title }}</text>
        <view class="meta-row">
          <view class="meta-item">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
              <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <text>{{ isFavorite ? '已收藏' : '收藏' }}</text>
          </view>
          <view class="meta-divider" />
          <view class="meta-item">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
              <path d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <text>{{ detail.stockText }}</text>
          </view>
        </view>
        <view v-if="detail.highlights.length" class="tag-wrap">
          <text v-for="tag in detail.highlights" :key="tag" class="product-tag">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
              <path d="M20 6L9 17L4 12" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            {{ tag }}
          </text>
        </view>
      </view>

      <!-- Payment Settings -->
      <view class="settings-card">
        <text class="section-title">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
            <rect x="1" y="4" width="22" height="16" rx="2" stroke="currentColor" stroke-width="2"/>
            <path d="M1 10H23" stroke="currentColor" stroke-width="2"/>
          </svg>
          支付设置
        </text>

        <view class="setting-row">
          <view class="setting-info">
            <text class="setting-label">购买数量</text>
            <text class="setting-hint">小计 ¥{{ subtotal }}</text>
          </view>
          <view class="stepper">
            <view class="step-btn" :class="{ disabled: quantity <= 1 }" @click="changeQuantity(-1)">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                <path d="M5 12H19" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
              </svg>
            </view>
            <text class="step-value">{{ quantity }}</text>
            <view class="step-btn" :class="{ disabled: quantity >= detail.stock }" @click="changeQuantity(1)">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                <path d="M12 5V19M5 12H19" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
              </svg>
            </view>
          </view>
        </view>

        <view class="payment-options">
          <view
            v-for="item in paymentOptions"
            :key="item.key"
            class="pay-option"
            :class="{ active: selectedPayKey === item.key, disabled: !item.available }"
            @click="selectPaymentOption(item)"
          >
            <view class="pay-option-header">
              <view class="pay-radio">
                <view v-if="selectedPayKey === item.key" class="pay-radio-dot" />
              </view>
              <text class="pay-title">{{ item.label }}</text>
            </view>
            <text class="pay-desc">{{ item.desc }}</text>
          </view>
        </view>

        <view v-if="purchaseMode !== 'CASH_ONLY'" class="points-row">
          <view class="setting-info">
            <text class="setting-label">积分抵扣</text>
            <text class="setting-hint">可填 0</text>
          </view>
          <input class="points-input" v-model="pointsAmount" type="digit" placeholder="0" />
        </view>

        <view class="summary-section">
          <view class="summary-line">
            <text>商品金额</text>
            <text>¥{{ subtotal }}</text>
          </view>
          <view v-if="Number(normalizedPoints) > 0" class="summary-line">
            <text>积分抵扣</text>
            <text class="discount">-¥{{ normalizedPoints }}</text>
          </view>
          <view class="summary-line total">
            <text>{{ cashLabel }}</text>
            <text class="total-price">¥{{ cashAmount }}</text>
          </view>
        </view>
      </view>

      <!-- Features -->
      <view class="features-card">
        <text class="section-title">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
            <path d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          商品亮点
        </text>
        <view class="feature-grid">
          <view v-for="item in detail.features" :key="item" class="feature-item">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              <path d="M22 4L12 14.01L9 11.01" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <text>{{ item }}</text>
          </view>
        </view>
      </view>

      <!-- Details -->
      <view class="details-card">
        <text class="section-title">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
            <rect x="3" y="3" width="18" height="18" rx="2" stroke="currentColor" stroke-width="2"/>
            <path d="M3 9H21" stroke="currentColor" stroke-width="2"/>
            <path d="M9 21V9" stroke="currentColor" stroke-width="2"/>
          </svg>
          图文详情
        </text>
        <view v-for="(item, idx) in detail.items" :key="idx" class="detail-item">{{ item }}</view>
      </view>

      <view class="bottom-space" />
    </template>

    <!-- Action Bar -->
    <view v-if="!loading && !failed" class="action-bar">
      <view class="action-tools">
        <view class="tool-item" @click="toggleFavorite">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
            <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" :fill="isFavorite ? 'currentColor' : 'none'" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          <text class="tool-label">{{ isFavorite ? '已收藏' : '收藏' }}</text>
        </view>
        <view class="tool-item" @click="goCart">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
            <path d="M6 2L3 6V20C3 20.5304 3.21071 21.0391 3.58579 21.4142C3.96086 21.7893 4.46957 22 5 22H19C19.5304 22 20.0391 21.7893 20.4142 21.4142C20.7893 21.0391 21 20.5304 21 20V6L18 2H6Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M3 6H21" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M16 10C16 11.0609 15.5786 12.0783 14.8284 12.8284C14.0783 13.5786 13.0609 14 12 14C10.9391 14 9.92172 13.5786 9.17157 12.8284C8.42143 12.0783 8 11.0609 8 10" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          <text class="tool-label">购物车</text>
        </view>
      </view>
      <view class="action-buttons">
        <button class="action-btn secondary" @click="addToCart">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
            <path d="M6 2L3 6V20C3 20.5304 3.21071 21.0391 3.58579 21.4142C3.96086 21.7893 4.46957 22 5 22H19C19.5304 22 20.0391 21.7893 20.4142 21.4142C20.7893 21.0391 21 20.5304 21 20V6L18 2H6Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M12 11V17M9 14H15" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
          </svg>
          加入购物车
        </button>
        <button class="action-btn primary" @click="createAndPay">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
            <rect x="1" y="4" width="22" height="16" rx="2" stroke="currentColor" stroke-width="2"/>
            <path d="M1 10H23" stroke="currentColor" stroke-width="2"/>
          </svg>
          去结算
        </button>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed, ref, watch } from 'vue';
import { onLoad } from '@dcloudio/uni-app';
import { assetApi, commerceApi, packageApi } from '@/api/modules';
import { getApiBaseUrl } from '@/config/index';
import { normalizePaymentOptions } from '@/utils/payment-options';
import { trackEvent, trackPageView } from '@/utils/track';

const LEGACY_FILE_BASE_URL = 'https://file.hoh516.com/huohonghuo';
const loading = ref(false);
const failed = ref(false);
const id = ref('');
const isFavorite = ref(false);
const quantity = ref(1);
const pointsAmount = ref('');
const payChannel = ref('BALANCE');
const purchaseMode = ref('CASH_ONLY');
const selectedPayKey = ref('');
const assetSummary = ref({});
const currentGalleryIndex = ref(0);

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

const paymentOptions = computed(() => {
  return normalizePaymentOptions(detail.value.paymentOptions).map((item) => {
    const balanceSufficient = item.value !== 'BALANCE'
      || Number(assetSummary.value.BALANCE || 0) >= Number(subtotal.value || 0);
    const available = item.available !== false && balanceSufficient;
    return {
      ...item,
      desc: !balanceSufficient ? `${item.desc}（余额不足）` : item.desc,
      available,
      unavailable_reason: !balanceSufficient ? '账户余额不足' : item.unavailable_reason
    };
  });
});

const subtotal = computed(() => {
  return (Number(detail.value.price || 0) * Number(quantity.value || 1)).toFixed(2);
});

const normalizedPoints = computed(() => {
  const option = paymentOptions.value.find(o => o.key === selectedPayKey.value);
  if (!option || option.purchase_mode === 'CASH_ONLY') return '0.00';
  const amount = Math.max(0, Number(pointsAmount.value || 0));
  const maxPoints = Math.max(0, Number(subtotal.value) - 0.01);
  return Math.min(amount, maxPoints).toFixed(2);
});

const cashAmount = computed(() => {
  return Math.max(0, Number(subtotal.value) - Number(normalizedPoints.value)).toFixed(2);
});

const cashLabel = computed(() => ({
  BALANCE: '余额支付',
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

const normalize = (res) => {
  const price = Number(res?.price ?? res?.sale_price ?? 0);
  const marketPrice = Number(res?.market_price ?? 0);
  const soldCount = Number(res?.sold_count ?? res?.sales_volume ?? 0);
  const stock = Number(res?.stock ?? 0);
  const gallery = resolveGallery(res);
  const features = Array.isArray(res?.features) && res.features.length ? res.features : ['官方精选', '品质保障', '支持支付'];
  const items = Array.isArray(res?.items) && res.items.length ? res.items : (Array.isArray(res?.content) && res.content.length ? res.content : ['暂无更多说明']);

  return {
    title: res?.name || res?.title || '未命名商品',
    desc: res?.description || res?.desc || '暂无描述',
    tag: res?.tag || '精选商品',
    category: res?.category_name || res?.tag || '精选商品',
    image: gallery[0] || '',
    gallery,
    price: price > 0 ? price.toFixed(2) : '0.00',
    originPrice: marketPrice > price ? marketPrice.toFixed(2) : '',
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
    isFavorite.value = false;
  }
};

watch(
  () => detail.value.defaultPayChannel,
  (value) => {
    if (!value || selectedPayKey.value) return;
    const option = paymentOptions.value.find((item) => item.value === value && item.available !== false)
      || paymentOptions.value.find((item) => item.available !== false)
      || paymentOptions.value[0];
    if (option) selectPaymentOption(option);
  },
  { immediate: true }
);

watch(
  paymentOptions,
  (options) => {
    if (!options.length) return;
    const available = options.find((item) => item.available !== false);
    const target = available || options[0];
    if (target && !options.some((item) => item.key === selectedPayKey.value)) {
      selectPaymentOption(target);
    }
  },
  { immediate: true }
);

const loadDetail = async () => {
  if (!id.value) return;
  loading.value = true;
  failed.value = false;
  try {
    const [res, assets] = await Promise.all([packageApi.detail(id.value), assetApi.summary()]);
    detail.value = normalize(res || {});
    assetSummary.value = assets || {};
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

const onGalleryChange = (e) => {
  currentGalleryIndex.value = e.detail.current;
};

onLoad((query) => {
  id.value = query?.id || '';
  trackPageView('package_detail_view', { id: id.value });
  loadDetail();
});

const goBack = () => uni.navigateBack();

const shareProduct = () => {
  uni.showToast({ title: '分享功能开发中', icon: 'none' });
};

function changeQuantity(delta) {
  const next = Math.max(1, Number(quantity.value || 1) + delta);
  if (detail.value.stock > 0 && next > detail.value.stock) {
    uni.showToast({ title: '库存不足', icon: 'none' });
    return;
  }
  quantity.value = next;
}

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
  uni.switchTab({ url: '/pages/cart/index' });
};

const createAndPay = () => {
  if (!['HOT_SALE', 'SELF_OPERATED', 'REPURCHASE'].includes(detail.value.zoneType)) {
    uni.showToast({ title: '当前商品暂不支持下单', icon: 'none' });
    return;
  }
  if (!paymentOptions.value.length) {
    uni.showToast({ title: '当前商品暂不支持支付', icon: 'none' });
    return;
  }
  trackEvent('package_detail_checkout', { id: id.value, zone_type: detail.value.zoneType });
  const params = [
    `product_id=${encodeURIComponent(String(id.value))}`,
    `quantity=${encodeURIComponent(String(Number(quantity.value || 1)))}`,
    `pay_channel=${encodeURIComponent(payChannel.value)}`,
    `purchase_mode=${encodeURIComponent(purchaseMode.value)}`,
    `points_amount=${encodeURIComponent(normalizedPoints.value)}`
  ].join('&');
  uni.navigateTo({ url: `/subpackages/order/confirm?${params}` });
};
</script>

<style scoped>
@import '@/styles/common.css';

.detail-page {
  min-height: 100vh;
  background: var(--bg);
  padding-bottom: calc(env(safe-area-inset-bottom) + 140rpx);
}

/* Header */
.page-header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16rpx 24rpx;
  padding-top: calc(16rpx + env(safe-area-inset-top));
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(20rpx);
  -webkit-backdrop-filter: blur(20rpx);
}

.back-btn,
.share-btn {
  width: 72rpx;
  height: 72rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.8);
  border-radius: var(--radius-full);
  color: var(--text);
  transition: all var(--duration-fast) var(--ease-out);
}

.back-btn:active,
.share-btn:active {
  transform: scale(0.92);
  background: var(--bg);
}

.header-title {
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  color: var(--text);
}

/* Gallery */
.gallery-section {
  position: relative;
  background: var(--card);
  padding-top: calc(88rpx + env(safe-area-inset-top));
}

.gallery-swiper {
  width: 100%;
  height: 750rpx;
}

.gallery-image {
  width: 100%;
  height: 100%;
}

.gallery-placeholder {
  width: 100%;
  height: 750rpx;
  background: linear-gradient(135deg, var(--primary-bg), var(--primary-light));
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--primary);
}

.gallery-indicator {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  bottom: 24rpx;
  display: flex;
  gap: 12rpx;
  padding: 12rpx 20rpx;
  background: rgba(0, 0, 0, 0.2);
  border-radius: var(--radius-full);
}

.indicator-dot {
  width: 8rpx;
  height: 8rpx;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.4);
  transition: all var(--duration-normal) var(--ease-out);
}

.indicator-dot.active {
  width: 24rpx;
  border-radius: 4rpx;
  background: white;
}

.gallery-counter {
  position: absolute;
  right: 24rpx;
  bottom: 24rpx;
  padding: 8rpx 20rpx;
  background: rgba(0, 0, 0, 0.4);
  color: white;
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  border-radius: var(--radius-full);
  backdrop-filter: blur(8rpx);
}

/* Product Card */
.product-card {
  padding: 32rpx;
  background: var(--card);
  margin-top: 2rpx;
}

.price-wrap {
  display: flex;
  align-items: baseline;
  gap: 8rpx;
  margin-bottom: 8rpx;
}

.price-symbol {
  font-size: var(--text-lg);
  font-weight: var(--font-bold);
  color: var(--danger);
}

.price-value {
  font-size: 64rpx;
  font-weight: var(--font-bold);
  color: var(--danger);
  line-height: 1;
}

.price-tag {
  margin-left: 16rpx;
  padding: 8rpx 16rpx;
  background: linear-gradient(135deg, var(--accent), var(--accent-light));
  border-radius: var(--radius-sm);
}

.price-tag-text {
  font-size: 20rpx;
  font-weight: var(--font-bold);
  color: white;
}

.price-original {
  display: flex;
  align-items: center;
  gap: 16rpx;
  margin-bottom: 20rpx;
}

.price-original text {
  font-size: var(--text-sm);
  color: var(--text-muted);
  text-decoration: line-through;
}

.discount-badge {
  padding: 4rpx 12rpx;
  background: var(--danger-bg);
  border-radius: var(--radius-sm);
}

.discount-badge text {
  font-size: 20rpx;
  font-weight: var(--font-bold);
  color: var(--danger);
  text-decoration: none !important;
}

.product-title {
  font-size: var(--text-xl);
  font-weight: var(--font-bold);
  color: var(--text);
  line-height: 1.5;
  display: block;
  margin-bottom: 20rpx;
}

.meta-row {
  display: flex;
  align-items: center;
  gap: 24rpx;
  margin-bottom: 24rpx;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 8rpx;
  color: var(--text-muted);
  font-size: var(--text-xs);
}

.meta-divider {
  width: 1rpx;
  height: 24rpx;
  background: var(--border);
}

.tag-wrap {
  display: flex;
  flex-wrap: wrap;
  gap: 12rpx;
}

.product-tag {
  display: inline-flex;
  align-items: center;
  gap: 8rpx;
  padding: 10rpx 20rpx;
  background: var(--primary-bg);
  color: var(--primary);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  border-radius: var(--radius-full);
}

/* Settings Card */
.settings-card {
  margin: 24rpx;
  padding: 32rpx;
  background: var(--card);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-sm);
}

.section-title {
  display: flex;
  align-items: center;
  gap: 12rpx;
  font-size: var(--text-lg);
  font-weight: var(--font-bold);
  color: var(--text);
  margin-bottom: 28rpx;
}

.setting-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 28rpx;
  background: var(--bg);
  border-radius: var(--radius-lg);
  margin-bottom: 24rpx;
}

.setting-info {
  display: flex;
  flex-direction: column;
  gap: 6rpx;
}

.setting-label {
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  color: var(--text);
}

.setting-hint {
  font-size: var(--text-xs);
  color: var(--text-muted);
}

.stepper {
  display: flex;
  align-items: center;
  background: var(--card);
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: var(--shadow-xs);
}

.step-btn {
  width: 72rpx;
  height: 72rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--primary);
  transition: all var(--duration-fast) var(--ease-out);
}

.step-btn:active:not(.disabled) {
  background: var(--primary-bg);
}

.step-btn.disabled {
  color: var(--text-disabled);
}

.step-value {
  width: 80rpx;
  text-align: center;
  font-size: var(--text-lg);
  font-weight: var(--font-bold);
  color: var(--text);
  border-left: 1rpx solid var(--border);
  border-right: 1rpx solid var(--border);
}

.payment-options {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16rpx;
  margin-bottom: 24rpx;
}

.pay-option {
  padding: 24rpx;
  background: var(--bg);
  border-radius: var(--radius-lg);
  border: 2rpx solid transparent;
  transition: all var(--duration-fast) var(--ease-out);
}

.pay-option.active {
  border-color: var(--primary);
  background: var(--primary-bg);
}

.pay-option.disabled {
  opacity: 0.5;
}

.pay-option-header {
  display: flex;
  align-items: center;
  gap: 12rpx;
  margin-bottom: 8rpx;
}

.pay-radio {
  width: 32rpx;
  height: 32rpx;
  border: 2rpx solid var(--border);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--duration-fast) var(--ease-out);
}

.pay-option.active .pay-radio {
  border-color: var(--primary);
}

.pay-radio-dot {
  width: 16rpx;
  height: 16rpx;
  background: var(--primary);
  border-radius: 50%;
}

.pay-title {
  font-size: var(--text-base);
  font-weight: var(--font-bold);
  color: var(--text);
}

.pay-desc {
  font-size: var(--text-xs);
  color: var(--text-muted);
  padding-left: 44rpx;
}

.points-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 24rpx 28rpx;
  background: var(--bg);
  border-radius: var(--radius-lg);
  margin-bottom: 24rpx;
}

.points-input {
  width: 180rpx;
  height: 64rpx;
  padding: 0 24rpx;
  text-align: center;
  background: var(--card);
  border-radius: var(--radius-md);
  font-size: var(--text-lg);
  font-weight: var(--font-bold);
  color: var(--text);
  box-shadow: var(--shadow-xs);
}

.summary-section {
  padding-top: 24rpx;
  border-top: 1rpx solid var(--border);
}

.summary-line {
  display: flex;
  justify-content: space-between;
  font-size: var(--text-sm);
  color: var(--text-muted);
  margin-bottom: 16rpx;
}

.summary-line .discount {
  color: var(--success);
}

.summary-line.total {
  font-size: var(--text-lg);
  font-weight: var(--font-bold);
  color: var(--text);
  margin-top: 20rpx;
  padding-top: 20rpx;
  border-top: 2rpx dashed var(--border);
}

.total-price {
  color: var(--danger);
}

/* Features Card */
.features-card {
  margin: 0 24rpx 24rpx;
  padding: 32rpx;
  background: var(--card);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-sm);
}

.feature-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16rpx;
}

.feature-item {
  display: flex;
  align-items: center;
  gap: 12rpx;
  padding: 24rpx;
  background: var(--bg);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.feature-item svg {
  color: var(--success);
  flex-shrink: 0;
}

/* Details Card */
.details-card {
  margin: 0 24rpx;
  padding: 32rpx;
  background: var(--card);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-sm);
  margin-bottom: 24rpx;
}

.detail-item {
  padding: 24rpx;
  background: var(--bg);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  color: var(--text-secondary);
  line-height: 1.7;
  margin-top: 16rpx;
}

/* Loading State */
.loading-state {
  padding-top: calc(88rpx + env(safe-area-inset-top));
}

.skeleton-hero {
  width: 100%;
  height: 750rpx;
}

.skeleton-content {
  padding: 32rpx;
}

.skeleton {
  background: linear-gradient(90deg, var(--border-light) 25%, var(--bg) 50%, var(--border-light) 75%);
  background-size: 200% 100%;
  animation: skeleton-shimmer 1.5s infinite;
  border-radius: var(--radius-md);
}

.skeleton-price {
  height: 80rpx;
  width: 50%;
  margin-bottom: 20rpx;
}

.skeleton-title {
  height: 48rpx;
  width: 90%;
  margin-bottom: 16rpx;
}

.skeleton-title.short {
  width: 60%;
  margin-bottom: 40rpx;
}

.skeleton-actions {
  display: flex;
  gap: 24rpx;
  margin-top: 48rpx;
}

.skeleton-action {
  flex: 1;
  height: 88rpx;
  border-radius: var(--radius-lg);
}

@keyframes skeleton-shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* State View */
.state-view {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 200rpx 32rpx;
  padding-top: calc(200rpx + env(safe-area-inset-top));
}

.state-icon {
  color: var(--border);
  margin-bottom: 32rpx;
}

.state-icon.error {
  color: var(--error);
}

.state-title {
  font-size: var(--text-xl);
  font-weight: var(--font-semibold);
  color: var(--text);
  margin-bottom: 12rpx;
}

.state-desc {
  font-size: var(--text-base);
  color: var(--text-muted);
  margin-bottom: 40rpx;
}

.state-action {
  display: flex;
  align-items: center;
  gap: 12rpx;
  padding: 20rpx 40rpx;
  background: linear-gradient(135deg, var(--primary), var(--primary-dark));
  color: white;
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  border-radius: var(--radius-full);
  box-shadow: var(--shadow-primary);
}

.state-action:active {
  opacity: 0.9;
  transform: scale(0.98);
}

.bottom-space {
  height: 40rpx;
}

/* Action Bar */
.action-bar {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  padding: 16rpx 24rpx;
  padding-bottom: calc(16rpx + env(safe-area-inset-bottom));
  background: var(--card);
  border-top: 1rpx solid var(--border);
  box-shadow: 0 -8rpx 32rpx rgba(0, 0, 0, 0.06);
}

.action-tools {
  display: flex;
  gap: 40rpx;
  margin-right: 32rpx;
}

.tool-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6rpx;
  color: var(--text);
  transition: color var(--duration-fast) var(--ease-out);
}

.tool-item:active {
  transform: scale(0.95);
  color: var(--primary);
}

.tool-label {
  font-size: 20rpx;
  color: var(--text-muted);
}

.action-buttons {
  flex: 1;
  display: flex;
  gap: 16rpx;
}

.action-btn {
  flex: 1;
  height: 88rpx;
  border-radius: var(--radius-lg);
  font-size: var(--text-base);
  font-weight: var(--font-bold);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12rpx;
  border: none;
  transition: all var(--duration-fast) var(--ease-out);
}

.action-btn.secondary {
  background: var(--card);
  color: var(--primary);
  border: 2rpx solid var(--primary);
}

.action-btn.secondary:active {
  background: var(--primary-bg);
}

.action-btn.primary {
  background: linear-gradient(135deg, var(--primary), var(--primary-dark));
  color: white;
  box-shadow: var(--shadow-primary);
}

.action-btn.primary:active {
  transform: scale(0.98);
  opacity: 0.9;
}

/* Reduced Motion */
@media (prefers-reduced-motion: reduce) {
  .back-btn,
  .share-btn,
  .step-btn,
  .tool-item,
  .action-btn,
  .pay-option,
  .indicator-dot {
    transition: none;
  }

  .skeleton {
    animation: none;
  }
}
</style>
