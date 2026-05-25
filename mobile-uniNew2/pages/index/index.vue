<template>
  <view class="entry-page">
    <view class="hero-card card">
      <view class="hero-top">
        <view class="hero-copy">
          <view class="hero-tag">Welcome</view>
          <view class="hero-title">Excellent Mall</view>
          <view class="hero-desc">商城、同城服务、个人中心统一沉淀为一套更有质感的移动端体验。</view>
        </view>
        <view class="hero-mark">E</view>
      </view>

      <view class="hero-banner mt-20">
        <view class="banner-title">红橙电商风</view>
        <view class="banner-subtitle">更像成熟业务，而不是默认模板</view>
      </view>

      <view class="entry-actions mt-24">
        <button class="btn btn-primary" @click="go('/pages/login/index')">进入登录</button>
        <button class="btn btn-ghost" @click="go('/pages/home/index')">查看首页</button>
      </view>
    </view>

    <view class="card mt-24 feature-card">
      <view class="section-title">当前能力</view>
      <view class="feature-list">
        <view class="feature-item">首页已按电商主视觉重新设计</view>
        <view class="feature-item">个人中心、登录、本地生活已同步统一风格</view>
        <view class="feature-item">继续可以逐页深改套餐、详情、邀请、佣金等高频页面</view>
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
  padding: 24rpx 24rpx 44rpx;
}

.hero-card {
  background:
    radial-gradient(circle at 92% 8%, rgba(255, 190, 146, 0.18), transparent 34%),
    linear-gradient(180deg, #fffdf9 0%, #fff6ec 100%);
}

.hero-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 18rpx;
}

.hero-tag {
  display: inline-flex;
  align-items: center;
  padding: 6rpx 14rpx;
  border-radius: 999rpx;
  background: rgba(255, 138, 43, 0.12);
  color: #ff6a00;
  font-size: 20rpx;
  font-weight: 800;
}

.hero-title {
  margin-top: 10rpx;
  font-size: 44rpx;
  line-height: 1.2;
  font-weight: 900;
  color: #4a2b13;
}

.hero-desc {
  margin-top: 10rpx;
  font-size: 24rpx;
  line-height: 1.65;
  color: #836a52;
}

.hero-mark {
  width: 96rpx;
  height: 96rpx;
  border-radius: 28rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #ff7a00, #ff4f3a);
  color: #fff;
  font-size: 40rpx;
  font-weight: 900;
  box-shadow: 0 16rpx 26rpx rgba(255, 89, 44, 0.18);
}

.hero-banner {
  border-radius: 24rpx;
  padding: 18rpx 20rpx;
  background: linear-gradient(135deg, #ff7a00, #ff5f3d);
  color: #fff;
}

.banner-title {
  font-size: 28rpx;
  font-weight: 800;
}

.banner-subtitle {
  margin-top: 6rpx;
  font-size: 21rpx;
  opacity: 0.92;
}

.entry-actions {
  display: grid;
  gap: 14rpx;
}

.feature-card {
  border-radius: 28rpx;
}

.feature-list {
  display: grid;
  gap: 14rpx;
}

.feature-item {
  border-radius: 18rpx;
  padding: 18rpx;
  background: #fff5ec;
  color: #6f5438;
  font-size: 24rpx;
  line-height: 1.55;
  border: 1rpx solid rgba(194, 157, 118, 0.16);
}
</style>
