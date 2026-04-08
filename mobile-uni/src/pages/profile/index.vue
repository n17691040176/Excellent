<template>
  <view class="page profile-page">
    <view class="card hero-card">
      <view v-if="loadError" class="status-card profile-status">
        <view class="status-title">个人信息加载失败</view>
        <view class="status-desc">{{ loadError }}</view>
        <button class="secondary-btn retry-btn" @click="loadData">重新加载</button>
      </view>
      <view v-else>
        <view class="profile-top">
          <view class="avatar-shell">{{ profileInitial }}</view>
          <view class="profile-main">
            <view class="title">{{ profile.nickname || '会员' }}</view>
            <view class="desc">
              手机号 {{ profile.phone || '--' }}，邀请码 {{ inviteCode || '--' }}，团队归属 {{ teamSummary.team_id || '未加入团队' }}。
            </view>
            <view class="profile-tags">
              <view class="profile-tag">资产联动</view>
              <view class="profile-tag">团队关系</view>
              <view class="profile-tag">签到权益</view>
            </view>
          </view>
        </view>

        <view class="metric-grid">
          <view class="metric-card" v-for="item in metrics" :key="item.label">
            <view class="metric-label">{{ item.label }}</view>
            <view class="metric-value">{{ item.value }}</view>
            <view class="metric-meta">{{ item.meta }}</view>
          </view>
        </view>
      </view>
    </view>

    <view class="card">
      <view class="section-head">
        <view class="section-title">账户操作</view>
        <view class="section-link">常用直达</view>
      </view>
      <view class="action-grid">
        <view class="action-item tap-item" v-for="item in actionItems" :key="item.key" @click="handleAction(item.key)">
          <view class="action-title">{{ item.title }}</view>
          <view class="action-desc">{{ item.desc }}</view>
        </view>
      </view>
    </view>

    <view class="card">
      <view class="section-head">
        <view class="section-title">资料设置</view>
        <view class="section-link">实时保存</view>
      </view>
      <input v-model="profile.nickname" class="input" placeholder="请输入昵称" maxlength="20" />
      <input v-model="profile.real_name" class="input" placeholder="请输入真实姓名" maxlength="20" />
      <input v-model="profile.avatar" class="input" placeholder="请输入头像 URL" />
      <view class="action-row">
        <button class="secondary-btn" @click="handleSignin">{{ signinLoading ? '签到中...' : '每日签到' }}</button>
        <button class="primary-btn" @click="saveProfile">{{ saveLoading ? '保存中...' : '保存资料' }}</button>
      </view>
    </view>

    <view class="card">
      <button class="danger-btn" @click="logout">退出登录</button>
    </view>
  </view>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'

import { assetApi, commissionApi, userApi } from '../../api/modules'
import { clearAuth, setUserCache } from '../../utils/auth'
import { ensureLogin } from '../../utils/guard'
import { normalizeLoadError } from '../../utils/ui'

const profile = reactive({
  nickname: '',
  phone: '',
  real_name: '',
  avatar: ''
})
const assets = ref({})
const commissionSummary = ref({})
const inviteCode = ref('')
const teamSummary = ref({})
const loadError = ref('')
const saveLoading = ref(false)
const signinLoading = ref(false)

const actionItems = [
  { key: 'orders', title: '我的订单', desc: '统一查看支付和履约状态' },
  { key: 'invite', title: '邀请好友', desc: '分享邀请码，完成上下级绑定' },
  { key: 'team', title: '我的团队', desc: '查看归属团队和成员结构' },
  { key: 'commission', title: '佣金中心', desc: '跟进冻结、释放和提现进度' },
  { key: 'assets', title: '资产中心', desc: '查看余额、积分、兑换券和 AI 券' },
  { key: 'settings', title: '账号设置', desc: '维护密码和运行时配置' }
]

