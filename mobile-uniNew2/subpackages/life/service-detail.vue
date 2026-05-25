<template>
  <view class="container service-detail-page">
    <view v-if="loading" class="card state-card">加载中...</view>
    <view v-else-if="failed" class="card state-card">
      <view>服务详情加载失败</view>
      <button class="btn btn-ghost retry-btn mt-16" @click="loadDetail">重试</button>
    </view>
    <template v-else>
      <view class="card hero-card">
        <view class="hero-tag">服务详情</view>
        <view class="title mt-16">{{ detail.title }}</view>
        <view class="desc">{{ detail.desc }}</view>
        <view class="price mt-20">¥{{ detail.price }}</view>
      </view>

      <view class="card mt-24 content-card">
        <view class="section-title">服务内容</view>
        <view class="line" v-for="item in detail.content" :key="item">- {{ item }}</view>
      </view>

      <button class="btn btn-primary mt-24 book-btn" @click="book">立即预约</button>
    </template>
  </view>
</template>

<script setup>
import { ref } from 'vue';
import { onLoad } from '@dcloudio/uni-app';
import { localLifeApi } from '@/api/modules';
import { trackEvent, trackPageView } from '@/utils/track';

const loading = ref(false);
const failed = ref(false);
const id = ref('');
const detail = ref({
  title: '',
  desc: '',
  price: 0,
  content: []
});

const normalize = (res) => ({
  title: res?.name || res?.title || '未命名服务',
  desc: res?.description || res?.desc || '暂无描述',
  price: res?.price ?? res?.sale_price ?? 0,
  content: res?.content || res?.items || ['暂无服务内容']
});

const loadDetail = async () => {
  if (!id.value) return;
  loading.value = true;
  failed.value = false;
  try {
    const res = await localLifeApi.serviceDetail(id.value);
    detail.value = normalize(res || {});
  } catch (error) {
    failed.value = true;
  } finally {
    loading.value = false;
  }
};

onLoad((query) => {
  id.value = query?.id || '';
  trackPageView('life_service_detail_view', { id: id.value });
  loadDetail();
});

const book = () => {
  trackEvent('life_service_detail_book', { id: id.value });
  uni.showToast({ title: '已发起预约', icon: 'none' });
};
</script>

<style scoped>
@import '@/styles/common.css';
.service-detail-page { padding-bottom: 36rpx; }
.hero-card {
  background:
    radial-gradient(circle at 96% 8%, rgba(255, 166, 82, 0.16), transparent 38%),
    linear-gradient(180deg, #fffdf9 0%, #fff7ef 100%);
  border: 1rpx solid rgba(255, 154, 106, 0.16);
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
.title { font-size: 38rpx; font-weight: 800; color: #4f321a; }
.desc { margin-top: 10rpx; color: #836a52; font-size: 24rpx; }
.price { font-size: 44rpx; color: #ff6a00; font-weight: 800; }
.content-card { border: 1rpx solid rgba(255, 154, 106, 0.16); }
.line { margin-top: 10rpx; color: #5b3a1b; font-size: 25rpx; }
.book-btn { width: 100%; }
.state-card { text-align: center; }
.retry-btn { width: 180rpx; }
</style>
