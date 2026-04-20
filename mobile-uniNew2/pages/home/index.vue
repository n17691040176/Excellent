<template>
  <view class="container home-page">
    <view class="mall-header" :class="{ sticky: headerSticky }">
      <view class="brand-row" :class="{ compact: headerSticky }">
        <view class="brand-left">
          <view class="brand-logo">Excellent</view>
          <view class="brand-slogan" v-if="!headerSticky">甄选好物 同城生活</view>
        </view>
        <view class="brand-entry interactive" @click="go('/pages/profile/index', true, 'profile')">我的</view>
      </view>

      <view class="search-row interactive" @click="go('/pages/packages/list', true, 'search_bar')">
        <view class="search-icon">搜</view>
        <view class="search-placeholder">{{ activeSearchPlaceholder }}</view>
        <view class="search-btn">搜索</view>
      </view>
    </view>

    <view class="hero-swiper card ecom-shadow-soft">
      <swiper
        class="hero-swiper-inner"
        circular
        autoplay
        interval="3200"
        duration="360"
        indicator-dots
        indicator-color="rgba(255,122,0,0.22)"
        indicator-active-color="#ff7a00"
      >
        <swiper-item v-for="slide in heroSlides" :key="slide.key">
          <view class="hero-slide interactive" @click="go(slide.path, slide.isTab, slide.key)">
            <view class="hero-top row-between">
              <view>
                <view class="hero-kicker">{{ slide.kicker }}</view>
                <view class="hero-title">{{ slide.title }}</view>
                <view class="hero-subtitle">{{ slide.subtitle }}</view>
              </view>
              <view class="hero-tag">{{ slide.tag }}</view>
            </view>
            <view class="hero-point">{{ slide.point }}</view>
          </view>
        </swiper-item>
      </swiper>
    </view>

    <view class="recommend mt-24">
      <view class="row-between recommend-head">
        <view>
          <view class="section-title no-margin">精选商品</view>
          <view class="recommend-subtitle">双列瀑布流，快速找到想买的好物</view>
        </view>
        <view class="recommend-count">持续上新</view>
      </view>

      <view v-if="loading" class="recommend-state">商品加载中...</view>
      <view v-else-if="failed" class="recommend-state">
        商品加载失败
        <button class="btn btn-ghost retry-btn mt-16" @click="loadRecommend">重试</button>
      </view>
      <view v-else-if="!recommends.length" class="recommend-state">暂无推荐商品</view>

      <view v-else class="waterfall-grid">
        <view
          v-for="item in recommends"
          :key="item.id"
          class="waterfall-card interactive"
          @click="openRecommend(item)"
        >
          <image v-if="item.image" class="waterfall-cover" :src="item.image" mode="aspectFill" lazy-load />
          <view v-else class="waterfall-cover waterfall-cover-fallback" />

          <view class="waterfall-body">
            <view class="waterfall-badge-row">
              <text class="waterfall-badge">{{ item.badge }}</text>
              <text v-if="item.tip" class="waterfall-tip">{{ item.tip }}</text>
            </view>
            <view class="waterfall-title">{{ item.title }}</view>
            <view class="waterfall-desc">{{ item.desc }}</view>
            <view class="waterfall-price-row">
              <view class="ecom-price">
                <text class="ecom-price-main">¥{{ item.price }}</text>
                <text v-if="item.marketPrice" class="ecom-price-origin">¥{{ item.marketPrice }}</text>
              </view>
            </view>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue';
import { onHide, onPageScroll, onPullDownRefresh, onShow } from '@dcloudio/uni-app';
import { packageApi } from '@/api/modules';
import { getApiBaseUrl } from '@/config/index';
import { trackEvent, trackPageView } from '@/utils/track';

const LEGACY_FILE_BASE_URL = 'https://file.hoh516.com/huohonghuo';

