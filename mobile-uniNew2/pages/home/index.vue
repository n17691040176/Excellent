<template>
  <view class="home-page">
    <view class="hero-shell">
      <view class="search-row interactive" @click="go('/pages/packages/list', true, 'search_bar')">
        <view class="search-icon">搜</view>
        <view class="search-placeholder">{{ activeSearchPlaceholder }}</view>
        <view class="search-btn">搜索</view>
      </view>
    </view>

    <view class="hero-swiper">
      <swiper
        class="hero-swiper-inner"
        circular
        autoplay
        interval="3200"
        duration="360"
        indicator-dots
        indicator-color="rgba(255,122,0,0.18)"
        indicator-active-color="#ff6a00"
      >
        <swiper-item v-for="slide in heroSlides" :key="slide.key">
          <view class="hero-slide interactive" @click="go(slide.path, slide.isTab, slide.key)">
            <view class="hero-slide-badge">{{ slide.tag }}</view>
            <view class="hero-slide-title">{{ slide.title }}</view>
            <view class="hero-slide-desc">{{ slide.desc }}</view>
            <view class="hero-slide-foot">
              <view class="hero-slide-dot" />
              <view class="hero-slide-foot-text">{{ slide.foot }}</view>
            </view>
          </view>
        </swiper-item>
      </swiper>
    </view>

    <view class="waterfall-section">
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
          <view class="waterfall-thumb-wrap">
            <image v-if="item.image" class="waterfall-cover" :src="item.image" mode="aspectFill" lazy-load />
            <view v-else class="waterfall-cover waterfall-cover-fallback" />
            <view class="waterfall-chip">{{ item.badge }}</view>
            <view v-if="item.tip" class="waterfall-tip">{{ item.tip }}</view>
          </view>

          <view class="waterfall-body">
            <view class="waterfall-title">{{ item.title }}</view>
            <view class="waterfall-desc">{{ item.desc }}</view>
            <view class="waterfall-price-row">
              <view class="ecom-price">
                <text class="ecom-price-main">¥{{ item.price }}</text>
                <text v-if="item.marketPrice" class="ecom-price-origin">¥{{ item.marketPrice }}</text>
              </view>
              <view class="waterfall-buy">立即抢购</view>
            </view>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue';
import { onHide, onPullDownRefresh, onShow } from '@dcloudio/uni-app';
import { packageApi } from '@/api/modules';
import { getApiBaseUrl } from '@/config/index';
import { trackEvent, trackPageView } from '@/utils/track';

const LEGACY_FILE_BASE_URL = 'https://file.hoh516.com/huohonghuo';

const heroSlides = [
  {
    key: 'mall',
    title: '精选商城',
    desc: '严选爆款，限时热卖更划算',
    foot: '热卖补贴专区',
    tag: '热卖',
    path: '/pages/packages/list',
    isTab: true
  },
  {
    key: 'quality',
    title: '品质好物',
    desc: '高复购商品，适合日用与礼赠',
    foot: '品质推荐更新',
    tag: '推荐',
    path: '/pages/packages/list',
    isTab: true
  },
  {
    key: 'service',
    title: '本地生活',
    desc: '附近服务直达，预约更快捷',
    foot: '同城服务上新',
    tag: '附近',
    path: '/pages/local-life/index',
    isTab: true
  }
];

const searchPlaceholders = ['搜智能手表', '搜共享设备', '搜海鲜礼盒', '搜品质好物'];

const loading = ref(false);
const failed = ref(false);
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

// 页面正常随滚动，不再对首页顶部区域做吸顶处理。

onPullDownRefresh(async () => {
  await loadRecommend();
  uni.stopPullDownRefresh();
});
</script>

<style scoped>
@import '@/styles/common.css';

.home-page {
  padding: 18rpx 18rpx 28rpx;
  box-sizing: border-box;
}

