<template>
  <view class="container life-orders-page">
    <view class="card">
      <view class="section-title">本地生活订单</view>
      <view class="muted">预约、上门、完成等状态统一查看</view>
    </view>

    <StateView v-if="loading && !list.length" title="加载中..." custom-class="mt-24" />
    <StateView v-else-if="failed && !list.length" title="订单加载失败" :show-retry="true" custom-class="mt-24" @retry="reload" />

    <template v-else>
      <view class="mt-24" v-for="item in list" :key="item.no">
        <view class="card order-item">
          <view class="row-between">
            <view class="no">{{ item.no }}</view>
            <view class="badge" :class="item.badge">{{ item.status }}</view>
          </view>
          <view class="name">{{ item.name }}</view>
          <view class="muted mt-16">预约时间：{{ item.time }}</view>
        </view>
      </view>

      <view v-if="!list.length" class="card state-card mt-24">
        <view class="state-title">暂无生活订单</view>
        <view class="muted">先去服务大厅看看热门服务。</view>
      </view>

      <view v-if="list.length" class="load-more muted">{{ loadMoreText }}</view>
    </template>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue';
import { onPullDownRefresh, onReachBottom, onShow } from '@dcloudio/uni-app';
import StateView from '@/components/StateView.vue';
import { localLifeApi } from '@/api/modules';
import { pickListPayload } from '@/utils/adapters';

const loading = ref(false);
const failed = ref(false);
const page = ref(1);
const pageSize = 10;
const hasMore = ref(true);
const list = ref([]);

const toLifeOrderView = (item = {}, index = 0) => {
  const status = item.status_text || item.status || '待上门';
  return {
    no: item.order_no || item.no || `LIFE-${Date.now()}-${index}`,
    name: item.service_name || item.title || '未命名服务订单',
    time: item.appointment_time || item.time || item.created_at || '--',
    status,
    badge: status === '已完成' ? 'badge-green' : status === '运输中' ? 'badge-blue' : 'badge-orange'
  };
};

const fetchList = async ({ reset = false } = {}) => {
  if (loading.value) return;
  if (!reset && !hasMore.value) return;

  loading.value = true;
  failed.value = false;
  const targetPage = reset ? 1 : page.value;

  try {
    const res = await localLifeApi.orders({ page: targetPage, page_size: pageSize });
    const rows = pickListPayload(res).map(toLifeOrderView);
    list.value = reset ? rows : [...list.value, ...rows];
    hasMore.value = rows.length >= pageSize;
    page.value = targetPage + 1;
  } catch (error) {
    failed.value = true;
  } finally {
    loading.value = false;
  }
};

const reload = () => fetchList({ reset: true });

const loadMoreText = computed(() => {
  if (loading.value) return '加载更多中...';
  return hasMore.value ? '上拉加载更多' : '没有更多了';
});

onShow(() => {
  reload();
});

onPullDownRefresh(async () => {
  await reload();
  uni.stopPullDownRefresh();
});

onReachBottom(() => {
  fetchList();
});
</script>

<style scoped>
@import '@/styles/common.css';
.life-orders-page { padding-bottom: 36rpx; }
.order-item { margin-bottom: 16rpx; }
.no { font-size: 23rpx; color: #667a71; }
.name { margin-top: 12rpx; font-size: 30rpx; font-weight: 700; color: #173a2a; }
.state-card { text-align: center; }
.state-title { font-size: 30rpx; font-weight: 700; color: #173a2a; margin-bottom: 8rpx; }
.retry-btn { width: 180rpx; margin-left: auto; margin-right: auto; }
.load-more { text-align: center; padding: 12rpx 0 18rpx; }
</style>
