<template>
  <view class="container entry-page">
    <view class="card hero-card">
      <view class="brand-mark">Excellent</view>
      <view class="hero-title mt-20">乐享好物，连接同城生活</view>
      <view class="hero-desc mt-16">商城套餐、本地服务、团队增长能力统一沉淀在同一套移动端体验里。</view>

      <view class="entry-actions mt-24">
        <button class="btn btn-primary" @click="go('/pages/login/index')">进入登录</button>
        <button class="btn btn-ghost" @click="go('/pages/home/index')">查看首页</button>
      </view>
    </view>

    <view class="card mt-24">
      <view class="section-title">当前能力</view>
      <view class="feature-list">
        <view class="feature-item">商城首页与套餐列表已统一为暖橙电商风格</view>
        <view class="feature-item">本地生活、订单、资产、佣金等页面文案已完成清理</view>
        <view class="feature-item">H5 构建已通过，可继续在 HBuilder 浏览器预览</view>
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
  padding-bottom: 36rpx;
}

.hero-card {
  background:
    radial-gradient(circle at 92% 8%, rgba(255, 173, 95, 0.22), transparent 34%),
    linear-gradient(180deg, #fffdf9 0%, #fff7ef 100%);
}

.brand-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 10rpx 18rpx;
  border-radius: 999rpx;
  background: rgba(255, 138, 43, 0.12);
  color: #d06400;
  font-size: 22rpx;
  font-weight: 800;
  letter-spacing: 0.6rpx;
}

.hero-title {
  font-size: 42rpx;
  line-height: 1.25;
  font-weight: 800;
  color: #4a2b13;
}

.hero-desc {
  font-size: 24rpx;
  line-height: 1.65;
  color: #836a52;
}

.entry-actions {
  display: grid;
  gap: 14rpx;
}

.feature-list {
  display: grid;
  gap: 14rpx;
}

.feature-item {
  border-radius: 16rpx;
  padding: 18rpx;
  background: #fbf4ec;
  color: #6f5438;
  font-size: 24rpx;
  line-height: 1.55;
  border: 1rpx solid rgba(194, 157, 118, 0.16);
}
</style>
