<template>
  <view class="life-page">
    <!-- Hero Zone -->
    <view class="hero-zone">
      <view class="hero-header">
        <view class="hero-icon">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none">
            <path d="M12 2L2 7L12 12L22 7L12 2Z" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
            <path d="M2 17L12 22L22 17" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
            <path d="M2 12L12 17L22 12" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
          </svg>
        </view>
        <view class="hero-text">
          <text class="hero-title">本地生活</text>
          <text class="hero-sub">发现身边服务</text>
        </view>
      </view>
      <view class="hero-badges">
        <view class="badge-item">新人专享</view>
        <view class="badge-divider" />
        <view class="badge-item">极速响应</view>
        <view class="badge-divider" />
        <view class="badge-item">品质保障</view>
      </view>
    </view>

    <!-- Quick Entries -->
    <view class="quick-section">
      <view class="quick-grid">
        <view
          v-for="item in quickEntries"
          :key="item.label"
          class="quick-item"
          @click="go(item.path)"
        >
          <view class="quick-icon" :style="{ background: item.bg }">
            <svg width="36" height="36" viewBox="0 0 24 24" fill="none" v-html="item.svgPath" />
          </view>
          <text class="quick-label">{{ item.label }}</text>
        </view>
      </view>
    </view>

    <!-- Service Scenes -->
    <view class="scene-section">
      <view class="section-header">
        <text class="section-title">热门场景</text>
      </view>
      <view class="scene-grid">
        <view
          v-for="scene in scenes"
          :key="scene.title"
          class="scene-card"
          @click="go(scene.path)"
        >
          <view class="scene-icon" :style="{ background: scene.bg }">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" v-html="scene.svgPath" />
          </view>
          <view class="scene-info">
            <text class="scene-title">{{ scene.title }}</text>
          </view>
          <svg class="scene-arrow" width="20" height="20" viewBox="0 0 24 24" fill="none">
            <path d="M9 18L15 12L9 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </view>
      </view>
    </view>

    <!-- Services List -->
    <view class="service-section">
      <view class="section-header">
        <text class="section-title">精选服务</text>
        <view class="section-more" @click="goAll">
          <text>查看全部</text>
          <svg class="arrow-icon" width="16" height="16" viewBox="0 0 24 24" fill="none">
            <path d="M9 18L15 12L9 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </view>
      </view>

      <view v-if="loading" class="service-list">
        <view v-for="i in 3" :key="i" class="service-card">
          <view class="skeleton service-img" />
          <view class="skeleton service-title" />
        </view>
      </view>

      <view v-else-if="failed" class="error-state">
        <svg class="error-icon" width="80" height="80" viewBox="0 0 24 24" fill="none">
          <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/>
          <path d="M12 8V12M12 16H12.01" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        </svg>
        <text class="error-text">服务加载失败</text>
        <view class="retry-btn" @click="fetchServices">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
            <path d="M1 4V10H7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M3.51 15C4.15839 16.8404 5.38734 18.4202 7.01166 19.5014C8.63598 20.5826 10.5677 21.1066 12.5157 20.9945C14.4637 20.8824 16.3226 20.1397 17.8121 18.8798C19.3016 17.6198 20.3413 15.9089 20.7741 14.0064C21.2068 12.1039 21.0107 10.1157 20.2127 8.33153C19.4148 6.54734 18.0551 5.06235 16.3288 4.10187C14.6025 3.14139 12.6009 2.75431 10.6223 3.00104C8.64365 3.24778 6.79194 4.11503 5.34 5.47" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          点击重试
        </view>
      </view>

      <view v-else-if="!services.length" class="empty-state">
        <svg class="empty-icon" width="100" height="100" viewBox="0 0 24 24" fill="none">
          <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="1.5"/>
          <path d="M8 15C8.5 16.5 9.5 18 12 18C14.5 18 15.5 16.5 16 15" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
          <circle cx="9" cy="9" r="1.5" fill="currentColor"/>
          <circle cx="15" cy="9" r="1.5" fill="currentColor"/>
        </svg>
        <text class="empty-text">暂无服务</text>
      </view>

      <view v-else class="service-list">
        <view
          v-for="item in services"
          :key="item.id"
          class="service-card"
          @click="go(`/subpackages/life/service-detail?id=${item.id}`)"
        >
          <view class="service-image-wrap">
            <image
              v-if="item.image"
              class="service-image"
              :src="item.image"
              mode="aspectFill"
            />
            <view v-else class="service-placeholder">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none">
                <rect x="3" y="3" width="18" height="18" rx="2" stroke="currentColor" stroke-width="1.5" opacity="0.3"/>
                <circle cx="8.5" cy="8.5" r="1.5" fill="currentColor" opacity="0.3"/>
                <path d="M21 15L16 10.5V10C16 8.89543 15.1046 8 14 8H10C8.89543 8 8 8.89543 8 10V10.5L3 15" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" opacity="0.3"/>
              </svg>
            </view>
            <view class="service-tag">{{ item.tag }}</view>
          </view>
          <view class="service-info">
            <text class="service-title">{{ item.title }}</text>
            <view class="service-footer">
              <view class="service-price">
                <text class="price-symbol">¥</text>
                <text class="price-value">{{ item.price }}</text>
                <text class="price-original">¥{{ item.originalPrice }}</text>
              </view>
              <view class="service-btn">预约</view>
            </view>
          </view>
        </view>
      </view>
    </view>

    <view class="bottom-space" />
  </view>
