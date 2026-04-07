const DEFAULT_LOAD_ERROR = '请检查网络或接口状态后重试'

const ORDER_STATUS_LABELS = {
  CREATED: '待支付',
  PAID: '待完成',
  CONFIRMED: '已完成',
  CLOSED: '已关闭'
}

const ORDER_STATUS_TONES = {
  CREATED: 'tone-created',
  PAID: 'tone-paid',
  CONFIRMED: 'tone-confirmed',
  CLOSED: 'tone-closed'
}

const COMMISSION_FLOW_STATUS_LABELS = {
  FROZEN: '冻结中',
  SETTLED: '已结算',
  CANCELED: '已取消'
}

const COMMISSION_FLOW_STATUS_TONES = {
  FROZEN: 'tone-created',
  SETTLED: 'tone-confirmed',
  CANCELED: 'tone-closed'
}

const WITHDRAW_STATUS_LABELS = {
  PENDING: '待审核',
  APPROVED: '已通过',
  REJECTED: '已驳回',
  PAID: '已打款'
}

const WITHDRAW_STATUS_TONES = {
  PENDING: 'tone-created',
  APPROVED: 'tone-confirmed',
  REJECTED: 'tone-closed',
  PAID: 'tone-paid'
}

const ASSET_DIRECTION_LABELS = {
  INCOME: '收入',
  EXPENSE: '支出'
}

const ASSET_DIRECTION_TONES = {
  INCOME: 'tone-income',
  EXPENSE: 'tone-expense'
}

const TEAM_ROLE_LABELS = {
  OWNER: '负责人',
  MEMBER: '成员'
}

function normalizeMessage(value) {
  return typeof value === 'string' ? value.trim() : ''
}

export function normalizeLoadError(error, fallback = DEFAULT_LOAD_ERROR) {
  const message =
    normalizeMessage(error?.response?.data?.message) ||
    normalizeMessage(error?.message) ||
    normalizeMessage(error)

  return message || fallback
}

export function orderStatusLabel(status, overrides = {}) {
  const labels = { ...ORDER_STATUS_LABELS, ...overrides }
  return labels[status] || status || '--'
}

export function orderStatusTone(status) {
  return ORDER_STATUS_TONES[status] || 'tone-default'
}

export function commissionFlowStatusLabel(status) {
  return COMMISSION_FLOW_STATUS_LABELS[status] || status || '--'
}

export function commissionFlowStatusTone(status) {
  return COMMISSION_FLOW_STATUS_TONES[status] || 'tone-default'
}

export function withdrawStatusLabel(status) {
  return WITHDRAW_STATUS_LABELS[status] || status || '--'
}

export function withdrawStatusTone(status) {
  return WITHDRAW_STATUS_TONES[status] || 'tone-default'
}

export function assetDirectionLabel(direction) {
  return ASSET_DIRECTION_LABELS[direction] || direction || '--'
}

export function assetDirectionTone(direction) {
  return ASSET_DIRECTION_TONES[direction] || 'tone-default'
}

export function teamRoleLabel(role) {
  return TEAM_ROLE_LABELS[role] || role || '--'
}