.hero-shell {
  padding: 16rpx 18rpx;
  border-radius: 30rpx;
  background: linear-gradient(135deg, #ffb15f 0%, #ff8a2a 42%, #ff6a00 100%);
  box-shadow: 0 18rpx 34rpx rgba(205, 96, 31, 0.22);
}

.search-row {
  display: flex;
  align-items: center;
  gap: 10rpx;
  min-height: 76rpx;
  border-radius: 999rpx;
  background: rgba(255, 255, 255, 0.96);
  padding: 8rpx 10rpx 8rpx 16rpx;
  border: 1rpx solid rgba(255, 255, 255, 0.65);
  box-shadow: 0 10rpx 20rpx rgba(179, 72, 17, 0.14);
}

.search-icon {
  width: 44rpx;
  height: 44rpx;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 22rpx;
  font-weight: 700;
  background: linear-gradient(135deg, #ff8a2a, #ff5f3d);
}

.search-placeholder {
  flex: 1;
  color: #8b6550;
  font-size: 24rpx;
}

.search-btn {
  height: 56rpx;
  display: inline-flex;
  align-items: center;
  border-radius: 999rpx;
  padding: 0 22rpx;
  color: #fff;
  background: linear-gradient(135deg, #ff7a00, #ff4f3a);
  font-size: 22rpx;
  font-weight: 700;
  box-shadow: 0 8rpx 16rpx rgba(255, 89, 44, 0.22);
}

.hero-swiper {
  margin-top: 14rpx;
  overflow: hidden;
  border-radius: 30rpx;
  background: linear-gradient(180deg, #fffaf4 0%, #fff2e8 100%);
  border: 1rpx solid rgba(255, 122, 0, 0.14);
}

.hero-swiper-inner {
  height: 256rpx;
}

.hero-slide {
  height: 100%;
  padding: 24rpx 22rpx;
  background:
    radial-gradient(circle at 92% 18%, rgba(255, 255, 255, 0.2), transparent 26%),
    linear-gradient(135deg, #fff7ef 0%, #ffe8d2 46%, #ffd2aa 100%);
  box-sizing: border-box;
}

.hero-slide-badge {
  display: inline-flex;
  align-items: center;
  height: 38rpx;
  padding: 0 14rpx;
  border-radius: 999rpx;
  background: rgba(255, 255, 255, 0.42);
  color: #ff6a00;
  font-size: 20rpx;
  font-weight: 700;
}

.hero-slide-title {
  margin-top: 12rpx;
  font-size: 40rpx;
  line-height: 1.18;
  font-weight: 900;
  color: #4a2410;
}

.hero-slide-desc {
  margin-top: 10rpx;
  font-size: 24rpx;
  line-height: 1.45;
  color: #7f5a44;
  max-width: 420rpx;
}

.hero-slide-foot {
  margin-top: 20rpx;
  display: inline-flex;
  align-items: center;
  gap: 10rpx;
  padding: 10rpx 14rpx;
  border-radius: 999rpx;
  background: rgba(255, 255, 255, 0.55);
}

.hero-slide-dot {
  width: 10rpx;
  height: 10rpx;
  border-radius: 50%;
  background: #ff6a00;
}

.hero-slide-foot-text {
  font-size: 20rpx;
  color: #8b5d3a;
  font-weight: 700;
}

.waterfall-section {
  margin-top: 22rpx;
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
  gap: 16rpx;
}

.waterfall-card {
  overflow: hidden;
  border-radius: 28rpx;
  background: #fff;
  border: 1rpx solid rgba(255, 122, 0, 0.14);
  box-shadow: 0 14rpx 28rpx rgba(255, 96, 34, 0.08);
}

.waterfall-thumb-wrap {
  position: relative;
}

.waterfall-cover {
  width: 100%;
  height: 244rpx;
  display: block;
  background: #fff0df;
}

.waterfall-cover-fallback {
  background: linear-gradient(135deg, #ffcf9c, #ff9f5e 46%, #ff7a00);
}

.waterfall-chip {
  position: absolute;
  left: 14rpx;
  top: 14rpx;
  display: inline-flex;
  align-items: center;
  height: 34rpx;
  padding: 0 12rpx;
  border-radius: 999rpx;
  background: rgba(255, 255, 255, 0.9);
  color: #ff6a00;
  font-size: 18rpx;
  font-weight: 700;
}

.waterfall-tip {
  position: absolute;
  right: 14rpx;
  top: 14rpx;
  display: inline-flex;
  align-items: center;
  height: 34rpx;
  padding: 0 12rpx;
  border-radius: 999rpx;
  color: #fff;
  background: linear-gradient(135deg, #ff7a00, #ff4f3a);
  font-size: 18rpx;
  font-weight: 700;
}

.waterfall-body {
  padding: 14rpx 14rpx 16rpx;
}

.waterfall-title {
  min-height: 70rpx;
  font-size: 28rpx;
  line-height: 1.35;
  font-weight: 800;
  color: #4a2410;
}

.waterfall-desc {
  margin-top: 8rpx;
  font-size: 22rpx;
  color: #8a6a57;
  line-height: 1.45;
  min-height: 62rpx;
}

.waterfall-price-row {
  margin-top: 12rpx;
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12rpx;
}

.waterfall-buy {
  flex-shrink: 0;
  padding: 10rpx 16rpx;
  border-radius: 999rpx;
  background: linear-gradient(135deg, #ff7a00, #ff5f3d);
  color: #fff;
  font-size: 20rpx;
  font-weight: 700;
}

.interactive {
  transition: transform 180ms ease, opacity 180ms ease;
}

.interactive:active {
  transform: scale(0.98);
  opacity: 0.92;
}
</style>