</template>

<script setup>
import { onMounted, ref } from 'vue';
import { onPullDownRefresh, onReachBottom } from '@dcloudio/uni-app';
import { localLifeApi } from '@/api/modules';
import { trackEvent, trackPageView } from '@/utils/track';

const loading = ref(false);
const failed = ref(false);
const page = ref(1);
const services = ref([]);

const quickEntries = [
  {
    label: '到店',
    bg: 'linear-gradient(135deg, #10B981 0%, #059669 100%)',
    path: '/subpackages/life/index',
    svgPath: '<path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 3c1.66 0 3 1.34 3 3s-1.34 3-3 3-3-1.34-3-3 1.34-3 3-3zm0 14.2c-2.5 0-4.71-1.28-6-3.22.03-1.99 4-3.08 6-3.08 1.99 0 5.97 1.09 6 3.08-1.29 1.94-3.5 3.22-6 3.22z" fill="white"/>'
  },
  {
    label: '上门',
    bg: 'linear-gradient(135deg, #0EA5E9 0%, #0284C7 100%)',
    path: '/subpackages/life/index',
    svgPath: '<path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" stroke="white" stroke-width="2" stroke-linejoin="round"/><path d="M9 22V12h6v10" stroke="white" stroke-width="2" stroke-linejoin="round"/>'
  },
  {
    label: '急速',
    bg: 'linear-gradient(135deg, #F97316 0%, #EA580C 100%)',
    path: '/subpackages/life/index',
    svgPath: '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
  },
  {
    label: '热榜',
    bg: 'linear-gradient(135deg, #6366F1 0%, #4F46E5 100%)',
    path: '/subpackages/life/index',
    svgPath: '<path d="M8.5 14.5A2.5 2.5 0 0011 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 11-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 002.5 2.5z" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
  }
];

const scenes = [
  {
    icon: '◈',
    title: '保洁服务',
    bg: 'linear-gradient(135deg, #10B981 0%, #059669 100%)',
    path: '/subpackages/life/index',
    svgPath: '<path d="M12 2L2 7V17L12 22L22 17V7L12 2Z" stroke="white" stroke-width="2" stroke-linejoin="round"/><path d="M12 22V12M2 7L22 17M22 7L2 17" stroke="white" stroke-width="2" stroke-linejoin="round"/>'
  },
  {
    icon: '○',
    title: '维修安装',
    bg: 'linear-gradient(135deg, #0EA5E9 0%, #0284C7 100%)',
    path: '/subpackages/life/index',
    svgPath: '<path d="M14.7 6.3a1 1 0 000 1.4l1.6 1.6a1 1 0 001.4 0l3.77-3.77a6 6 0 01-7.94 7.94l-6.91 6.91a2.12 2.12 0 01-3-3l6.91-6.91a6 6 0 017.94-7.94l-3.76 3.76z" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
  },
  {
    icon: '◻',
    title: '汽车服务',
    bg: 'linear-gradient(135deg, #F97316 0%, #EA580C 100%)',
    path: '/subpackages/life/index',
    svgPath: '<path d="M19 17h2c.6 0 1-.4 1-1v-3c0-.9-.7-1.7-1.5-1.9C18.7 10.6 16 10 16 10s-1.3-1.4-2.2-2.3c-.5-.4-1.1-.7-1.8-.7H5c-.6 0-1.1.4-1.4.9l-1.5 2.8c-.1.2-.1.4-.1.6v4.7c0 .6.4 1 1 1h1" stroke="white" stroke-width="2" stroke-linecap="round"/><circle cx="6.5" cy="17.5" r="2.5" stroke="white" stroke-width="2"/><circle cx="16.5" cy="17.5" r="2.5" stroke="white" stroke-width="2"/>'
  },
  {
    icon: '⊞',
    title: '美容美体',
    bg: 'linear-gradient(135deg, #6366F1 0%, #4F46E5 100%)',
    path: '/subpackages/life/index',
    svgPath: '<circle cx="12" cy="12" r="3" stroke="white" stroke-width="2"/><path d="M12 1v4M12 19v4M4.22 4.22l2.83 2.83M16.95 16.95l2.83 2.83M1 12h4M19 12h4M4.22 19.78l2.83-2.83M16.95 7.05l2.83-2.83" stroke="white" stroke-width="2" stroke-linecap="round"/>'
  }
];

