<template>
  <view class="container assets-page">
    <StateView v-if="pageLoading" title="加载中..." custom-class="mt-24" />
    <StateView
      v-else-if="pageFailed"
      title="资产数据加载失败"
      :show-retry="true"
      custom-class="mt-24"
      @retry="reloadPage"
    />

    <template v-else>
      <view class="card">
        <view class="row-between section-row">
          <view>
            <view class="section-title slim-title">资产明细</view>
            <view class="muted">按资产分类查看账户余额和每一笔变动</view>
          </view>
          <view class="badge badge-orange">{{ activeAssetTab.label }}</view>
        </view>

        <view class="tab-wrap">
          <view
            v-for="tab in assetTabs"
            :key="tab.value"
            class="tab-chip interactive"
            :class="{ active: activeAssetType === tab.value }"
            @click="changeAssetType(tab.value)"
          >
            {{ tab.label }}
          </view>
        </view>

        <FilterChips
          class="mt-16"
          :items="detailRangeOptions"
          :model-value="activeDetailRange"
          @change="changeDetailRange"
        />

        <view class="detail-stat-grid mt-20">
          <view v-for="item in detailCards" :key="item.key" class="detail-stat-card">
            <view class="detail-stat-label">{{ item.label }}</view>
            <view class="detail-stat-value">{{ item.value }}</view>
            <view class="detail-stat-meta">{{ item.meta }}</view>
          </view>
        </view>

        <view class="detail-caption mt-16">{{ activeAssetTab.desc }}</view>

        <view v-if="activeAssetTips.length" class="asset-guide mt-16">
          <view v-for="item in activeAssetTips" :key="item.title" class="asset-guide-item">
            <view class="asset-guide-title">{{ item.title }}</view>
            <view class="asset-guide-desc">{{ item.desc }}</view>
          </view>
        </view>

        <view v-if="activeAssetType === 'balance'" class="withdraw-entry mt-20">
          <view>
            <view class="withdraw-title">余额提现</view>
            <view class="withdraw-tip">提现功能已拆分到独立页面，审核通过后 80% 到账，20% 自动转入消费金。</view>
          </view>
          <button class="btn btn-primary withdraw-link-btn" @click="goBalanceWithdraw">去提现</button>
        </view>

        <StateView
          v-if="detailLoading && !detailRows.length"
          title="明细加载中..."
          custom-class="asset-empty"
        />
        <StateView
          v-else-if="detailFailed && !detailRows.length"
          title="明细加载失败"
          :show-retry="true"
          custom-class="asset-empty"
          @retry="reloadAssetDetail"
        />
        <StateView
          v-else-if="!detailRows.length"
          :title="activeAssetTab.emptyTitle"
          :description="activeAssetTab.emptyDesc"
          custom-class="asset-empty"
        />

        <view v-else class="detail-list mt-20">
          <view v-for="item in detailRows" :key="item.id" class="detail-item">
            <view class="row-between detail-top">
              <view class="detail-name">{{ item.name }}</view>
              <view class="detail-amount" :class="item.type === 'in' ? 'amount-in' : 'amount-out'">
                {{ item.type === 'in' ? '+' : '-' }}{{ item.amountText }}
              </view>
            </view>
            <view class="detail-note">{{ item.summaryText }}</view>
            <view class="detail-action-row">
              <view class="detail-meta">{{ item.time }}</view>
              <view class="copy-link interactive" @click.stop="toggleDetailExpand(item.id)">
                {{ isDetailExpanded(item.id) ? '收起详情' : '展开详情' }}
              </view>
            </view>
            <DetailInfoPanel
              v-if="isDetailExpanded(item.id)"
              :items="item.detailItems"
              :note="item.detailNote"
            >
              <view v-if="item.sourceNo" class="detail-meta-copy">
                <text class="detail-meta">{{ item.sourceLabel }} {{ item.sourceNo }}</text>
                <view class="copy-link interactive" @click.stop="copyText(item.sourceNo, item.sourceLabel)">复制</view>
              </view>
            </DetailInfoPanel>
          </view>
        </view>

        <view v-if="detailRows.length" class="load-more muted">
          {{ detailLoadMoreText }}
        </view>
      </view>

      <view v-if="isPowerBankTab" class="card mt-24">
        <view class="row-between section-row">
          <view class="section-title slim-title">{{ powerBankSectionTitle }}</view>
          <view class="muted">{{ powerBanks.length }} 台</view>
        </view>
        <StateView
          v-if="!powerBanks.length"
          title="暂时还没有绑定的充电宝"
          description="绑定成功后，这里会展示设备状态、累计收益和最近结算时间。"
          custom-class="asset-empty"
        />
        <view v-else class="power-bank-list">
          <view v-for="item in powerBanks" :key="item.id" class="power-bank-item">
            <view class="row-between">
              <view class="power-bank-title">{{ item.device_name || item.device_code }}</view>
              <view class="power-bank-status" :class="item.status === 'ACTIVE' ? 'status-active' : 'status-disabled'">
                {{ item.status === 'ACTIVE' ? '生效中' : '已停用' }}
              </view>
            </view>
            <view class="power-bank-code">编号：{{ item.device_code }}</view>
            <view class="power-bank-meta">
              <text>累计收益 ¥{{ money(item.total_income_amount) }}</text>
              <text>最近结算 {{ item.last_income_date || '--' }}</text>
            </view>
            <view v-if="item.remark" class="power-bank-remark">{{ item.remark }}</view>
          </view>
        </view>
      </view>
    </template>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue';
