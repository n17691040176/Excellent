import { getInviteWebBaseUrl } from '../config/index'

export function copyInviteCode(code) {
  if (!code) {
    uni.showToast({ title: '暂无邀请码', icon: 'none' })
    return
  }
  uni.setClipboardData({
    data: code,
    showToast: false,
    success() {
      uni.showToast({ title: '邀请码已复制', icon: 'success' })
    }
  })
}

export function copyInviteLink(code) {
  if (!code) {
    uni.showToast({ title: '暂无邀请码', icon: 'none' })
    return
  }
  const base = getInviteWebBaseUrl().replace(/\/$/, '')
  const url = `${base}/#/login?invite_code=${encodeURIComponent(code)}`
  uni.setClipboardData({
    data: url,
    showToast: false,
    success() {
      uni.showToast({ title: '邀请链接已复制', icon: 'success' })
    }
  })
}
