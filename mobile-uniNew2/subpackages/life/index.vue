<template>
  <view class="container life-list-page">
    <view class="card hero-card">
      <view class="hero-tag">本地生活</view>
      <view class="section-title mt-12">本地服务大厅</view>
      <view class="muted">根据位置推荐高口碑服务商与可预约时段</view>
    </view>

    <view class="mt-24" v-for="item in list" :key="item.id">
      <view class="card item" @click="goDetail(item.id)">
        <view class="row-between">
          <view class="item-title">{{ item.title }}</view>
          <view class="badge badge-orange">{{ item.tag }}</view>
        </view>
        <view class="item-desc">{{ item.desc }}</view>
        <view class="row-between mt-16">
          <view class="item-price">¥{{ item.price }}</view>
          <view class="item-link">查看详情</view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref } from 'vue';

const list = ref([
  { id: 's1001', title: '全屋深度清洁', desc: '上门 3 小时，含专业工具。', price: 199, tag: '热门' },
  { id: 's1002', title: '空调拆洗保养', desc: '支持单台/多台组合服务。', price: 149, tag: '季节' }
]);

const goDetail = (id) => uni.navigateTo({ url: `/subpackages/life/service-detail?id=${id}` });
</script>

<style scoped>
@import '@/styles/common.css';
.life-list-page { padding-bottom: 36rpx; }
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
.item { margin-bottom: 16rpx; border: 1rpx solid rgba(255, 154, 106, 0.16); }
.item-title { font-size: 30rpx; font-weight: 700; color: #173a2a; }
.item-desc { margin-top: 10rpx; color: #60746a; font-size: 24rpx; }
.item-price { font-size: 34rpx; color: #ff6a00; font-weight: 800; }
.item-link { color: #ff6a00; font-size: 24rpx; }
</style>