import { onLoad, onPullDownRefresh, onReachBottom, onShow } from '@dcloudio/uni-app';

import DetailInfoPanel from '@/components/DetailInfoPanel.vue';
import FilterChips from '@/components/FilterChips.vue';
import StateView from '@/components/StateView.vue';
import { assetApi } from '@/api/modules';
import { pickListPayload } from '@/utils/adapters';

const DETAIL_PAGE_SIZE = 12;
const ASSET_PAGE_CACHE_KEY = 'asset_page_view_state';
const detailRangeOptions = [
  { value: 7, label: '最近7天' },
  { value: 30, label: '最近30天' },
  { value: 0, label: '全部' }
];
const assetTabs = [
  {
    value: 'balance',
    label: '余额',
    desc: '充电宝收益、推荐奖等会进入余额账户，也支持提现。',
    emptyTitle: '暂时还没有余额明细',
    emptyDesc: '收益入账、提现申请或余额支出后，会在这里更新记录。'
  },
  {
    value: 'voucher',
    label: '消费金',
    desc: '消费金主要用于商城抵扣，也会承接余额提现的 20% 转入。',
    emptyTitle: '暂时还没有消费金明细',
    emptyDesc: '消费金转入、抵扣使用后，会在这里更新记录。'
  },
  {
    value: 'points',
    label: '积分',
    desc: '积分用于补贴、转赠以及商城支付抵扣。',
    emptyTitle: '暂时还没有积分明细',
    emptyDesc: '积分转入、转出或抵扣使用后，会在这里更新记录。'
  },
  {
    value: 'power_bank',
    label: '充电宝',
    desc: '查看已绑定充电宝数量，以及绑定、启用、停用等设备明细。',
    emptyTitle: '暂时还没有充电宝明细',
    emptyDesc: '充电宝绑定、启用、停用或收益更新后，会在这里展示记录。'
  }
];

const pageLoading = ref(false);
const pageFailed = ref(false);
const detailLoading = ref(false);
const detailFailed = ref(false);
const summary = ref({});
const powerBanks = ref([]);
const activeAssetType = ref(assetTabs[0].value);
const assetDetail = ref({});
const detailRows = ref([]);
const detailPage = ref(1);
const detailHasMore = ref(true);
const detailRequestKey = ref(0);
const activeDetailRange = ref(detailRangeOptions[0].value);
const expandedDetailIds = ref([]);

