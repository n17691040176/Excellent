<template>
  <view class="address-page">
    <view class="page-header">
      <view class="back-btn" @click="goBack">←</view>
      <text class="header-title">收货地址</text>
      <view class="header-action" @click="addAddress">新增</view>
    </view>

    <view v-if="loading" class="state-card">地址加载中...</view>
    <view v-else-if="!addresses.length" class="state-card">
      <text>暂无收货地址</text>
      <button class="primary-btn" @click="addAddress">添加地址</button>
    </view>
    <view v-else class="address-list">
      <view v-for="item in addresses" :key="item.id" class="address-card" @click="chooseAddress(item)">
        <view class="address-main">
          <text class="contact">{{ item.receiver_name }} {{ item.receiver_phone }}</text>
          <text v-if="item.is_default" class="default-tag">默认</text>
        </view>
        <text class="detail">{{ item.full_address || fullAddress(item) }}</text>
        <view class="actions" @click.stop>
          <text v-if="!item.is_default" @click="setDefault(item)">设为默认</text>
          <text @click="editAddress(item)">编辑</text>
          <text class="danger" @click="removeAddress(item)">删除</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref } from 'vue';
import { onLoad, onShow } from '@dcloudio/uni-app';
import { addressApi } from '@/api/modules';
import { pickListPayload } from '@/utils/adapters';

const loading = ref(false);
const addresses = ref([]);
const selectMode = ref(false);

function fullAddress(item) {
  return [item.province, item.city, item.district, item.detail_address].filter(Boolean).join(' ');
}

async function loadData() {
  loading.value = true;
  try {
    addresses.value = pickListPayload(await addressApi.list());
  } finally {
    loading.value = false;
  }
}

function goBack() {
  uni.navigateBack();
}

function addAddress() {
  uni.navigateTo({ url: '/subpackages/profile/address-edit' });
}

function editAddress(item) {
  uni.navigateTo({ url: `/subpackages/profile/address-edit?id=${item.id}` });
}

async function setDefault(item) {
  await addressApi.setDefault(item.id);
  await loadData();
  uni.showToast({ title: '默认地址已更新', icon: 'success' });
}

async function chooseAddress(item) {
  if (!selectMode.value) return;
  if (!item.is_default) await addressApi.setDefault(item.id);
  uni.navigateBack();
}

async function removeAddress(item) {
  uni.showModal({
    title: '删除地址',
    content: '确认删除该收货地址吗？',
    success: async ({ confirm }) => {
      if (!confirm) return;
      await addressApi.remove(item.id);
      await loadData();
      uni.showToast({ title: '地址已删除', icon: 'success' });
    }
  });
}

onLoad((query) => {
  selectMode.value = query?.select === '1';
});

onShow(loadData);
</script>

<style scoped>
@import '@/styles/elegant.css';

.address-page { min-height: 100vh; background: var(--bg); }
.page-header { display: flex; align-items: center; justify-content: space-between; padding: 24rpx 32rpx; padding-top: calc(24rpx + env(safe-area-inset-top)); background: var(--card); border-bottom: 1rpx solid var(--border-light); }
.back-btn, .header-action { width: 88rpx; color: var(--primary); }
.header-action { text-align: right; }
.header-title { color: var(--text); font-size: 32rpx; font-weight: 700; }
.state-card, .address-card { margin: 24rpx; padding: 28rpx; background: var(--card); border: 1rpx solid var(--border-light); border-radius: var(--radius-xl); }
.state-card { text-align: center; color: var(--text-muted); }
.primary-btn { margin-top: 24rpx; color: white; background: var(--primary); }
.address-main { display: flex; align-items: center; gap: 16rpx; }
.contact { color: var(--text); font-weight: 700; }
.default-tag { padding: 4rpx 12rpx; color: var(--primary); background: var(--primary-bg); border-radius: 999rpx; font-size: 20rpx; }
.detail { display: block; margin-top: 16rpx; color: var(--text-muted); line-height: 1.6; }
.actions { display: flex; justify-content: flex-end; gap: 28rpx; margin-top: 22rpx; padding-top: 18rpx; border-top: 1rpx solid var(--border-light); color: var(--primary); font-size: 24rpx; }
.danger { color: var(--error); }
</style>