const heroSlides = [
  {
    key: 'mall',
    kicker: 'Excellent',
    title: '精选商城',
    subtitle: '商品与服务统一接入，一个首页就能逛全站',
    tag: '热卖',
    point: '商品更全，浏览更快',
    path: '/pages/packages/list',
    isTab: true
  },
  {
    key: 'quality',
    kicker: 'Excellent',
    title: '品质优选',
    subtitle: '高意向商品集中呈现，少筛选，直达好货',
    tag: '精选',
    point: '双列商品流畅浏览',
    path: '/pages/packages/list',
    isTab: true
  },
  {
    key: 'service',
    kicker: 'Excellent',
    title: '本地生活',
    subtitle: '到店与上门服务同步覆盖，入口保持统一',
    tag: '附近',
    point: '服务频道与商品频道无缝切换',
    path: '/pages/local-life/index',
    isTab: true
  }
];

const searchPlaceholders = ['搜智能手表', '搜共享设备', '搜海鲜礼盒', '搜品质好物'];

const loading = ref(false);
const failed = ref(false);
const headerSticky = ref(false);
const searchPlaceholderIndex = ref(0);
const searchTimer = ref(null);
const recommends = ref([]);

const activeSearchPlaceholder = computed(() => {
  return searchPlaceholders[searchPlaceholderIndex.value] || searchPlaceholders[0];
});

