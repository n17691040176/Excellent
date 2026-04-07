<template>
  <div class="page safe-bottom">
    <van-nav-bar title="个人中心" fixed placeholder />

    <div class="page-card hero-soft">
      <div class="top-row">
        <div class="avatar-badge">{{ profileInitial }}</div>
        <div style="flex: 1; min-width: 0;">
          <h2 class="page-title" style="margin-bottom: 0.1rem;">{{ profile.nickname || '会员' }}</h2>
          <p class="page-desc" style="margin-bottom: 0;">手机号 {{ profile.phone || '--' }}，邀请码 {{ inviteCode || '--' }}，团队归属 {{ teamSummary.team_id || '未加入团队' }}。</p>
          <div class="chip-list">
            <div class="chip">资产联动</div>
            <div class="chip">团队关系</div>
            <div class="chip">签到权益</div>
          </div>
        </div>
      </div>
      <div class="metric-grid">
        <div class="metric-card" v-for="item in metrics" :key="item.label">
          <div class="metric-label">{{ item.label }}</div>
          <div class="metric-value">{{ item.value }}</div>
          <div class="metric-meta">{{ item.meta }}</div>
        </div>
      </div>
    </div>

    <div class="page-card">
      <div class="section-head">
        <h3 class="cell-group-title" style="margin: 0;">账户操作</h3>
        <span class="section-link-text">常用直达</span>
      </div>
      <div class="quick-grid">
        <div class="quick-card" v-for="item in quickActions" :key="item.key" @click="router.push(item.to)">
          <div class="quick-title">{{ item.title }}</div>
          <div class="quick-desc">{{ item.desc }}</div>
        </div>
      </div>
    </div>

    <div class="page-card">
      <div class="section-head">
        <h3 class="cell-group-title" style="margin: 0;">资料设置</h3>
        <span class="section-link-text">实时保存</span>
      </div>
      <van-form @submit="saveProfile">
        <van-field v-model="profile.nickname" label="昵称" placeholder="请输入昵称" />
        <van-field v-model="profile.real_name" label="真实姓名" placeholder="请输入真实姓名" />
        <van-field v-model="profile.avatar" label="头像地址" placeholder="请输入头像 URL" />
        <div class="inline-actions submit-bar">
          <van-button block round plain type="primary" @click="handleSignin">每日签到</van-button>
          <van-button block round type="primary" native-type="submit">保存资料</van-button>
        </div>
      </van-form>
    </div>

    <AppTabbar />
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { showSuccessToast } from 'vant'

import AppTabbar from '@/components/AppTabbar.vue'
import { assetApi, commissionApi, userApi } from '@/api/modules'
import { setUserCache } from '@/utils/auth'

const router = useRouter()
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

const quickActions = [
  { key: 'invite', title: '邀请好友', desc: '分享邀请码，完成上下级绑定', to: '/invite' },
  { key: 'team', title: '我的团队', desc: '查看归属团队和成员结构', to: '/team' },
  { key: 'commission', title: '佣金中心', desc: '跟进冻结、释放和提现进度', to: '/commission' },
  { key: 'assets', title: '资产中心', desc: '查看余额、积分、兑换券和 AI 券', to: '/assets' },
  { key: 'orders', title: '我的订单', desc: '统一查看支付和履约状态', to: '/orders' },
  { key: 'settings', title: '账号设置', desc: '维护密码和运行时配置', to: '/settings' }
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

async function loadData() {
  const [profileData, assetData, summaryData, codeData, teamData] = await Promise.all([
    userApi.profile(),
    assetApi.summary(),
    commissionApi.summary(),
    userApi.inviteCode(),
    userApi.teamSummary()
  ])
  Object.assign(profile, profileData)
  assets.value = assetData || {}
  commissionSummary.value = summaryData || {}
  inviteCode.value = codeData?.invite_code || ''
  teamSummary.value = teamData || {}
}

async function saveProfile() {
  const data = await userApi.updateProfile({
    nickname: profile.nickname,
    real_name: profile.real_name,
    avatar: profile.avatar
  })
  Object.assign(profile, data)
  setUserCache(data)
  showSuccessToast('资料已更新')
}

async function handleSignin() {
  await assetApi.signin()
  showSuccessToast('今日签到成功')
  await loadData()
}

onMounted(loadData)
</script>