const normalizeRows = (res) => {
  const rows = Array.isArray(res) ? res : res?.items || res?.list || [];
  return rows.map((item, idx) => {
    const price = Number(item.price ?? item.sale_price ?? 0);
    const originalPrice = price + 38;
    return {
      id: item.id || `s-${idx}`,
      title: item.name || item.title || '未命名服务',
      price: price.toFixed(2),
      originalPrice: originalPrice.toFixed(2),
      tag: item.tag || '热门',
      image: ''
    };
  });
};

const fetchServices = async (reset = true) => {
  loading.value = true;
  failed.value = false;
  try {
    const currentPage = reset ? 1 : page.value;
    const res = await localLifeApi.services({ page: currentPage, page_size: 10 });
    const rows = normalizeRows(res);
    services.value = reset ? rows : [...services.value, ...rows];
    page.value = currentPage + 1;
  } catch (error) {
    failed.value = true;
  } finally {
    loading.value = false;
  }
};

const go = (path) => {
  trackEvent('local_life_click', { path });
  uni.navigateTo({ url: path });
};

const goAll = () => {
  trackEvent('local_life_view_all');
  uni.navigateTo({ url: '/subpackages/life/index' });
};

onMounted(() => {
  trackPageView('local_life_home');
  fetchServices(true);
});

onPullDownRefresh(async () => {
  await fetchServices(true);
  uni.stopPullDownRefresh();
});

onReachBottom(() => {
  trackEvent('local_life_load_more', { page: page.value });
  fetchServices(false);
});
</script>

<style scoped>
@import '@/styles/common.css';

.life-page {
  min-height: 100vh;
  background: var(--bg);
  padding-bottom: calc(env(safe-area-inset-bottom) + 140rpx);
}

/* ===== Hero Zone ===== */
.hero-zone {
  position: relative;
  padding: 40rpx 32rpx;
  padding-top: calc(40rpx + env(safe-area-inset-top));
  background: linear-gradient(135deg, #10B981 0%, #059669 100%);
  overflow: hidden;
}

/* 装饰圆形 */
.hero-zone::before,
.hero-zone::after {
  content: '';
  position: absolute;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.1);
}
.hero-zone::before {
  width: 320rpx;
  height: 320rpx;
  right: -80rpx;
  top: -120rpx;
}
.hero-zone::after {
  width: 200rpx;
  height: 200rpx;
  left: -60rpx;
  bottom: -60rpx;
}

.hero-header {
  position: relative;
  display: flex;
  align-items: center;
  gap: 24rpx;
  margin-bottom: 28rpx;
}

.hero-icon {
  width: 88rpx;
  height: 88rpx;
  background: rgba(255, 255, 255, 0.25);
  border-radius: 22rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  box-shadow: 0 8rpx 20rpx rgba(0, 0, 0, 0.15);
}

.hero-text {
  display: flex;
  flex-direction: column;
  gap: 6rpx;
}

.hero-title {
  font-size: 44rpx;
  font-weight: 800;
  color: white;
  letter-spacing: 1rpx;
}

.hero-sub {
  font-size: 26rpx;
  color: rgba(255, 255, 255, 0.85);
}

.hero-badges {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 24rpx;
  padding: 24rpx;
  background: rgba(255, 255, 255, 0.18);
  border-radius: var(--radius-lg);
  backdrop-filter: blur(10px);
}

.badge-item {
  font-size: 24rpx;
  font-weight: 600;
  color: white;
}

.badge-divider {
  width: 1rpx;
  height: 24rpx;
  background: rgba(255, 255, 255, 0.3);
}

/* ===== Quick Section ===== */
.quick-section {
  margin: -24rpx 32rpx 0;
}

.quick-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20rpx;
  background: var(--card);
  border-radius: var(--radius-xl);
  padding: 36rpx 28rpx;
  box-shadow: var(--shadow-md);
}

.quick-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14rpx;
}

