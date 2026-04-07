<template>
  <view class="page">
    <view class="card">
      <view class="title">邀请码与分享</view>
      <view class="desc">下级通过邀请码注册后自动绑定上下级关系，仅支持一级、二级返现。</view>
      <view class="info-list">
        <view class="info-row">我的邀请码：{{ inviteCode || '--' }}</view>
        <view class="info-row">一级邀请人数：{{ (records.level1 || []).length }}</view>
        <view class="info-row">二级邀请人数：{{ (records.level2 || []).length }}</view>
      </view>
      <view class="action-row">
        <button class="secondary-btn" @click="handleCopy">复制邀请码</button>
        <button class="primary-btn" @click="handleShare">复制邀请链接</button>
      </view>
    </view>

    <view class="card">
      <view class="section-title">一级邀请</view>
      <view v-if="(records.level1 || []).length">
        <view class="record-card" v-for="item in records.level1 || []" :key="`l1-${item.id}`">
          <view class="record-title">{{ item.nickname || `用户 ${item.id}` }}</view>
          <view class="record-meta">{{ item.phone || '--' }}</view>
        </view>
      </view>
      <view v-else class="empty-text">暂无一级邀请记录</view>
    </view>

    <view class="card">
      <view class="section-title">二级邀请</view>
      <view v-if="(records.level2 || []).length">
        <view class="record-card" v-for="item in records.level2 || []" :key="`l2-${item.id}`">
          <view class="record-title">{{ item.nickname || `用户 ${item.id}` }}</view>
          <view class="record-meta">{{ item.phone || '--' }}</view>
        </view>
      </view>
      <view v-else class="empty-text">暂无二级邀请记录</view>
    </view>
  </view>
</template>

<script setup>
import { ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'

import { userApi } from '../../api/modules'
import { ensureLogin } from '../../utils/guard'
import { copyInviteCode, copyInviteLink } from '../../utils/share'

const inviteCode = ref('')
const records = ref({})

async function loadData() {
  const [codeData, recordData] = await Promise.all([
    userApi.inviteCode(),
    userApi.inviteRecords()
  ])
  inviteCode.value = codeData?.invite_code || ''
  records.value = recordData || {}
}

function handleCopy() {
  copyInviteCode(inviteCode.value)
}

function handleShare() {
  copyInviteLink(inviteCode.value)
}

onShow(() => {
  if (!ensureLogin()) {
    return
  }
  loadData()
})
</script>

<style scoped>
.page { min-height: 100vh; padding: 32rpx; }
.card { background: #ffffff; border-radius: 24rpx; padding: 32rpx; margin-bottom: 24rpx; }
.title { font-size: 40rpx; font-weight: 600; margin-bottom: 16rpx; }
.desc { font-size: 28rpx; color: #6b7280; line-height: 1.6; margin-bottom: 20rpx; }
.section-title { font-size: 34rpx; font-weight: 600; margin-bottom: 20rpx; }
.info-list { display: grid; gap: 12rpx; margin-bottom: 20rpx; }
.info-row, .record-meta, .empty-text { font-size: 26rpx; color: #4b5563; line-height: 1.6; }
.action-row { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16rpx; }
.record-card {
  background: #f5f7fb;
  border-radius: 20rpx;
  padding: 24rpx;
  margin-bottom: 16rpx;
}
.record-title { font-size: 30rpx; font-weight: 600; margin-bottom: 8rpx; }
.primary-btn,
.secondary-btn {
  height: 88rpx;
  line-height: 88rpx;
  border-radius: 18rpx;
  font-size: 30rpx;
}
.primary-btn { background: #0d6efd; color: #ffffff; }
.secondary-btn { background: #eef4ff; color: #0d6efd; }
</style>
