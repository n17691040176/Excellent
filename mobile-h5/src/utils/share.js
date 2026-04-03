import { showSuccessToast } from 'vant'

export async function copyInviteCode(code) {
  if (!code) return
  await navigator.clipboard.writeText(code)
  showSuccessToast('邀请码已复制')
}

export async function shareInviteLink(code) {
  const url = `${window.location.origin}/#/login?invite_code=${code}`
  await navigator.clipboard.writeText(url)
  showSuccessToast('邀请链接已复制')
}
