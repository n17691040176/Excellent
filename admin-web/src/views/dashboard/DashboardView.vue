<template>
  <div class="dashboard-view">
    <!-- 统一页面头部 -->
    <PageHeader title="经营总览" :description="scopeHint">
      <template #actions>
        <el-button type="primary" @click="loadData">刷新数据</el-button>
      </template>
    </PageHeader>

    <!-- 指标卡片行 -->
    <div class="metric-grid">
      <MetricCard
        v-for="item in metrics"
        :key="item.label"
        :value="item.value"
        :label="item.label"
        :subtext="item.subtext"
        :variant="item.variant"
      />
    </div>

    <!-- 仪表板网格 -->
    <div class="dashboard-grid">
      <div class="panel-card data-card">
        <div class="section-title-lite">
          <h3>运营关注点</h3>
          <p>当前版本建议持续盯住商品审核、提现和本地生活履约。</p>
        </div>
        <el-timeline>
          <el-timeline-item timestamp="今日重点" type="primary">
            提现审核与本地生活核销需要优先保障处理时效。
          </el-timeline-item>
          <el-timeline-item timestamp="商品侧" type="warning">
            核查商品审核、上架状态和专区配置是否匹配，避免无效商品入池。
          </el-timeline-item>
          <el-timeline-item timestamp="收益侧" type="success">
            关注套餐发券、AI 券抵扣与积分补贴链路是否一致。
          </el-timeline-item>
        </el-timeline>
      </div>

      <div class="panel-card data-card">
        <div class="section-title-lite">
          <h3>快捷入口</h3>
          <p>高频操作一键直达。</p>
        </div>
        <div class="quick-grid">
          <el-button plain @click="$router.push('/products')">商品管理</el-button>
          <el-button plain @click="$router.push('/orders')">订单管理</el-button>
          <el-button plain @click="$router.push('/withdraws')">提现审核</el-button>
          <el-button plain @click="$router.push('/decorations/home')">移动端装修</el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'

import { dashboardApi } from '@/api/modules'
import { useUserStore } from '@/stores/user'
import { PageHeader, MetricCard } from '@/components/common'

const userStore = useUserStore()
const overview = ref({})

const scopeHint = computed(() =>
  userStore.role === 'TEAM_ADMIN'
    ? '当前为团队管理员视角，仅展示所属团队的经营数据、订单、返现与提现待办。'
    : '把核心运营数字、待办审核和资产动向放进同一张平台总览视图。'
)

const metrics = computed(() => [
  { label: '用户总数', value: overview.value.user_total ?? 0, subtext: '注册用户与运营触达基数', variant: 'primary' },
  { label: '团队总数', value: overview.value.team_total ?? 0, subtext: '组织协同与团队隔离状态', variant: 'neutral' },
  { label: '订单总数', value: overview.value.order_total ?? 0, subtext: '套餐、商城与本地生活合并口径', variant: 'success' },
  { label: '待审提现', value: overview.value.withdraw_pending_total ?? 0, subtext: `佣金总额 ¥${Number(overview.value.commission_total ?? 0).toFixed(2)}`, variant: overview.value.withdraw_pending_total > 0 ? 'warning' : 'neutral' }
])

async function loadData() {
  overview.value = await dashboardApi.overview()
}

onMounted(loadData)
</script>

<style scoped>
@import '@/styles/variables.css';

.dashboard-view {
  display: grid;
  gap: var(--space-4);
}

.dashboard-grid {
  display: grid;
  grid-template-columns: 1.2fr 0.8fr;
  gap: var(--space-4);
}

.section-title-lite {
  margin-bottom: var(--space-4);
}

.section-title-lite h3 {
  margin: 0;
  font-size: var(--text-xl);
  color: var(--text-primary);
}

.section-title-lite p {
  margin: var(--space-2) 0 0;
  color: var(--text-muted);
  line-height: var(--leading-relaxed);
}

.quick-grid {
  display: grid;
  gap: var(--space-3);
}

.quick-grid .el-button {
  justify-content: flex-start;
  border-color: var(--border-default);
  background: var(--bg-surface);
}

.quick-grid .el-button:hover {
  border-color: var(--primary-mid);
  color: var(--primary-deep);
  background: var(--primary-50);
}

@media (max-width: 1100px) {
  .dashboard-grid {
    grid-template-columns: 1fr;
  }
}
</style>
