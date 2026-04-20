<template>
  <view class="container feature-page">
    <StateView v-if="loading" title="加载足迹中..." />
    <StateView v-else-if="failed" title="足迹加载失败" :show-retry="true" @retry="loadData" />
    <StateView
      v-else-if="!items.length"
      title="最近还没有浏览记录"
      description="打开商品详情后，会自动记录你的浏览足迹。"
    />

    <view v-else class="card-list">
      <view v-for="item in items" :key="item.product_id" class="card goods-card">
        <image v-if="item.image" class="goods-cover" :src="item.image" mode="aspectFill" />
        <view v-else class="goods-cover goods-fallback" />

        <view class="goods-main">
          <view class="row-between">
            <view class="goods-title">{{ item.title }}</view>
            <view class="badge badge-orange">{{ item.view_count || 1 }}次</view>
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
.card-list { display: flex; flex-direction: column; gap: 16rpx; }
.goods-card { display: flex; gap: 18rpx; }
.goods-cover {
  width: 180rpx;
  height: 180rpx;
  border-radius: 20rpx;
  flex-shrink: 0;
  background: #f3eadf;
}
.goods-fallback { background: linear-gradient(135deg, #f1dec9, #e7c8a4 46%, #d8af83); }
.goods-main { flex: 1; min-width: 0; }
.goods-title { font-size: 28rpx; font-weight: 700; color: #4f321a; line-height: 1.35; }
.goods-desc { margin-top: 10rpx; font-size: 22rpx; color: #8b7158; line-height: 1.45; }
.goods-meta { margin-top: 10rpx; font-size: 20rpx; color: #a08469; }
.price { font-size: 34rpx; color: #c96a14; font-weight: 800; }
.mini-btn { width: 132rpx; height: 58rpx; line-height: 58rpx; padding: 0; font-size: 22rpx; }
</style>
