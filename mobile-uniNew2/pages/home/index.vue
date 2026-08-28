<template>
  <view class="home-page">
    <view class="banner-section">
      <swiper
        class="banner-swiper"
        circular
        autoplay
        interval="5000"
        indicator-dots
        indicator-color="rgba(255, 255, 255, 0.45)"
        indicator-active-color="#FFFFFF"
        :current="currentBanner"
        @change="onBannerChange"
      >
        <swiper-item v-for="item in banners" :key="item.id">
          <view class="banner-card" :style="bannerStyle(item)" @click="openDecorationLink(item)">
            <image v-if="item.image" class="banner-image" :src="item.image" mode="aspectFill" />
          </view>
        </swiper-item>
      </swiper>
    </view>

    <view class="hot-section">
      <view class="section-header">
        <view class="section-left">
          <text class="hot-title">爆款推荐</text>
          <view class="hot-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
              <path d="M12 2L14.09 8.26L20.18 9.27L15.54 13.14L16.82 19.02L12 16.09L7.18 19.02L8.46 13.14L3.82 9.27L9.91 8.26L12 2Z" fill="currentColor" />
            </svg>
          </view>
        </view>
      </view>

      <view v-if="loading" class="hot-grid">
        <view v-for="i in 4" :key="i" class="hot-card">
          <view class="skeleton hot-skeleton-image" />
          <view class="skeleton hot-skeleton-title" />
          <view class="skeleton hot-skeleton-price" />
        </view>
      </view>

      <swiper
        v-else-if="hotProducts.length > 4"
        class="hot-swiper"
        circular
        autoplay
        interval="4000"
        :display-multiple-items="4"
        :gap="16"
      >
        <swiper-item v-for="item in hotProducts" :key="item.id">
          <view class="hot-card" @click="openProduct(item)">
            <view class="hot-img-wrap">
              <image class="hot-img" :src="item.image" mode="aspectFill" lazy-load />
            </view>
            <view class="hot-info">
              <text class="hot-name">{{ item.title }}</text>
              <view class="hot-price">
                <text class="price-symbol">¥</text>
                <text class="price-value">{{ item.price }}</text>
              </view>
            </view>
          </view>
        </swiper-item>
      </swiper>

      <view v-else class="hot-grid">
        <view
          v-for="item in hotProducts"
          :key="item.id"
          class="hot-card"
          @click="openProduct(item)"
        >
          <view class="hot-img-wrap">
            <image class="hot-img" :src="item.image" mode="aspectFill" lazy-load />
          </view>
          <view class="hot-info">
            <text class="hot-name">{{ item.title }}</text>
            <view class="hot-price">
              <text class="price-symbol">¥</text>
              <text class="price-value">{{ item.price }}</text>
            </view>
          </view>
        </view>
      </view>
    </view>

    <view class="featured-section">
      <view class="section-header">
        <text class="section-title">推荐好货</text>
      </view>

      <view v-if="loading" class="product-grid">
        <view v-for="i in 6" :key="i" class="product-card">
          <view class="skeleton skeleton-image" />
          <view class="product-info">
            <view class="skeleton skeleton-title" />
            <view class="skeleton skeleton-price" />
          </view>
        </view>
      </view>

      <view v-else-if="products.length > 0" class="product-grid">
        <view
          v-for="item in products"
          :key="item.id"
          class="product-card"
          @click="openProduct(item)"
        >
          <view class="product-img-wrap">
            <image class="product-img" :src="item.image" mode="aspectFill" lazy-load />
          </view>
          <view class="product-info">
            <text class="product-name">{{ item.title }}</text>
            <view class="product-bottom">
              <view class="price">
                <text class="price-currency">¥</text>
                <text class="price-value">{{ item.price }}</text>
                <text v-if="item.original" class="price-original">¥{{ item.original }}</text>
              </view>
              <view class="add-btn">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                  <path d="M12 5V19M5 12H19" stroke="white" stroke-width="2" stroke-linecap="round" />
                </svg>
              </view>
            </view>
          </view>
        </view>
      </view>

      <view v-else class="empty-state">
        <text class="empty-text">暂无商品</text>
      </view>
    </view>

    <view class="bottom-space" />
  </view>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { onPullDownRefresh, onShow } from '@dcloudio/uni-app';
import { homeApi, packageApi } from '@/api/modules';
import { getAssetBaseUrl } from '@/config/index';
import { trackEvent, trackPageView } from '@/utils/track';
import { selectImageSwiperBlock } from '@/utils/home-decoration';

const BASE_URL = 'https://file.h516.com/huohonghuo';