const activeAssetTab = computed(() => assetTabs.find((item) => item.value === activeAssetType.value) || assetTabs[0]);
const isPowerBankTab = computed(() => activeAssetType.value === 'power_bank');
const activeAssetTips = computed(() => {
  if (activeAssetType.value === 'voucher') {
    return [
      { title: '消费场景', desc: '消费金主要用于商城下单抵扣，明细里会展示转入和抵扣记录。' },
      { title: '余额联动', desc: '余额提现审核通过后，其中 20% 会自动进入消费金账户。' }
    ];
  }

  if (activeAssetType.value === 'points') {
    return [
      { title: '积分用途', desc: '积分可用于补贴、转赠以及商城支付抵扣，变动都会进入明细。' },
      { title: '明细查看', desc: '转入、转出、抵扣等记录都可以通过下方明细继续追踪。' }
    ];
  }

  if (activeAssetType.value === 'power_bank') {
    return [
      { title: '设备明细', desc: '绑定、启用、停用和收益入账都会在当前明细中展示。' },
      { title: '设备列表', desc: '下方设备列表会展示已绑定充电宝的状态、收益和最近结算时间。' }
    ];
  }

  return [];
});
const powerBankStats = computed(() => {
  const rows = Array.isArray(powerBanks.value) ? powerBanks.value : [];
  const activeFromList = rows.filter((item) => String(item.status || '').toUpperCase() === 'ACTIVE').length;
  const totalCount = firstNumber(
    assetDetail.value.total_amount,
    summary.value.POWER_BANK,
    summary.value.power_bank,
    summary.value.power_bank_count,
    rows.length
  );
  const activeCount = firstNumber(assetDetail.value.available_amount, activeFromList);

  return {
    activeCount,
    totalCount
  };
});
const powerBankSectionTitle = computed(() => (isPowerBankTab.value ? '充电宝设备' : '已绑定充电宝'));
const detailCards = computed(() => {
  if (isPowerBankTab.value) {
    return [
      {
        key: 'active',
        label: '当前生效',
        value: formatAssetValue(powerBankStats.value.activeCount, true),
        meta: '当前可正常结算收益的设备数'
      },
      {
        key: 'total',
        label: '累计绑定',
        value: formatAssetValue(powerBankStats.value.totalCount, true),
        meta: '当前账号下已绑定设备总数'
      }
    ];
  }

  if (activeAssetType.value === 'balance') {
    return [
      {
        key: 'available',
        label: '当前可用',
        value: `¥${money(assetDetail.value.available_amount)}`,
        meta: '当前可直接提现或使用的余额'
      },
      {
        key: 'withdrawn',
        label: '累计提现',
        value: `¥${money(assetDetail.value.withdrawn_amount)}`,
        meta: '审核通过后实际到账金额'
      }
    ];
  }

  if (activeAssetType.value === 'voucher') {
    return [
      {
        key: 'available',
        label: '当前可用',
        value: `¥${money(assetDetail.value.available_amount)}`,
        meta: '当前可用于商城抵扣的消费金额度'
      },
      {
        key: 'consumed',
        label: '累计抵扣',
        value: `¥${money(assetDetail.value.consumed_amount)}`,
        meta: '历史下单抵扣和消费使用金额'
      }
    ];
  }

  return [
    {
      key: 'available',
      label: '当前可用',
      value: `¥${money(assetDetail.value.available_amount)}`,
      meta: '当前可继续使用或转赠的积分额度'
    },
    {
      key: 'consumed',
      label: '累计使用',
      value: `¥${money(assetDetail.value.consumed_amount)}`,
      meta: '历史转赠、抵扣或其他积分支出'
    }
  ];
});

const detailLoadMoreText = computed(() => {
  if (detailLoading.value && detailRows.value.length) return '加载更多明细中...';
  if (detailHasMore.value) return '上拉可继续加载更多明细';
  return '已经到底了';
});

function money(value) {
  return Number(value || 0).toFixed(2);
}

function normalizeAssetType(type) {
  return String(type || '').trim().toLowerCase();
}

function normalizeDetailRange(value) {
  const num = Number(value);
  return detailRangeOptions.some((item) => item.value === num) ? num : detailRangeOptions[0].value;
}

function readPageCache() {
  const cached = uni.getStorageSync(ASSET_PAGE_CACHE_KEY);
  return cached && typeof cached === 'object' ? cached : {};
}

function writePageCache() {
  uni.setStorageSync(ASSET_PAGE_CACHE_KEY, {
    tab: activeAssetType.value,
    range: activeDetailRange.value
  });
}