const metrics = computed(() => [
  { label: '余额', value: Number(assets.value.BALANCE || 0).toFixed(2), meta: '设备分佣与爆款消费' },
  { label: '积分', value: Number(assets.value.POINTS || 0).toFixed(2), meta: '补贴排队、转赠与商城消费' },
  { label: '可提现佣金', value: Number(commissionSummary.value.available_amount || 0).toFixed(2), meta: '确认收货后释放' },
  { label: '冻结佣金', value: Number(commissionSummary.value.frozen_amount || 0).toFixed(2), meta: '订单有效支付后先冻结' }
])

const profileInitial = computed(() => {
  const source = profile.nickname || profile.real_name || profile.phone || 'M'
  return String(source).slice(0, 1).toUpperCase()
})

function openPage(url) {
  uni.navigateTo({ url })
}

function openOrders() {
  uni.navigateTo({ url: '/pages/orders/list' })
}

function handleAction(key) {
  const actionMap = {
    invite: () => openPage('/subpackages/invite/index'),
    team: () => openPage('/subpackages/team/index'),
    commission: () => openPage('/subpackages/commission/index'),
    assets: () => openPage('/subpackages/assets/index'),
    orders: openOrders,
    settings: () => openPage('/subpackages/profile/settings')
  }
  actionMap[key]?.()
}

async function loadData() {
  loadError.value = ''
  try {
    const [profileData, assetData, summaryData, codeData, teamData] = await Promise.all([
      userApi.profile(),
      assetApi.summary(),
      commissionApi.summary(),
      userApi.inviteCode(),
      userApi.teamSummary()
    ])
    Object.assign(profile, profileData || {})
    assets.value = assetData || {}
    commissionSummary.value = summaryData || {}
    inviteCode.value = codeData?.invite_code || ''
    teamSummary.value = teamData || {}
  } catch (error) {
    loadError.value = normalizeLoadError(error)
  }
}

async function saveProfile() {
  saveLoading.value = true
  try {
    const data = await userApi.updateProfile({
      nickname: profile.nickname,
      real_name: profile.real_name,
      avatar: profile.avatar
    })
    Object.assign(profile, data || {})
    setUserCache(data)
    uni.showToast({ title: '资料已更新', icon: 'success' })
  } finally {
    saveLoading.value = false
  }
}

async function handleSignin() {
  signinLoading.value = true
  try {
    await assetApi.signin()
    uni.showToast({ title: '今日签到成功', icon: 'success' })
    loadData()
  } finally {
    signinLoading.value = false
  }
}

function logout() {
  clearAuth()
  uni.reLaunch({ url: '/pages/login/index' })
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

.profile-top {
  display: flex;
  align-items: center;
  gap: 22rpx;
}

.avatar-shell {
  width: 112rpx;
  height: 112rpx;
  border-radius: 32rpx;
  background: var(--theme-dark-panel);
  color: #ffffff;
  font-size: 42rpx;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: 0 18rpx 30rpx rgba(111, 84, 58, 0.18);
}

.profile-main {
  flex: 1;
  min-width: 0;
}

.profile-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 12rpx;
  margin-top: 18rpx;
}

.profile-tag {
  padding: 10rpx 18rpx;
  border-radius: 999rpx;
  background: var(--theme-accent-soft);
  color: var(--theme-accent);
  font-size: 22rpx;
  border: 1rpx solid var(--theme-accent-border);
}

.action-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16rpx;
}

.action-item {
  background: var(--theme-surface-muted);
  border-radius: 24rpx;
  padding: 24rpx;
  min-height: 164rpx;
  box-sizing: border-box;
  border: 1rpx solid var(--theme-border);
}

.action-title {
  font-size: 30rpx;
  font-weight: 700;
  color: var(--theme-text);
  margin-bottom: 10rpx;
}

.action-desc {
  font-size: 24rpx;
  color: var(--theme-text-muted);
  line-height: 1.7;
}

.retry-btn {
  margin-top: 20rpx;
}
</style>