const currentBanner = ref(0);
const banners = ref([]);
const hotProducts = ref([]);
const products = ref([]);
const loading = ref(false);

const defaultBanners = [
  {
    id: 1,
    gradient: 'linear-gradient(135deg, #059669 0%, #10B981 50%, #34D399 100%)'
  },
  {
    id: 2,
    gradient: 'linear-gradient(135deg, #D97706 0%, #F59E0B 50%, #FBBF24 100%)'
  },
  {
    id: 3,
    gradient: 'linear-gradient(135deg, #3B82F6 0%, #60A5FA 50%, #93C5FD 100%)'
  }
];

banners.value = [...defaultBanners];

const onBannerChange = (e) => {
  currentBanner.value = e.detail.current;
};

const resolveImage = (value) => {
  if (!value) return '';
  if (/^https?:\/\//i.test(value)) return value;
  if (value.startsWith('/profile/')) return `${BASE_URL}${value}`;
  if (value.startsWith('/')) return `${getAssetBaseUrl()}${value}`;
  return value;
};

const enabledItems = (items = []) => {
  return (Array.isArray(items) ? items : []).filter((item) => item && item.enabled !== false);
};

const normalizeProducts = (rows) => {
  return (rows || []).map((item, idx) => {
    const salePrice = Number(item.price ?? item.sale_price ?? 0);
    const marketPrice = Number(item.market_price ?? 0);
    return {
      id: item.id || item.product_id || idx,
      title: item.name || item.title || '未命名商品',
      price: salePrice.toFixed(2),
      original: marketPrice > salePrice ? marketPrice.toFixed(2) : '',
      image: resolveImage(item.image || item.main_image || item.cover || '')
    };
  });
};

const normalizeHotProducts = (rows) => {
  const hotRows = (rows || []).filter((item) => item.is_hot === 1 || item.tag === '爆款' || item.is_flash === 1);
  return normalizeProducts(hotRows.length ? hotRows : (rows || []).slice(0, 4));
};

const normalizeBannerItems = (payload) => {
  const swiper = selectImageSwiperBlock(payload);
  const rows = enabledItems(swiper?.items).filter((item) => String(item?.image_url || '').trim());
  if (!rows.length) return [...defaultBanners];
  return rows.map((item, index) => ({
    id: item.id || `${swiper.id || 'swiper'}-${index}`,
    image: resolveImage(String(item.image_url || '').trim()),
    path: item.path || '',
    open_type: item.open_type || 'navigate',
    gradient: defaultBanners[index % defaultBanners.length].gradient
  }));
};

const bannerStyle = (item) => {
  return { background: item.gradient || defaultBanners[0].gradient };
};

const openDecorationLink = (item = {}) => {
  const path = item.path || '';
  if (!path) return;
  trackEvent('home_decoration_link', { path });
  if (item.open_type === 'switchTab') {
    uni.switchTab({ url: path });
    return;
  }
  uni.navigateTo({ url: path });
};

const loadDecoration = async () => {
  try {
    const res = await homeApi.decoration();
    const payload = res?.payload || res;
    banners.value = normalizeBannerItems(payload);
  } catch (error) {
    banners.value = [...defaultBanners];
  }
};

const loadProducts = async () => {
  loading.value = true;
  try {
    const res = await packageApi.list({ page: 1, page_size: 40 });
    const allProducts = Array.isArray(res) ? res : res?.list || res?.items || [];
    hotProducts.value = normalizeHotProducts(allProducts);
    products.value = normalizeProducts(allProducts);
  } catch (error) {
    console.error('加载商品失败', error);
    hotProducts.value = [];
    products.value = [];
  } finally {
    loading.value = false;
  }
};

const loadPageData = async () => {
  await Promise.all([loadDecoration(), loadProducts()]);
  uni.stopPullDownRefresh?.();
};

const openProduct = (item) => {
  trackEvent('home_product', { id: item.id });
  uni.navigateTo({ url: `/subpackages/package/detail?id=${item.id}` });
};

onShow(() => {
  trackPageView('home');
  loadPageData();
});

onMounted(() => {
  trackPageView('home');
  loadPageData();
});

onPullDownRefresh(async () => {
  await loadPageData();
});
</script>

<style scoped>
.home-page {
  --home-gutter: var(--space-4);
  min-height: 100vh;
  background: var(--bg);
  padding-top: calc(env(safe-area-inset-top) + var(--space-4));
  padding-bottom: calc(env(safe-area-inset-bottom) + 140rpx);
}

.banner-section,
.hot-section,
.featured-section {
  padding-left: var(--home-gutter);
  padding-right: var(--home-gutter);
}

.banner-swiper {
  height: 320rpx;
  border-radius: var(--radius-xl);
  overflow: hidden;
  box-shadow: var(--shadow-md);
}

.banner-card {
  height: 100%;
  position: relative;
  overflow: hidden;
}

.banner-image {
  width: 100%;
  height: 100%;
  display: block;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-5);
}