function firstNumber(...values) {
  for (const value of values) {
    if (value === null || value === undefined || value === '') continue;
    const num = Number(value);
    if (Number.isFinite(num)) return num;
  }
  return 0;
}

function countText(value) {
  const num = firstNumber(value);
  if (Math.abs(num - Math.round(num)) < 0.000001) {
    return String(Math.round(num));
  }
  return num.toFixed(2).replace(/\.?0+$/, '');
}

function formatAssetValue(value, isCount = false) {
  return isCount ? `${countText(value)} 台` : `¥${money(value)}`;
}

function formatDetailTime(value, short = false) {
  if (!value) return '--';
  const text = String(value).replace('T', ' ');
  return short ? text.slice(5, 16) : text.slice(0, 16);
}

function formatLedgerBizName(item, isCountAsset = false) {
  const businessType = String(item.business_type || '').trim().toUpperCase();
  const mappedName = {
    DAILY_SIGNIN: '每日签到奖励',
    POINTS_TRANSFER_OUT: '积分转出',
    POINTS_TRANSFER_IN: '积分转入',
    BALANCE_WITHDRAW_APPLY: '余额提现申请',
    BALANCE_WITHDRAW_APPROVE: '余额提现到账',
    BALANCE_WITHDRAW_REJECT: '余额提现退回',
    BALANCE_WITHDRAW_VOUCHER: '余额提现转消费金',
    POINTS_WITHDRAW_APPLY: '积分提现申请',
    POINTS_WITHDRAW_APPROVE: '积分提现到账',
    POINTS_WITHDRAW_REJECT: '积分提现退回',
    POWER_BANK_BIND: '充电宝绑定',
    POWER_BANK_ENABLE: '充电宝启用',
    POWER_BANK_DISABLE: '充电宝停用',
    POWER_BANK_DAILY_INCOME: '充电宝每日收益',
    POWER_BANK_REFERRAL_INCOME: '充电宝推荐收益',
    ORDER_DEDUCT: '下单抵扣',
    SELF_OPERATED_REWARD: '自营专区奖励',
    TEST_SEED: '测试资产初始化',
    PAYFLOW_SMOKE_SEED: '支付流程测试充值'
  }[businessType];

  if (mappedName) return mappedName;
  if (item.biz_name) return item.biz_name;
  if (businessType) return businessType.replace(/_/g, ' ');
  return isCountAsset ? '充电宝变动' : '资产变动';
}

function formatLedgerSourceLabel(item) {
  const businessType = String(item.business_type || '').trim().toUpperCase();
  return {
    ORDER_DEDUCT: '订单号',
    BALANCE_WITHDRAW_APPLY: '提现单号',
    BALANCE_WITHDRAW_APPROVE: '提现单号',
    BALANCE_WITHDRAW_REJECT: '提现单号',
    BALANCE_WITHDRAW_VOUCHER: '提现单号',
    POINTS_WITHDRAW_APPLY: '提现单号',
    POINTS_WITHDRAW_APPROVE: '提现单号',
    POINTS_WITHDRAW_REJECT: '提现单号',
    POWER_BANK_BIND: '设备编号',
    POWER_BANK_ENABLE: '设备编号',
    POWER_BANK_DISABLE: '设备编号'
  }[businessType] || '来源单号';
}

