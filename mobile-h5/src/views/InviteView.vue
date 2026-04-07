<template>
  <div class="page safe-bottom">
    <van-nav-bar title="邀请好友" fixed placeholder />

    <div class="page-card hero-soft">
      <div class="hero-badge">Invite Center</div>
      <h2 class="page-title">让邀请码、邀请链路和邀请结果在一个页面闭环</h2>
      <p class="page-desc">下级通过邀请码注册后自动绑定上下级关系，仅支持一级、二级返现。</p>
      <div class="price-panel">
        <div class="price-panel-label">我的邀请码</div>
        <div class="price-panel-value">{{ inviteCode || '--' }}</div>
      </div>
      <div class="inline-actions submit-bar">
        <van-button block round plain type="primary" @click="handleCopy">复制邀请码</van-button>
        <van-button block round type="primary" @click="handleShare">复制邀请链接</van-button>
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
      <van-tabs v-model:active="activeTab" animated>
        <van-tab title="一级邀请" name="level1">
          <div v-if="loadError" class="state-card">
            <div class="state-title">邀请记录加载失败</div>
            <div class="state-desc">{{ loadError }}</div>
            <van-button block round plain type="primary" style="margin-top: 0.18rem;" @click="loadData">重新加载</van-button>
          </div>
          <div v-else-if="loading" class="card-stack">
            <div class="skeleton-card short"></div>
          </div>
          <div v-else-if="records.level1?.length" class="card-stack">
            <div class="soft-section" v-for="item in records.level1 || []" :key="`l1-${item.id}`">
              <div class="product-name">{{ item.nickname || `用户 ${item.id}` }}</div>
              <div class="product-meta">{{ item.phone || '--' }}</div>
            </div>
          </div>
          <van-empty v-else image="search" description="暂无一级邀请记录" />
        </van-tab>

        <van-tab title="二级邀请" name="level2">
          <div v-if="records.level2?.length" class="card-stack">
            <div class="soft-section" v-for="item in records.level2 || []" :key="`l2-${item.id}`">
              <div class="product-name">{{ item.nickname || `用户 ${item.id}` }}</div>
              <div class="product-meta">{{ item.phone || '--' }}</div>
            </div>
          </div>
          <van-empty v-else image="search" description="暂无二级邀请记录" />
        </van-tab>
      </van-tabs>
    </div>

    <AppTabbar />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'

import AppTabbar from '@/components/AppTabbar.vue'
import { userApi } from '@/api/modules'
import { copyInviteCode, shareInviteLink } from '@/utils/share'
import { normalizeLoadError } from '@/utils/ui'

const inviteCode = ref('')
const records = ref({})
const activeTab = ref('level1')
const loading = ref(false)
const loadError = ref('')

const metrics = computed(() => [
  { label: '一级邀请', value: records.value.level1?.length || 0, meta: '直接通过邀请码绑定' },
  { label: '二级邀请', value: records.value.level2?.length || 0, meta: '由一级邀请继续扩散' },
  { label: '邀请码', value: inviteCode.value || '--', meta: '可复制分享给潜在用户' },
  { label: '当前视图', value: activeTab.value === 'level1' ? '一级' : '二级', meta: '可切换查看两层邀请结果' }
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

async function handleCopy() {
  await copyInviteCode(inviteCode.value)
}

async function handleShare() {
  await shareInviteLink(inviteCode.value)
}

onMounted(loadData)
</script>