.section-left {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.section-title,
.hot-title {
  display: block;
  font-size: var(--text-lg);
  font-weight: var(--font-bold);
  color: var(--text);
}

.hot-title {
  color: var(--primary);
}

.hot-icon {
  color: var(--accent);
  animation: star-pulse 2s ease-in-out infinite;
}

@keyframes star-pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.7; transform: scale(0.9); }
}

.hot-section {
  padding-top: var(--space-6);
}

.hot-swiper {
  height: 280rpx;
  margin: 0;
}

.hot-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--space-3);
}

.hot-card {
  display: flex;
  flex-direction: column;
  min-width: 0;
  transition: transform var(--duration-fast) var(--ease-spring);
}

.hot-card:active {
  transform: scale(0.96);
}

.hot-img-wrap,
.hot-skeleton-image {
  width: 100%;
  aspect-ratio: 1;
  border-radius: var(--radius-lg);
  background: linear-gradient(135deg, var(--bg) 0%, var(--border-light) 100%);
  overflow: hidden;
  margin-bottom: var(--space-2);
  box-shadow: var(--shadow-sm);
}

.hot-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.hot-info {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.hot-name {
  font-size: var(--text-xs);
  color: var(--text);
  font-weight: var(--font-medium);
  line-height: 1.3;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.hot-price {
  display: flex;
  align-items: baseline;
  gap: 2rpx;
}

.hot-price .price-symbol {
  font-size: var(--text-xs);
  color: var(--primary);
  font-weight: var(--font-semibold);
}

.hot-price .price-value {
  font-size: var(--text-base);
  color: var(--primary);
  font-weight: var(--font-bold);
  font-family: 'DIN Alternate', 'Helvetica Neue', Arial, sans-serif;
}

.featured-section {
  padding-top: var(--space-8);
}

.product-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-4);
}

.product-card {
  background: var(--card);
  border-radius: var(--radius-xl);
  overflow: hidden;
  box-shadow: var(--shadow-sm);
  transition: all var(--duration-fast) var(--ease-out);
}

.product-card:active {
  transform: scale(0.98);
  box-shadow: var(--shadow-xs);
}

.product-img-wrap {
  position: relative;
  width: 100%;
  aspect-ratio: 1;
  background: linear-gradient(135deg, var(--bg) 0%, var(--border-light) 100%);
}

.product-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.product-info {
  padding: var(--space-4);
}

.product-name {
  display: block;
  min-height: 2.4em;
  margin-bottom: var(--space-3);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text);
  line-height: var(--leading-snug);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.product-bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}

.price {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 2rpx;
  min-width: 0;
}

.price-currency {
  font-size: var(--text-sm);
  color: var(--primary);
  font-weight: var(--font-semibold);
}

.price-value {
  font-size: var(--text-lg);
  color: var(--primary);
  font-weight: var(--font-bold);
  font-family: 'DIN Alternate', 'Helvetica Neue', Arial, sans-serif;
}

.price-original {
  margin-left: var(--space-2);
  font-size: 22rpx;
  color: var(--text-muted);
  text-decoration: line-through;
}

.add-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 56rpx;
  height: 56rpx;
  flex: 0 0 56rpx;
  background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
  color: white;
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-primary);
  transition: all var(--duration-fast) var(--ease-out);
}

.add-btn:active {
  transform: scale(0.9);
  box-shadow: var(--shadow-sm);
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-16) 0;
}

.empty-text {
  font-size: var(--text-base);
  color: var(--text-muted);
}

.skeleton {
  background: linear-gradient(
    90deg,
    var(--bg) 0%,
    var(--border-light) 50%,
    var(--bg) 100%
  );
  background-size: 200% 100%;
  animation: skeleton-loading 1.5s ease-in-out infinite;
}

@keyframes skeleton-loading {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.skeleton-image {
  width: 100%;
  aspect-ratio: 1;
}

.skeleton-title,
.hot-skeleton-title {
  height: 32rpx;
  border-radius: var(--radius-sm);
  margin-bottom: var(--space-3);
}

.skeleton-price,
.hot-skeleton-price {
  width: 120rpx;
  height: 36rpx;
  border-radius: var(--radius-sm);
}

.bottom-space {
  height: var(--space-8);
}

@media (prefers-reduced-motion: reduce) {
  .hot-icon,
  .add-btn,
  .product-card {
    transition: none;
    animation: none;
  }
}
</style>
