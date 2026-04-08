<template>
  <view class="page">
    <view class="card hero-card">
      <view class="badge">Invite Center</view>
      <view class="title">让邀请码、邀请链路和邀请结果在一个页面闭环</view>
      <view class="desc">下级通过邀请码注册后自动绑定上下级关系，仅支持一级、二级返现。</view>
      <view class="invite-code-box">
        <view class="invite-code-label">我的邀请码</view>
        <view class="invite-code-value">{{ inviteCode || '--' }}</view>
      </view>
      <view class="action-row">
        <button class="secondary-btn" @click="handleCopy">复制邀请码</button>
        <button class="primary-btn" @click="handleShare">复制邀请链接</button>
      </view>
      <view class="metric-grid">
        <view class="metric-card" v-for="item in metrics" :key="item.label">
          <view class="metric-label">{{ item.label }}</view>
          <view class="metric-value">{{ item.value }}</view>
          <view class="metric-meta">{{ item.meta }}</view>
        </view>
      </view>
    </view>

    <view class="card">
      <view class="switch-row">
        <view class="switch-tab" :class="{ active: activeLevel === 'level1' }" @click="activeLevel = 'level1'">一级邀请</view>
        <view class="switch-tab" :class="{ active: activeLevel === 'level2' }" @click="activeLevel = 'level2'">二级邀请</view>
      </view>

      <view v-if="loadError" class="status-card">
        <view class="status-title">邀请记录加载失败</view>
        <view class="status-desc">{{ loadError }}</view>
        <button class="secondary-btn retry-btn" @click="loadData">重新加载</button>
      </view>
      <view v-else-if="loading">
        <view class="skeleton-block short"></view>
      </view>
      <view v-else-if="currentRecords.length" class="record-list">
        <view class="record-card" v-for="item in currentRecords" :key="`${activeLevel}-${item.id}`">
          <view class="record-title">{{ item.nickname || `用户 ${item.id}` }}</view>
          <view class="record-meta">{{ item.phone || '--' }}</view>
        </view>
      </view>
      <view v-else class="empty-text">{{ activeLevel === 'level1' ? '暂无一级邀请记录' : '暂无二级邀请记录' }}</view>
    </view>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'

import { userApi } from '../../api/modules'
import { ensureLogin } from '../../utils/guard'
import { copyInviteCode, copyInviteLink } from '../../utils/share'
import { normalizeLoadError } from '../../utils/ui'

const inviteCode = ref('')
const records = ref({})
const activeLevel = ref('level1')
const loading = ref(false)
const loadError = ref('')

const currentRecords = computed(() => records.value[activeLevel.value] || [])
const metrics = computed(() => [
  { label: '一级邀请', value: (records.value.level1 || []).length, meta: '直接通过邀请码绑定' },
  { label: '二级邀请', value: (records.value.level2 || []).length, meta: '由一级邀请继续扩散' },
  { label: '邀请码', value: inviteCode.value || '--', meta: '可复制分享给潜在用户' },
  { label: '当前视图', value: activeLevel.value === 'level1' ? '一级' : '二级', meta: '可切换查看两层邀请结果' }
])

async function loadData() {
  loading.value = true
  loadError.value = ''
  try {
    const [codeData, recordData] = await Promise.all([
      userApi.inviteCode(),
      userApi.inviteRecords()
    ])
    inviteCode.value = codeData?.invite_code || ''
    records.value = recordData || {}
  } catch (error) {
    loadError.value = normalizeLoadError(error)
  } finally {
    loading.value = false
  }
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
.hero-card {
  background:
    radial-gradient(circle at 100% 0%, rgba(232, 192, 149, 0.24), transparent 34%),
    radial-gradient(circle at 0% 12%, rgba(208, 220, 244, 0.28), transparent 28%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(250, 247, 241, 0.98) 100%);
}

.invite-code-box {
  background: var(--theme-dark-panel);
  border-radius: 24rpx;
  padding: 24rpx;
  margin: 18rpx 0 20rpx;
  color: #ffffff;
  box-shadow: 0 16rpx 32rpx rgba(111, 84, 58, 0.14);
}

.invite-code-label {
  font-size: 22rpx;
  opacity: 0.72;
  margin-bottom: 10rpx;
}

.invite-code-value {
  font-size: 44rpx;
  font-weight: 700;
  line-height: 1.1;
}

.record-list {
  display: grid;
  gap: 16rpx;
}

.record-card {
  margin-bottom: 0;
}

.record-meta {
  font-size: 24rpx;
  line-height: 1.7;
  color: var(--theme-text-muted);
}

.retry-btn {
  margin-top: 20rpx;
}

.short {
  height: 112rpx;
}
</style>
