<template>
  <div class="page safe-bottom">
    <van-nav-bar title="邀请好友" fixed placeholder />

    <div class="page-card">
      <h2 class="page-title">邀请码与分享</h2>
      <p class="page-desc">下级通过邀请码注册后自动绑定上下级关系，仅支持一级、二级返现。</p>
      <van-cell-group inset>
        <van-cell title="我的邀请码" :value="inviteCode" />
        <van-cell title="一级邀请人数" :value="String(records.level1?.length || 0)" />
        <van-cell title="二级邀请人数" :value="String(records.level2?.length || 0)" />
      </van-cell-group>
      <div class="inline-actions submit-bar">
        <van-button block round plain type="primary" @click="handleCopy">复制邀请码</van-button>
        <van-button block round type="primary" @click="handleShare">复制邀请链接</van-button>
      </div>
    </div>

    <div class="page-card">
      <h3 class="cell-group-title">一级邀请</h3>
      <van-cell-group inset>
        <van-cell v-for="item in records.level1 || []" :key="`l1-${item.id}`" :title="item.nickname || `用户 ${item.id}`" :label="item.phone || '--'" />
      </van-cell-group>
      <van-empty v-if="!(records.level1 || []).length" image="search" description="暂无一级邀请记录" />
    </div>

    <div class="page-card">
      <h3 class="cell-group-title">二级邀请</h3>
      <van-cell-group inset>
        <van-cell v-for="item in records.level2 || []" :key="`l2-${item.id}`" :title="item.nickname || `用户 ${item.id}`" :label="item.phone || '--'" />
      </van-cell-group>
      <van-empty v-if="!(records.level2 || []).length" image="search" description="暂无二级邀请记录" />
    </div>

    <AppTabbar />
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'

import AppTabbar from '@/components/AppTabbar.vue'
import { userApi } from '@/api/modules'
import { copyInviteCode, shareInviteLink } from '@/utils/share'

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

async function handleCopy() {
  await copyInviteCode(inviteCode.value)
}

async function handleShare() {
  await shareInviteLink(inviteCode.value)
}

onMounted(loadData)
</script>
