<template>
  <view class="container team-page">
    <view class="card hero-card">
      <view class="section-title">我的团队</view>
      <view class="muted">查看团队规模、邀请层级和最近加入成员</view>

      <view class="grid-2 mt-20">
        <view class="stat">
          <view class="num">{{ summary.total }}</view>
          <view class="label">团队成员</view>
        </view>
        <view class="stat">
          <view class="num">{{ summary.level1 }}</view>
          <view class="label">一级邀请</view>
        </view>
        <view class="stat">
          <view class="num">{{ summary.level2 }}</view>
          <view class="label">二级邀请</view>
        </view>
        <view class="stat">
          <view class="num">{{ validCount }}</view>
          <view class="label">有效成员</view>
        </view>
      </view>
    </view>

    <StateView v-if="loading" title="团队数据加载中..." custom-class="mt-24" />
    <StateView
      v-else-if="failed"
      title="团队数据加载失败"
      :show-retry="true"
      custom-class="mt-24"
      @retry="loadData"
    />
    <StateView
      v-else-if="!members.length"
      title="暂无团队成员"
      description="邀请好友注册后，这里会展示最近加入的团队成员。"
      custom-class="mt-24"
    />

    <view v-else class="member-list mt-24">
      <view v-for="m in members" :key="m.id" class="card member-card">
        <view class="row-between">
          <view class="name">{{ m.name }}</view>
          <view class="badge" :class="m.level === '一级' ? 'badge-orange' : 'badge-blue'">{{ m.level }}</view>
        </view>
        <view class="muted mt-12">手机号：{{ m.phone }}</view>
        <view class="muted mt-12">加入时间：{{ m.joinedAt }}</view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue';
import { onPullDownRefresh, onShow } from '@dcloudio/uni-app';
import StateView from '@/components/StateView.vue';
import { userApi } from '@/api/modules';
import { pickListPayload } from '@/utils/adapters';

const loading = ref(false);
const failed = ref(false);
const summary = ref({
  total: 0,
  level1: 0,
  level2: 0
});
const members = ref([]);

const validCount = computed(() => members.value.filter((item) => item.status === 'valid').length);

function formatTime(value) {
  if (!value) return '--';
  return String(value).replace('T', ' ').slice(0, 16);
}

function maskPhone(value) {
  const raw = String(value || '');
  if (raw.length < 7) return raw || '--';
  return `${raw.slice(0, 3)}****${raw.slice(-4)}`;
}

function toMemberView(item = {}, index = 0) {
  const levelNumber = Number(item.level || 1);
  return {
    id: item.id || `member-${index}`,
    name: item.nickname || `成员 ${index + 1}`,
    phone: maskPhone(item.phone),
    level: levelNumber === 2 ? '二级' : '一级',
    status: item.status || 'valid',
    joinedAt: formatTime(item.created_at || item.joined_at)
  };
}

async function loadData() {
  loading.value = true;
  failed.value = false;
  try {
    const [summaryRes, recordsRes] = await Promise.allSettled([
      userApi.teamSummary(),
      userApi.inviteRecords({ page: 1, page_size: 50 })
    ]);

    if (summaryRes.status === 'fulfilled') {
      summary.value = {
        total: Number(summaryRes.value?.member_count ?? summaryRes.value?.total_members ?? 0),
        level1: 0,
        level2: 0
      };
    }

    if (recordsRes.status === 'fulfilled') {
      const rows = pickListPayload(recordsRes.value);
      members.value = rows.map(toMemberView);
      summary.value = {
        ...summary.value,
        level1: rows.filter((item) => Number(item.level) === 1).length,
        level2: rows.filter((item) => Number(item.level) === 2).length
      };
    }

    if (summaryRes.status === 'rejected' && recordsRes.status === 'rejected') {
      failed.value = true;
    }
  } catch (error) {
    failed.value = true;
  } finally {
    loading.value = false;
  }
}

onShow(() => {
  loadData();
});

onPullDownRefresh(async () => {
  await loadData();
  uni.stopPullDownRefresh();
});
</script>

<style scoped>
@import '@/styles/common.css';

.team-page { padding-bottom: 36rpx; }

.hero-card {
  background:
    radial-gradient(circle at 95% 8%, rgba(255, 193, 120, 0.22), transparent 40%),
    linear-gradient(180deg, #fffdf9 0%, #fff7ef 100%);
}

.grid-2 { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12rpx; }

.stat {
  border-radius: 16rpx;
  background: linear-gradient(180deg, #fffaf4 0%, #fbf2e7 100%);
  padding: 14rpx;
  border: 1rpx solid rgba(198, 161, 124, 0.16);
}

.num { font-size: 34rpx; color: #b85d11; font-weight: 800; }
.label { margin-top: 4rpx; font-size: 22rpx; color: #8b7158; }
.member-list { display: flex; flex-direction: column; gap: 16rpx; }
.member-card { border-radius: 22rpx; }
.name { font-size: 30rpx; font-weight: 700; color: #4f321a; }
</style>