function formatLedgerNote(item, beforeText) {
  const businessType = String(item.business_type || '').trim().toUpperCase();
  const noteParts = [];
  const mappedNote = {
    ORDER_DEDUCT: '下单支付时使用该资产完成抵扣',
    DAILY_SIGNIN: '签到奖励已发放到账户',
    POINTS_TRANSFER_OUT: '积分已转赠给其他用户',
    POINTS_TRANSFER_IN: '收到他人转赠的积分',
    BALANCE_WITHDRAW_APPLY: '提现申请已提交，等待审核',
    BALANCE_WITHDRAW_APPROVE: '提现审核通过，到账部分已处理',
    BALANCE_WITHDRAW_REJECT: '提现申请未通过，金额已退回',
    BALANCE_WITHDRAW_VOUCHER: '余额提现的 20% 已自动转入消费金',
    POINTS_WITHDRAW_APPLY: '积分提现申请已提交，等待审核',
    POINTS_WITHDRAW_APPROVE: '积分提现审核通过',
    POINTS_WITHDRAW_REJECT: '积分提现未通过，积分已退回',
    POWER_BANK_BIND: '充电宝设备已绑定到当前账号',
    POWER_BANK_ENABLE: '充电宝设备已恢复生效',
    POWER_BANK_DISABLE: '充电宝设备已停用',
    POWER_BANK_DAILY_INCOME: '充电宝每日收益已入账',
    POWER_BANK_REFERRAL_INCOME: '推荐充电宝收益已入账',
    SELF_OPERATED_REWARD: '自营专区奖励已发放',
    TEST_SEED: '测试环境初始化资产',
    PAYFLOW_SMOKE_SEED: '支付流程联调初始化资产'
  }[businessType];

  if (item.remark) {
    noteParts.push(item.remark);
  } else if (mappedNote) {
    noteParts.push(mappedNote);
  }
  noteParts.push(`变动前 ${beforeText}`);
  return noteParts.join(' · ');
}

function buildDetailRows(rows = []) {
  const isCountAsset = activeAssetType.value === 'power_bank';

  return rows.map((item, index) => {
    const amount = Number(item.amount ?? item.change_amount ?? 0);
    const type = amount >= 0 ? 'in' : 'out';
    const beforeText = formatAssetValue(item.before_amount, isCountAsset);
    const afterText = formatAssetValue(item.after_amount, isCountAsset);

    return {
      id: item.id || `${activeAssetType.value}-${index}`,
      name: formatLedgerBizName(item, isCountAsset),
      amountText: formatAssetValue(Math.abs(amount), isCountAsset),
      type,
      summaryText: item.remark || formatLedgerBizName(item, isCountAsset),
      detailNote: formatLedgerNote(item, beforeText),
      beforeText,
      afterText,
      detailItems: [
        { key: 'before', label: '变动前', value: beforeText },
        { key: 'after', label: '变动后', value: afterText },
        { key: 'time', label: '变动时间', value: formatDetailTime(item.created_at || item.time) }
      ],
      sourceLabel: item.source_no ? formatLedgerSourceLabel(item) : '',
      sourceNo: item.source_no || '',
      time: formatDetailTime(item.created_at || item.time)
    };
  });
}

async function loadOverview() {
  const [summaryRes, powerBanksRes] = await Promise.allSettled([
    assetApi.summary(),
    assetApi.powerBanks()
  ]);

  if (summaryRes.status === 'fulfilled') {
    summary.value = summaryRes.value || {};
  }
  if (powerBanksRes.status === 'fulfilled') {
    powerBanks.value = pickListPayload(powerBanksRes.value);
  }

  if (summaryRes.status === 'rejected' && powerBanksRes.status === 'rejected') {
    throw new Error('overview_load_failed');
  }
}

async function loadAssetDetail({ reset = false } = {}) {
  if (detailLoading.value && !reset) return;
  if (!reset && !detailHasMore.value) return;

  const requestKey = detailRequestKey.value + 1;
  detailRequestKey.value = requestKey;
  if (reset) {
    detailRows.value = [];
    detailPage.value = 1;
    detailHasMore.value = true;
  }
  detailLoading.value = true;
  detailFailed.value = false;
  const targetPage = reset ? 1 : detailPage.value;

  try {
    let detailRes = assetDetail.value;
    const ledgerParams = { page: targetPage, page_size: DETAIL_PAGE_SIZE };
    if (Number(activeDetailRange.value) > 0) {
      ledgerParams.recent_days = Number(activeDetailRange.value);
    }
    if (reset) {
      const [accountRes, ledgerRes] = await Promise.all([
        assetApi.detail(activeAssetType.value),
        assetApi.ledgers(activeAssetType.value, ledgerParams)
      ]);
      if (requestKey !== detailRequestKey.value) return;
      detailRes = accountRes || {};
      assetDetail.value = detailRes;
      const rows = buildDetailRows(pickListPayload(ledgerRes));
      detailRows.value = rows;
      expandedDetailIds.value = expandedDetailIds.value.filter((id) => rows.some((item) => String(item.id) === String(id)));
      detailHasMore.value = rows.length >= DETAIL_PAGE_SIZE;
      detailPage.value = targetPage + 1;
      return;
    }

    const ledgerRes = await assetApi.ledgers(activeAssetType.value, ledgerParams);
    if (requestKey !== detailRequestKey.value) return;
    assetDetail.value = detailRes || {};
    const rows = buildDetailRows(pickListPayload(ledgerRes));
    detailRows.value = [...detailRows.value, ...rows];
    expandedDetailIds.value = expandedDetailIds.value.filter((id) => detailRows.value.some((item) => String(item.id) === String(id)));
    detailHasMore.value = rows.length >= DETAIL_PAGE_SIZE;
    detailPage.value = targetPage + 1;
  } catch (error) {
    if (requestKey === detailRequestKey.value) {
      detailFailed.value = true;
    }
  } finally {
    if (requestKey === detailRequestKey.value) {
      detailLoading.value = false;
    }
  }
}

