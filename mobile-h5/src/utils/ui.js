const DEFAULT_LOAD_ERROR = '请检查网络或接口状态后重试'

const ORDER_STATUS_LABELS = {
  CREATED: '待支付',
  PAID: '待完成',
  CONFIRMED: '已完成',
  CLOSED: '已关闭'
}

const ORDER_STATUS_CLASSES = {
  CREATED: 'status-warning',
  PAID: 'status-primary',
  CONFIRMED: 'status-success',
  CLOSED: 'status-muted'
}

const COMMISSION_FLOW_STATUS_LABELS = {
  FROZEN: '冻结中',
  SETTLED: '已结算',
  CANCELED: '已取消'
}

const COMMISSION_FLOW_STATUS_CLASSES = {
  FROZEN: 'status-warning',
  SETTLED: 'status-success',
  CANCELED: 'status-muted'
}

const WITHDRAW_STATUS_LABELS = {
  PENDING: '待审核',
  APPROVED: '已通过',
  REJECTED: '已驳回',
  PAID: '已打款'
}

const WITHDRAW_STATUS_CLASSES = {
  PENDING: 'status-warning',
  APPROVED: 'status-success',
  REJECTED: 'status-danger',
  PAID: 'status-primary'
}

const ASSET_DIRECTION_LABELS = {
  INCOME: '收入',
  EXPENSE: '支出'
}

const ASSET_DIRECTION_CLASSES = {
  INCOME: 'status-success',
  EXPENSE: 'status-danger'
}

const TEAM_ROLE_LABELS = {
  OWNER: '负责人',
  MEMBER: '成员'
}

const TEAM_ROLE_CLASSES = {
  OWNER: 'status-success',
  MEMBER: 'status-primary'
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

export function orderStatusClass(status) {
  return ORDER_STATUS_CLASSES[status] || 'status-muted'
}

export function commissionFlowStatusLabel(status) {
  return COMMISSION_FLOW_STATUS_LABELS[status] || status || '--'
}

export function commissionFlowStatusClass(status) {
  return COMMISSION_FLOW_STATUS_CLASSES[status] || 'status-muted'
}

export function withdrawStatusLabel(status) {
  return WITHDRAW_STATUS_LABELS[status] || status || '--'
}

export function withdrawStatusClass(status) {
  return WITHDRAW_STATUS_CLASSES[status] || 'status-muted'
}

export function assetDirectionLabel(direction) {
  return ASSET_DIRECTION_LABELS[direction] || direction || '--'
}

export function assetDirectionClass(direction) {
  return ASSET_DIRECTION_CLASSES[direction] || 'status-muted'
}

export function teamRoleLabel(role) {
  return TEAM_ROLE_LABELS[role] || role || '--'
}

export function teamRoleClass(role) {
  return TEAM_ROLE_CLASSES[role] || 'status-muted'
}
