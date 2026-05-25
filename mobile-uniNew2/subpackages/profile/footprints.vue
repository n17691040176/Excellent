<template>
  <view class="container feature-page">
    <view class="card hero-card">
      <view class="hero-tag">浏览足迹</view>
      <view class="section-title mt-12">最近看过的商品都在这里</view>
      <view class="muted">继续查看喜欢的商品，快速回到上次浏览的位置</view>
    </view>

    <StateView v-if="loading" title="加载足迹中..." custom-class="mt-24" />
    <StateView v-else-if="failed" title="足迹加载失败" :show-retry="true" custom-class="mt-24" @retry="loadData" />
    <StateView
      v-else-if="!items.length"
      title="最近还没有浏览记录"
      description="打开商品详情后，会自动记录你的浏览足迹。"
      custom-class="mt-24"
    />

    <view v-else class="card-list mt-24">
      <view v-for="item in items" :key="item.product_id" class="card goods-card">
        <view class="goods-thumb-wrap">
          <image v-if="item.image" class="goods-cover" :src="item.image" mode="aspectFill" />
          <view v-else class="goods-cover goods-fallback" />
          <view class="goods-badge">{{ item.view_count || 1 }}次</view>
        </view>

        <view class="goods-main">
          <view class="row-between">
            <view class="goods-title">{{ item.title }}</view>
          </view>
          <view class="goods-desc">{{ item.desc || '最近浏览商品' }}</view>
          <view class="goods-meta">最近浏览 {{ formatTime(item.last_viewed_at) }}</view>
          <view class="row-between mt-16">
            <view class="price">¥{{ money(item.price || item.sale_price) }}</view>
            <view class="row gap-12">
              <button class="btn btn-ghost mini-btn" @click="removeItem(item.product_id)">删除</button>
              <button class="btn btn-primary mini-btn" @click="goDetail(item.product_id)">继续看</button>
            </view>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref } from 'vue';
import { onShow } from '@dcloudio/uni-app';
import StateView from '@/components/StateView.vue';
import { commerceApi } from '@/api/modules';
import { pickListPayload } from '@/utils/adapters';

const loading = ref(false);
const failed = ref(false);
const items = ref([]);

function money(value) {
  return Number(value || 0).toFixed(2);
}

function formatTime(value) {
  if (!value) return '--';
  return String(value).replace('T', ' ').slice(0, 16);
}

async function loadData() {
  loading.value = true;
  failed.value = false;
  try {
    const res = await commerceApi.footprints({ page: 1, page_size: 50 });
    items.value = pickListPayload(res);
  } catch (error) {
    failed.value = true;
  } finally {
    loading.value = false;
  }
}

async function removeItem(productId) {
  await commerceApi.removeFootprint(productId);
  items.value = items.value.filter((item) => item.product_id !== productId);
}

function goDetail(productId) {
  uni.navigateTo({ url: `/subpackages/package/detail?id=${productId}` });
}

onShow(loadData);
</script>

<style scoped>
@import '@/styles/common.css';

.feature-page { padding-bottom: 36rpx; }
.hero-card {
  background:
    radial-gradient(circle at 96% 10%, rgba(255, 166, 82, 0.16), transparent 32%),
    linear-gradient(180deg, #fffdf9 0%, #fff6ec 100%);
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
.card-list { display: flex; flex-direction: column; gap: 16rpx; }
.goods-card { display: flex; gap: 18rpx; border: 1rpx solid rgba(255, 154, 106, 0.16); }
.goods-thumb-wrap { position: relative; flex-shrink: 0; }
.goods-cover {
  width: 180rpx;
  height: 180rpx;
  border-radius: 20rpx;
  flex-shrink: 0;
  background: #f3eadf;
}
.goods-badge {
  position: absolute;
  left: 12rpx;
  top: 12rpx;
  padding: 4rpx 12rpx;
  border-radius: 999rpx;
  background: rgba(255, 255, 255, 0.9);
  color: #ff6a00;
  font-size: 18rpx;
  font-weight: 700;
}
.goods-fallback { background: linear-gradient(135deg, #ffcf9c, #ff9f5e 46%, #ff7a00); }
.goods-main { flex: 1; min-width: 0; }
.goods-title { font-size: 28rpx; font-weight: 700; color: #4f321a; line-height: 1.35; }
.goods-desc { margin-top: 10rpx; font-size: 22rpx; color: #8b7158; line-height: 1.45; }
.goods-meta { margin-top: 10rpx; font-size: 20rpx; color: #a08469; }
.price { font-size: 34rpx; color: #ff6a00; font-weight: 800; }
.mini-btn { width: 132rpx; height: 58rpx; line-height: 58rpx; padding: 0; font-size: 22rpx; }
</style>