async function reloadAssetDetail() {
  await loadAssetDetail({ reset: true });
}

async function reloadPage() {
  pageLoading.value = true;
  pageFailed.value = false;
  try {
    await loadOverview();
    await reloadAssetDetail();
  } catch (error) {
    pageFailed.value = true;
  } finally {
    pageLoading.value = false;
  }
}

function syncPageOptions(extra = {}) {
  const pages = getCurrentPages();
  const currentPage = pages[pages.length - 1];
  if (!currentPage?.options) return;
  currentPage.options.tab = activeAssetType.value;
  currentPage.options.range = String(activeDetailRange.value);
  Object.keys(extra).forEach((key) => {
    currentPage.options[key] = String(extra[key]);
  });
  writePageCache();
}

function changeAssetType(type) {
  const nextType = normalizeAssetType(type);
  const exists = assetTabs.some((item) => item.value === nextType);
  if (!exists || activeAssetType.value === nextType) return;
  activeAssetType.value = nextType;
  syncPageOptions();
  reloadAssetDetail();
}

function changeDetailRange(value) {
  if (activeDetailRange.value === value) return;
  activeDetailRange.value = value;
  syncPageOptions();
  reloadAssetDetail();
}

function goBalanceWithdraw() {
  uni.navigateTo({ url: `/subpackages/assets/withdraw?range=${activeDetailRange.value}` });
}

function copyText(value, label = '内容') {
  if (!value) return;
  uni.setClipboardData({
    data: String(value),
    success: () => uni.showToast({ title: `已复制${label}`, icon: 'none' })
  });
}

function toggleDetailExpand(id) {
  const key = String(id);
  if (expandedDetailIds.value.includes(key)) {
    expandedDetailIds.value = expandedDetailIds.value.filter((item) => item !== key);
    return;
  }
  expandedDetailIds.value = [...expandedDetailIds.value, key];
}

function isDetailExpanded(id) {
  return expandedDetailIds.value.includes(String(id));
}

onLoad((options = {}) => {
  const cached = readPageCache();
  const nextType = normalizeAssetType(options.tab || options.asset_type || cached.tab);
  if (assetTabs.some((item) => item.value === nextType)) {
    activeAssetType.value = nextType;
  }
  activeDetailRange.value = normalizeDetailRange(options.range || options.recent_days || cached.range);
  syncPageOptions();
});

onShow(() => {
  reloadPage();
});

onPullDownRefresh(async () => {
  await reloadPage();
  uni.stopPullDownRefresh();
});

onReachBottom(() => {
  loadAssetDetail();
});
</script>

<style scoped>
@import '@/styles/common.css';

.assets-page {
  padding-bottom: 36rpx;
}

.slim-title {
  margin-bottom: 0;
}

.section-row {
  margin-bottom: 16rpx;
}

.tab-wrap {
  display: flex;
  gap: 12rpx;
  overflow-x: auto;
}

.tab-chip {
  flex-shrink: 0;
  padding: 12rpx 22rpx;
  border-radius: 999rpx;
  background: #f6f1ea;
  color: #7f6954;
  font-size: 24rpx;
  border: 1rpx solid rgba(194, 156, 117, 0.18);
}

