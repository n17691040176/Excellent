<template>
  <view class="entry-page">
    <!-- Hero Card -->
    <view class="hero-card">
      <view class="hero-top">
        <view class="hero-copy">
          <view class="hero-tag">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
              <path d="M12 2L2 7V17L12 22L22 17V7L12 2Z" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
              <path d="M12 22V12M2 7L22 17M22 7L2 17" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
            </svg>
            Welcome
          </view>
          <text class="hero-title">林间商城</text>
          <text class="hero-desc">商城、同城服务、个人中心统一沉淀为一套更有质感的移动端体验。</text>
        </view>
        <view class="hero-mark">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none">
            <path d="M12 2L2 7V17L12 22L22 17V7L12 2Z" stroke="white" stroke-width="2" stroke-linejoin="round"/>
            <path d="M12 22V12M2 7L22 17M22 7L2 17" stroke="white" stroke-width="2" stroke-linejoin="round"/>
          </svg>
        </view>
      </view>

      <view class="hero-banner">
        <view class="banner-icon">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
            <path d="M12 3L2 8V12L12 22L22 12V8L12 3Z" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
          </svg>
        </view>
        <view class="banner-text">
          <text class="banner-title">清新绿色风</text>
          <text class="banner-subtitle">更像成熟业务，而不是默认模板</text>
        </view>
      </view>

      <view class="entry-actions">
        <button class="btn btn-primary" @click="go('/pages/login/index')">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
            <path d="M20 21V19C20 17.9391 19.5786 16.9217 18.8284 16.1716C18.0783 15.4214 17.0609 15 16 15H8C6.93913 15 5.92172 15.4214 5.17157 16.1716C4.42143 16.9217 4 17.9391 4 19V21" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            <circle cx="12" cy="7" r="4" stroke="currentColor" stroke-width="2"/>
          </svg>
          进入登录
        </button>
        <button class="btn btn-ghost" @click="go('/pages/home/index')">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
            <path d="M3 9L12 2L21 9V20C21 20.5304 20.7893 21.0391 20.4142 21.4142C20.0391 21.7893 19.5304 22 19 22H5C4.46957 22 3.96086 21.7893 3.58579 21.4142C3.21071 21.0391 3 20.5304 3 20V9Z" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
            <path d="M9 22V12H15V22" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
          </svg>
          查看首页
        </button>
      </view>
    </view>

    <!-- Feature Card -->
    <view class="feature-card">
      <view class="section-header">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
          <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        <text class="section-title">当前能力</text>
      </view>
      <view class="feature-list">
        <view class="feature-item">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
            <path d="M20 6L9 17L4 12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          首页已采用绿色清新主题重新设计
        </view>
        <view class="feature-item">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
            <path d="M20 6L9 17L4 12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          个人中心、登录、本地生活、分类页已同步统一风格
        </view>
        <view class="feature-item">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
            <path d="M20 6L9 17L4 12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          继续可以逐页深改套餐、详情、邀请、佣金等高频页面
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
const go = (path) => {
  if (path === '/pages/home/index') {
    uni.switchTab({ url: path });
    return;
  }
  uni.navigateTo({ url: path });
};
</script>

<style scoped>
@import '@/styles/common.css';

.entry-page {
  min-height: 100vh;
  background: var(--bg);
  padding: 32rpx;
  padding-bottom: calc(env(safe-area-inset-bottom) + 120rpx);
}

/* ===== Hero Card ===== */
.hero-card {
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.08) 0%, rgba(16, 185, 129, 0.04) 100%);
  border: 1rpx solid rgba(16, 185, 129, 0.15);
  border-radius: var(--radius-xl);
  padding: 40rpx;
}

.hero-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 24rpx;
  margin-bottom: 32rpx;
}

.hero-copy {
  flex: 1;
}

.hero-tag {
  display: inline-flex;
  align-items: center;
  gap: 8rpx;
  padding: 8rpx 16rpx;
  background: rgba(5, 150, 105, 0.1);
  color: var(--primary);
  font-size: 20rpx;
  font-weight: var(--font-bold);
  border-radius: var(--radius-full);
  margin-bottom: 16rpx;
}

.hero-title {
  display: block;
  font-size: 44rpx;
  line-height: 1.2;
  font-weight: var(--font-black);
  color: var(--text);
  margin-bottom: 8rpx;
}

.hero-desc {
  display: block;
  font-size: 26rpx;
  line-height: 1.6;
  color: var(--text-muted);
}

.hero-mark {
  width: 96rpx;
  height: 96rpx;
  border-radius: var(--radius-xl);
  background: linear-gradient(135deg, var(--primary), var(--primary-dark));
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 16rpx 26rpx rgba(16, 185, 129, 0.2);
  flex-shrink: 0;
}

/* ===== Banner ===== */
.hero-banner {
  display: flex;
  align-items: center;
  gap: 16rpx;
  padding: 24rpx;
  background: linear-gradient(135deg, var(--primary), var(--primary-dark));
  border-radius: var(--radius-lg);
  margin-bottom: 32rpx;
}

.banner-icon {
  width: 56rpx;
  height: 56rpx;
  background: rgba(255, 255, 255, 0.2);
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  flex-shrink: 0;
}

.banner-text {
  display: flex;
  flex-direction: column;
  gap: 4rpx;
}

.banner-title {
  font-size: 28rpx;
  font-weight: var(--font-bold);
  color: white;
}

.banner-subtitle {
  font-size: 22rpx;
  color: rgba(255, 255, 255, 0.85);
}

/* ===== Buttons ===== */
.entry-actions {
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}

.btn {
  height: 96rpx;
  border-radius: var(--radius-full);
  font-size: 30rpx;
  font-weight: var(--font-semibold);
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12rpx;
  transition: all var(--duration-fast) var(--ease-out);
}

.btn:active {
  transform: scale(0.98);
}

.btn-primary {
  background: linear-gradient(135deg, var(--primary), var(--primary-dark));
  color: white;
  box-shadow: 0 12rpx 32rpx rgba(16, 185, 129, 0.25);
}

.btn-ghost {
  background: var(--card);
  color: var(--primary);
  border: 2rpx solid var(--primary);
}

/* ===== Feature Card ===== */
.feature-card {
  margin-top: 32rpx;
  background: var(--card);
  border-radius: var(--radius-xl);
  padding: 40rpx;
  box-shadow: var(--shadow-sm);
}

.section-header {
  display: flex;
  align-items: center;
  gap: 12rpx;
  color: var(--primary);
  margin-bottom: 24rpx;
}

.section-title {
  font-size: 32rpx;
  font-weight: var(--font-bold);
  color: var(--text);
}

.feature-list {
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}

.feature-item {
  display: flex;
  align-items: flex-start;
  gap: 12rpx;
  padding: 24rpx;
  background: rgba(5, 150, 105, 0.05);
  border-radius: var(--radius-md);
  border: 1rpx solid rgba(5, 150, 105, 0.1);
  font-size: 26rpx;
  line-height: 1.5;
  color: var(--text);
}

.feature-item svg {
  color: var(--primary);
  flex-shrink: 0;
  margin-top: 4rpx;
}

/* ===== Reduced Motion ===== */
@media (prefers-reduced-motion: reduce) {
  .btn {
    transition: none;
  }

  .btn:active {
    transform: none;
  }
}
</style>