.quick-icon {
  width: 96rpx;
  height: 96rpx;
  border-radius: var(--radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: var(--shadow-sm);
}

.quick-label {
  font-size: 26rpx;
  font-weight: 600;
  color: var(--text-secondary);
}

/* ===== Scene Section ===== */
.scene-section {
  padding: 48rpx 32rpx 0;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24rpx;
}

.section-title {
  font-size: 32rpx;
  font-weight: 700;
  color: var(--text);
}

.section-more {
  display: flex;
  align-items: center;
  font-size: 24rpx;
  color: var(--text-muted);
}

.arrow-icon {
  margin-left: 4rpx;
}

.scene-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16rpx;
}

.scene-card {
  display: flex;
  align-items: center;
  gap: 20rpx;
  padding: 28rpx;
  background: var(--card);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow);
  transition: all var(--duration-fast) var(--ease-out);
}

.scene-card:active {
  opacity: 0.85;
  transform: scale(0.97);
  box-shadow: var(--shadow-sm);
}

.scene-icon {
  width: 80rpx;
  height: 80rpx;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: var(--shadow-sm);
}

.scene-info {
  flex: 1;
}

.scene-title {
  font-size: 28rpx;
  font-weight: 600;
  color: var(--text);
}

.scene-arrow {
  color: var(--text-muted);
  flex-shrink: 0;
}

/* ===== Service Section ===== */
.service-section {
  padding: 48rpx 32rpx 0;
}

.service-list {
  display: flex;
  flex-direction: column;
  gap: 24rpx;
}

.service-card {
  background: var(--card);
  border-radius: var(--radius-xl);
  overflow: hidden;
  box-shadow: var(--shadow);
  transition: all var(--duration-normal) var(--ease-out);
}

.service-card:active {
  opacity: 0.9;
  transform: scale(0.98);
  box-shadow: var(--shadow-sm);
}

.service-image-wrap {
  position: relative;
  width: 100%;
  height: 300rpx;
}

.service-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.service-placeholder {
  width: 100%;
  height: 100%;
  background: linear-gradient(135deg, #E2E8F0 0%, #CBD5E1 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
}

.service-tag {
  position: absolute;
  left: 16rpx;
  top: 16rpx;
  padding: 10rpx 24rpx;
  background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
  color: white;
  font-size: 22rpx;
  font-weight: 700;
  border-radius: 24rpx;
  box-shadow: var(--shadow-primary);
}

.service-info {
  padding: 28rpx;
}

.service-title {
  display: block;
  font-size: 32rpx;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 20rpx;
  line-height: 1.4;
}

.service-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.service-price {
  display: flex;
  align-items: baseline;
  gap: 4rpx;
}

.price-symbol {
  font-size: 24rpx;
  font-weight: 600;
  color: var(--secondary);
}

.price-value {
  font-size: 36rpx;
  font-weight: 800;
  color: var(--secondary);
}

.price-original {
  font-size: 22rpx;
  color: var(--text-muted);
  text-decoration: line-through;
  margin-left: 8rpx;
}

.service-btn {
  padding: 16rpx 36rpx;
  background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
  color: white;
  font-size: 26rpx;
  font-weight: 600;
  border-radius: var(--radius-full);
  box-shadow: var(--shadow-primary);
  transition: all var(--duration-fast) var(--ease-out);
}

.service-btn:active {
  transform: scale(0.95);
  box-shadow: var(--shadow-sm);
}
  border-radius: 40rpx;
  transition: all var(--duration-fast) var(--ease-out);
}

.service-btn:active {
  transform: scale(0.95);
}

/* ===== States ===== */
.skeleton.service-img {
  width: 100%;
  height: 280rpx;
}

.skeleton.service-title {
  height: 40rpx;
  margin: 24rpx;
  width: 60%;
}

.empty-state,
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 64rpx;
  background: var(--card);
  border-radius: var(--radius-lg);
}

.empty-icon {
  color: var(--text-muted);
  margin-bottom: 16rpx;
}

.error-icon {
  color: var(--error);
  margin-bottom: 16rpx;
}

.empty-text,
.error-text {
  font-size: 28rpx;
  color: var(--text-muted);
  margin-bottom: 24rpx;
}

.retry-btn {
  display: flex;
  align-items: center;
  gap: 8rpx;
  padding: 16rpx 40rpx;
  background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
  color: white;
  font-size: 26rpx;
  font-weight: 600;
  border-radius: 40rpx;
  transition: all var(--duration-fast) var(--ease-out);
}

.retry-btn:active {
  transform: scale(0.95);
}

/* Bottom Space */
.bottom-space {
  height: 64rpx;
}

/* ===== Reduced Motion ===== */
@media (prefers-reduced-motion: reduce) {
  .scene-card,
  .service-card,
  .service-btn,
  .retry-btn {
    transition: none;
  }

  .scene-card:active,
  .service-card:active,
  .service-btn:active,
  .retry-btn:active {
    transform: none;
  }
}
</style>