const resolveImage = (value) => {
  if (!value) return '';
  if (/^https?:\/\//i.test(value)) return value;
  if (value.startsWith('/profile/')) return `${LEGACY_FILE_BASE_URL}${value}`;
  if (value.startsWith('/')) return `${getApiBaseUrl()}${value}`;
  return value;
};

const normalizeRows = (rows) => {
  return (rows || []).map((item, idx) => {
    const salePrice = Number(item.price ?? item.sale_price ?? 0);
    const marketPrice = Number(item.market_price ?? 0);
    const badge = item.tag || item.category_name || '精选';

    return {
      id: item.id || item.product_id || `home-${idx}`,
      title: item.name || item.title || '未命名商品',
      desc: item.description || item.desc || '暂无描述',
      price: salePrice.toFixed(2),
      marketPrice: marketPrice > salePrice ? marketPrice.toFixed(2) : '',
      badge,
      tip: salePrice >= 999 ? '高配' : salePrice <= 99 ? '实惠' : '',
      image: resolveImage(item.image || item.main_image || item.cover || item.gallery?.[0]),
      path: `/subpackages/package/detail?id=${item.id || item.product_id || idx}`
    };
  });
};

function homeTrack(event, payload = {}) {
  trackEvent(event, {
    page: '/pages/home/index',
    ...payload
  });
}

function startSearchPlaceholderTicker() {
  stopSearchPlaceholderTicker();
  searchTimer.value = setInterval(() => {
    searchPlaceholderIndex.value = (searchPlaceholderIndex.value + 1) % searchPlaceholders.length;
  }, 2600);
}

function stopSearchPlaceholderTicker() {
  if (searchTimer.value) {
    clearInterval(searchTimer.value);
    searchTimer.value = null;
  }
}

const loadRecommend = async () => {
  loading.value = true;
  failed.value = false;
  try {
    const res = await packageApi.list({ page: 1, page_size: 40 });
    recommends.value = normalizeRows(Array.isArray(res) ? res : res?.list || res?.items || []);
    homeTrack('home_data_loaded', { recommend_count: recommends.value.length });
  } catch (error) {
    failed.value = true;
  } finally {
    loading.value = false;
  }
};

const go = (path, isTab = false, entry = 'default') => {
  homeTrack('home_entry_click', { path, isTab, entry });
  if (isTab) {
    uni.switchTab({ url: path });
    return;
  }
  uni.navigateTo({ url: path });
};

function openRecommend(item) {
  homeTrack('home_waterfall_item_click', {
    item_id: item.id,
    item_title: item.title,
    item_price: item.price
  });
  uni.navigateTo({ url: item.path });
}

onShow(() => {
  trackPageView('home');
  startSearchPlaceholderTicker();
  loadRecommend();
});

onHide(() => {
  stopSearchPlaceholderTicker();
});

onPageScroll((event) => {
  const top = event?.scrollTop || 0;
  headerSticky.value = top > 56;
  uni.$emit('excellent:tabbar-scroll', {
    compact: top > 80,
    opacity: top > 120 ? 0.9 : 0.98
  });
});

onPullDownRefresh(async () => {
  await loadRecommend();
  uni.stopPullDownRefresh();
});
</script>

<style scoped>
@import '@/styles/common.css';

.home-page {
  padding-top: 0;
  padding-bottom: 36rpx;
}

.mall-header {
  position: sticky;
  top: var(--status-bar-height);
  z-index: 30;
  margin: 0 -24rpx 18rpx;
  padding: 18rpx 24rpx 16rpx;
  background:
    radial-gradient(circle at 10% 0%, rgba(255, 236, 213, 0.3), transparent 28%),
    radial-gradient(circle at 92% 12%, rgba(255, 255, 255, 0.24), transparent 22%),
    linear-gradient(135deg, #dec09a 0%, #cf9d69 58%, #bf8752 100%);
  border-bottom-left-radius: 28rpx;
  border-bottom-right-radius: 28rpx;
  border: 1rpx solid rgba(255, 255, 255, 0.26);
  box-shadow:
    0 12rpx 28rpx rgba(118, 78, 42, 0.2),
    inset 0 1rpx 0 rgba(255, 255, 255, 0.22);
  transition: all 0.2s ease;
}

.mall-header.sticky {
  padding-top: 10rpx;
  padding-bottom: 10rpx;
}

.brand-row {
  display: flex;
  align-items: center;
  margin-bottom: 12rpx;
  justify-content: space-between;
}

.brand-left {
  display: flex;
  align-items: center;
  gap: 12rpx;
}

.brand-logo {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 132rpx;
  height: 50rpx;
  padding: 0 16rpx;
  border-radius: 999rpx;
  background: rgba(255, 255, 255, 0.16);
  border: 1rpx solid rgba(255, 255, 255, 0.26);
  box-shadow: inset 0 1rpx 0 rgba(255, 255, 255, 0.22);
  font-size: 30rpx;
  font-weight: 800;
  color: #fffdf8;
  letter-spacing: 0.8rpx;
}

.brand-slogan {
  color: rgba(255, 248, 241, 0.92);
  font-size: 22rpx;
  letter-spacing: 0.4rpx;
}

.brand-entry {
  padding: 8rpx 18rpx;
  border-radius: 999rpx;
  background: rgba(255, 255, 255, 0.16);
  color: #fff;
  font-size: 22rpx;
  border: 1rpx solid rgba(255, 255, 255, 0.32);
  backdrop-filter: blur(6rpx);
  box-shadow: inset 0 1rpx 0 rgba(255, 255, 255, 0.18);
}

.search-row {
  display: flex;
  align-items: center;
  gap: 10rpx;
  min-height: 72rpx;
  border-radius: 999rpx;
  background: rgba(255, 255, 255, 0.92);
  padding: 8rpx 10rpx 8rpx 16rpx;
  border: 1rpx solid rgba(255, 255, 255, 0.48);
  box-shadow:
    0 10rpx 20rpx rgba(123, 79, 41, 0.08),
    inset 0 1rpx 0 rgba(255, 255, 255, 0.66);
}

.search-icon {
  color: #b9b0a8;
  font-size: 24rpx;
}

.search-placeholder {
  flex: 1;
  color: #988678;
  font-size: 24rpx;
  letter-spacing: 0.3rpx;
}

.search-btn {
  height: 54rpx;
  display: inline-flex;
  align-items: center;
  border-radius: 999rpx;
  padding: 0 22rpx;
  color: #fff;
  background: linear-gradient(135deg, #ca8d55, #bf7840);
  font-size: 22rpx;
  font-weight: 700;
  box-shadow: 0 8rpx 16rpx rgba(172, 103, 39, 0.16);
}

.hero-swiper {
  padding: 0;
  overflow: hidden;
  background: #fff;
  border: 1rpx solid rgba(193, 159, 120, 0.18);
  border-radius: 20rpx;
}

.hero-swiper-inner {
  height: 244rpx;
}

.hero-slide {
  height: 100%;
  padding: 24rpx;
  background: radial-gradient(circle at 88% 10%, rgba(213, 176, 141, 0.22), transparent 38%), #fff;
  box-sizing: border-box;
}

.hero-top {
  align-items: flex-start;
}

.hero-kicker {
  font-size: 20rpx;
  color: #8e6847;
  letter-spacing: 0.4rpx;
}

.hero-title {
  margin-top: 6rpx;
  font-size: 36rpx;
  line-height: 1.2;
  font-weight: 800;
  letter-spacing: 0.6rpx;
  color: #4f321b;
}

.hero-subtitle {
  margin-top: 8rpx;
  font-size: 22rpx;
  color: #7e654e;
}

.hero-tag {
  min-width: 58rpx;
  height: 58rpx;
  border-radius: 16rpx;
  padding: 0 10rpx;
  background: #bf8650;
  color: #fff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 22rpx;
  font-weight: 700;
  box-shadow: 0 8rpx 16rpx rgba(132, 88, 50, 0.22);
}

.hero-point {
  margin-top: 16rpx;
  display: inline-block;
  padding: 8rpx 14rpx;
  border-radius: 999rpx;
  font-size: 20rpx;
  color: #6a4a2f;
  background: #fbf3ea;
  border: 1rpx solid rgba(191, 145, 97, 0.2);
}

.recommend {
  margin-bottom: 20rpx;
}

.recommend-head {
  align-items: flex-end;
  margin-bottom: 14rpx;
}

.no-margin {
  margin-bottom: 0;
}

.recommend-subtitle {
  margin-top: 6rpx;
  font-size: 22rpx;
  color: #8a745f;
}

.recommend-count {
  padding: 8rpx 14rpx;
  border-radius: 999rpx;
  background: rgba(190, 133, 78, 0.12);
  color: #9a6333;
  font-size: 22rpx;
  font-weight: 700;
}

.recommend-state {
  margin-top: 14rpx;
  text-align: center;
  color: #6f655b;
}

.retry-btn {
  width: 180rpx;
}

.waterfall-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18rpx;
}

.waterfall-card {
  overflow: hidden;
  border-radius: 24rpx;
  background: rgba(255, 255, 255, 0.96);
  border: 1rpx solid rgba(198, 161, 124, 0.14);
  box-shadow: 0 14rpx 28rpx rgba(146, 103, 63, 0.08);
}

.waterfall-cover {
  width: 100%;
  height: 260rpx;
  display: block;
  background: #f4eadf;
}

.waterfall-cover-fallback {
  background: linear-gradient(135deg, #f1dec9, #e7c8a4 46%, #d8af83);
}

.waterfall-body {
  padding: 16rpx 16rpx 18rpx;
}

.waterfall-badge-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8rpx;
}

.waterfall-badge,
.waterfall-tip {
  display: inline-flex;
  align-items: center;
  height: 38rpx;
  padding: 0 12rpx;
  border-radius: 999rpx;
  font-size: 20rpx;
}

.waterfall-badge {
  color: #9a6333;
  background: rgba(190, 133, 78, 0.12);
}

.waterfall-tip {
  color: #fffaf4;
  background: #bd7d44;
}

.waterfall-title {
  margin-top: 12rpx;
  min-height: 76rpx;
  font-size: 28rpx;
  line-height: 1.35;
  font-weight: 700;
  color: #4f321b;
}

.waterfall-desc {
  margin-top: 8rpx;
  min-height: 64rpx;
  font-size: 22rpx;
  line-height: 1.45;
  color: #856a53;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.waterfall-price-row {
  margin-top: 14rpx;
}

.interactive {
  transition: transform 180ms ease, opacity 180ms ease;
}

.interactive:active {
  transform: scale(0.98);
  opacity: 0.92;
}
</style>
