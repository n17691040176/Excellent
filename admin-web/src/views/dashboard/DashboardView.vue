<template>
  <div>
    <div class="page-heading">
      <div>
        <h2>经营总览</h2>
        <p>{{ scopeHint }}</p>
      </div>
      <el-button type="primary" @click="loadData">刷新数据</el-button>
    </div>

    <div class="metric-grid">
      <div v-for="item in metrics" :key="item.label" class="metric-card">
        <div class="label">{{ item.label }}</div>
        <div class="value">{{ item.value }}</div>
        <div class="subtext">{{ item.subtext }}</div>
      </div>
    </div>

    <div style="display:grid;grid-template-columns:1.2fr 0.8fr;gap:16px;margin-top:18px;">
      <div class="panel-card data-card">
        <div class="page-heading" style="margin-bottom:14px;">
          <div>
            <h2 style="font-size:22px;">运营关注点</h2>
            <p>当前版本建议持续盯住招商、提现和本地生活履约。</p>
          </div>
        </div>
        <el-timeline>
          <el-timeline-item timestamp="今日重点" type="primary">
            提现审核与本地生活核销需要优先保障处理时效。
          </el-timeline-item>
          <el-timeline-item timestamp="招商侧" type="warning">
            核查供应商入场费与上架资格是否匹配，避免违规商品入池。
          </el-timeline-item>
          <el-timeline-item timestamp="资产侧" type="success">
            关注套餐发券、AI 券抵扣与积分补贴链路是否一致。
          </el-timeline-item>
        </el-timeline>
      </div>

      <div class="panel-card data-card">
        <div class="page-heading" style="margin-bottom:14px;">
          <div>
            <h2 style="font-size:22px;">快捷入口</h2>
            <p>高频操作一键直达。</p>
          </div>
        </div>
        <div class="form-grid">
          <el-button plain @click="$router.push('/withdraws')">提现审核</el-button>
          <el-button plain @click="$router.push('/suppliers')">招商中心</el-button>
          <el-button plain @click="$router.push('/commission')">返现管理</el-button>
          <el-button plain @click="$router.push('/local-life')">本地生活</el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'

import { dashboardApi } from '@/api/modules'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const overview = ref({})

const scopeHint = computed(() =>
  userStore.role === 'TEAM_ADMIN'
    ? '当前为团队管理员视角，仅展示所属团队的经营数据、订单、返现与提现待办。'
    : '把核心运营数字、待办审核和资产动向放进同一张平台总览视图。'
)

const metrics = computed(() => [
  { label: '用户总数', value: overview.value.user_total ?? 0, subtext: '注册用户与运营触达基数' },
  { label: '团队总数', value: overview.value.team_total ?? 0, subtext: '组织协同与团队隔离状态' },
  { label: '订单总数', value: overview.value.order_total ?? 0, subtext: '套餐、商城与本地生活合并口径' },
  { label: '佣金总额', value: overview.value.commission_total ?? 0, subtext: `待审提现 ${overview.value.withdraw_pending_total ?? 0} 笔` }
])

async function loadData() {
  overview.value = await dashboardApi.overview()
}

onMounted(loadData)
</script>