.tab-chip.active {
  background: #bf8752;
  color: #ffffff;
  border-color: #bf8752;
}

.detail-stat-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14rpx;
}

.detail-stat-card,
.withdraw-entry {
  padding: 18rpx;
  border-radius: 20rpx;
  background: #fffaf4;
  border: 1rpx solid rgba(198, 161, 124, 0.14);
}

.detail-stat-label {
  font-size: 22rpx;
  color: #8b7158;
}

.detail-stat-value {
  margin-top: 10rpx;
  font-size: 30rpx;
  font-weight: 800;
  color: #4f321a;
}

.detail-stat-meta,
.detail-caption {
  margin-top: 8rpx;
  font-size: 20rpx;
  color: #9a7e63;
}

.asset-guide {
  display: grid;
  gap: 12rpx;
}

.asset-guide-item {
  padding: 16rpx 18rpx;
  border-radius: 18rpx;
  background: #fffaf4;
  border: 1rpx solid rgba(198, 161, 124, 0.14);
}

.asset-guide-title {
  font-size: 24rpx;
  font-weight: 700;
  color: #4f321a;
}

.asset-guide-desc {
  margin-top: 6rpx;
  font-size: 21rpx;
  line-height: 1.55;
  color: #8d745d;
}

.withdraw-head {
  gap: 16rpx;
  align-items: flex-start;
}

.withdraw-entry {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20rpx;
}

.withdraw-title {
  font-size: 26rpx;
  font-weight: 700;
  color: #4f321a;
}

.withdraw-tip {
  margin-top: 8rpx;
  font-size: 21rpx;
  line-height: 1.5;
  color: #8d745d;
}

.withdraw-link-btn {
  width: 180rpx;
  padding: 0;
  flex-shrink: 0;
}

.asset-empty {
  padding: 16rpx 0 8rpx;
}

.detail-list,
.power-bank-list {
  display: grid;
  gap: 16rpx;
}

.detail-item,
.power-bank-item {
  padding: 18rpx;
  border-radius: 22rpx;
  background: #fffdf9;
  border: 1rpx solid rgba(198, 161, 124, 0.16);
}

.detail-name,
.power-bank-title {
  font-size: 27rpx;
  font-weight: 700;
  color: #4f321a;
  line-height: 1.35;
}

.detail-top {
  gap: 12rpx;
  align-items: flex-start;
}

.detail-amount {
  flex-shrink: 0;
  font-size: 28rpx;
  font-weight: 700;
}

.detail-note {
  margin-top: 8rpx;
  font-size: 21rpx;
  line-height: 1.5;
  color: #8d745d;
}

.detail-action-row {
  margin-top: 10rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12rpx;
}

.detail-meta-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 6rpx 12rpx;
  margin-top: 10rpx;
}

.detail-meta,
.power-bank-code,
.power-bank-meta,
.power-bank-remark {
  font-size: 20rpx;
  color: #9a7e63;
}

.detail-meta-copy {
  display: inline-flex;
  align-items: center;
  gap: 10rpx;
  flex-wrap: wrap;
}

.copy-link {
  padding: 4rpx 12rpx;
  border-radius: 999rpx;
  background: rgba(255, 138, 43, 0.12);
  color: #c96a14;
  font-size: 20rpx;
  line-height: 1.4;
}

.load-more {
  padding-top: 18rpx;
  text-align: center;
}

.power-bank-status {
  padding: 6rpx 14rpx;
  border-radius: 999rpx;
  font-size: 20rpx;
}

.status-active {
  color: #0f8b56;
  background: rgba(79, 207, 136, 0.14);
}

.status-disabled {
  color: #9a6a3d;
  background: rgba(198, 161, 124, 0.16);
}

.power-bank-code,
.power-bank-meta,
.power-bank-remark {
  margin-top: 10rpx;
}

.power-bank-meta {
  display: flex;
  justify-content: space-between;
  gap: 12rpx;
}

.amount-in {
  color: #c96a14;
}

.amount-out {
  color: #8e6d4f;
}

.interactive {
  transition: transform 180ms ease, opacity 180ms ease;
}

.interactive:active {
  transform: scale(0.98);
  opacity: 0.92;
}
</style>
