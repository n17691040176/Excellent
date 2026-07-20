import { formatDateTime, formatMoney } from './format';

function sumVisibleAssets(assetSummary = {}) {
  const total = Number(assetSummary.total_amount);
  if (!Number.isNaN(total)) return total;

  const balance = Number(assetSummary.BALANCE ?? assetSummary.balance ?? 0);
  const voucher = Number(assetSummary.VOUCHER ?? assetSummary.voucher ?? 0);
  const points = Number(assetSummary.POINTS ?? assetSummary.points ?? 0);

  return [balance, voucher, points].reduce((sum, item) => (
    sum + (Number.isNaN(item) ? 0 : item)
  ), 0);
}

export function pickListPayload(res) {
  if (Array.isArray(res)) return res;
  if (Array.isArray(res?.items)) return res.items;
  if (Array.isArray(res?.list)) return res.list;
  if (Array.isArray(res?.rows)) return res.rows;
  if (Array.isArray(res?.data)) return res.data;
  return [];
}

function preferredPayChannel(options = [], cashDue = 0, fallback = '') {
  if (Number(cashDue || 0) > 0) {
    const externalChannel = options.find((item) => ['ALIPAY', 'WECHAT'].includes(item));
    if (externalChannel) return externalChannel;
  }
  return fallback || options[0] || '';
}

export function toOrderView(item = {}, index = 0) {
  const status = item.status_text || item.status || '待支付';
  const payChannelOptions = Array.isArray(item.pay_channel_options) ? item.pay_channel_options : [];
  const cashDue = item.cash_due ?? item.payable_amount ?? 0;
  return {
    id: item.id || `o-${index}`,
    no: item.order_no || item.no || `NO.${Date.now()}${index}`,
    title: item.title || item.package_name || item.service_name || '未命名订单',
    time: formatDateTime(item.created_at || item.time),
    channel: item.biz_type === 'local_life' ? '本地生活' : item.channel_text || item.channel || '商城订单',
    amount: formatMoney(item.pay_amount ?? item.amount ?? 0),
    cashDue: formatMoney(cashDue),
    status,
    paymentCombo: item.payment_combo || '待支付',
    payChannel: preferredPayChannel(payChannelOptions, cashDue, item.default_pay_channel || item.pay_channel || ''),
    payChannelOptions,
    canPay: Boolean(item.can_pay),
    canConfirm: Boolean(item.can_confirm),
    canCancel: Boolean(item.can_cancel),
    canRefund: Boolean(item.can_refund),
    badgeClass: status === '已完成'
      ? 'badge-success'
      : status === '已发货'
        ? 'badge-info'
        : ['已取消', '已退款'].includes(status)
          ? 'badge-info'
          : 'badge-warning'
  };
}

export function toProfileOverview(profile = {}, teamSummary = {}, assetSummary = {}, commissionSummary = {}) {
  return {
    nickname: profile.nickname || profile.name || 'Excellent 用户',
    userId: profile.id || profile.user_id || '--',
    levelText: profile.level_name || '成长型合伙人',
    totalAsset: formatMoney(sumVisibleAssets(assetSummary)),
    withdrawableCommission: formatMoney(commissionSummary.withdrawable_amount ?? commissionSummary.available_amount ?? 0),
    teamMembers: teamSummary.member_count ?? teamSummary.total_members ?? 0
  };
}

export function toAssetLogs(rows = []) {
  const assetTypeLabelMap = {
    BALANCE: '余额',
    VOUCHER: '消费金',
    POINTS: '积分',
    POWER_BANK: '充电宝'
  };

  return rows.map((item, index) => {
    const amount = item.amount ?? item.change_amount ?? 0;
    const inOut = Number(amount) >= 0 ? 'in' : 'out';
    const assetType = String(item.asset_type || '').toUpperCase();
    const assetLabel = assetTypeLabelMap[assetType];
    const baseName = item.biz_name || item.title || item.remark || '资产变动';
    return {
      id: item.id || `asset-${index}`,
      name: assetLabel ? `${assetLabel} · ${baseName}` : baseName,
      amount: formatMoney(Math.abs(Number(amount || 0))),
      type: inOut,
      time: formatDateTime(item.created_at || item.time)
    };
  });
}

export function toCommissionFlows(rows = []) {
  return rows.map((item, index) => ({
    id: item.id || `cm-${index}`,
    name: item.biz_name || item.title || '佣金收益',
    status: item.status_text || item.status || '待结算',
    time: formatDateTime(item.created_at || item.time),
    amount: formatMoney(item.amount ?? item.commission_amount ?? 0)
  }));
}

export function toInviteStats(inviteRecords = []) {
  const total = inviteRecords.length;
  const valid = inviteRecords.filter((i) => i.status === 'valid' || i.status_text === '有效').length;
  return {
    total,
    valid
  };
}
