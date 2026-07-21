<template>
  <view class="invite-page">
    <view class="page-header">
      <view class="header-content">
        <AppBackButton @click="goBack" />
        <view class="logo-mark">邀</view>
        <text class="page-title">邀请好友</text>
        <view class="header-badge">实时</view>
      </view>
    </view>

    <view class="invite-card">
      <text class="card-kicker">我的专属邀请</text>
      <text class="card-title">分享二维码，邀请好友加入</text>
      <text class="card-subtitle">好友扫码并登录后，将自动成为你的直属下级</text>

      <view class="code-wrap">
        <text class="code-label">邀请码</text>
        <text class="code-value">{{ inviteCode || '加载中' }}</text>
        <button class="copy-btn" :disabled="!inviteCode" @click="copyCode">复制</button>
      </view>

      <view class="action-row">
        <button class="action-btn primary" :disabled="posterGenerating" @click="share">
          {{ posterGenerating ? '生成中...' : '立即分享' }}
        </button>
        <button class="action-btn secondary" :disabled="binding" @click="scanInvite">
          {{ binding ? '绑定中...' : '扫一扫绑定' }}
        </button>
      </view>
      <button class="manual-btn" @click="openManualBind">无法扫码？输入邀请码</button>
    </view>

    <view class="stats-card">
      <view class="card-header">
        <text class="section-title">邀请数据</text>
        <view class="update-badge">实时更新</view>
      </view>

      <view v-if="loading" class="loading-stats">
        <view class="skeleton skeleton-stat" />
        <view class="skeleton skeleton-stat" />
      </view>

      <view v-else-if="failed" class="error-stats">
        <text class="error-text">数据加载失败</text>
        <button class="retry-text" @click="loadInvite">重新加载</button>
      </view>

      <view v-else class="stats-grid">
        <view class="stat-item">
          <text class="stat-value">{{ stats.total }}</text>
          <text class="stat-label">累计邀请</text>
        </view>
        <view class="stat-divider" />
        <view class="stat-item">
          <text class="stat-value">{{ stats.valid }}</text>
          <text class="stat-label">有效绑定</text>
        </view>
      </view>
    </view>

    <canvas
      id="invitePosterCanvas"
      canvas-id="invitePosterCanvas"
      class="poster-canvas"
      :style="{ width: `${POSTER_WIDTH}px`, height: `${POSTER_HEIGHT}px` }"
    />

    <view v-if="posterVisible" class="modal-mask" @click="closePoster">
      <view class="poster-modal" @click.stop>
        <view class="modal-header">
          <text class="modal-title">邀请海报</text>
          <button class="close-btn" aria-label="关闭" @click="closePoster">×</button>
        </view>
        <view class="poster-preview">
          <image
            v-if="posterPath"
            class="poster-image"
            :src="posterPath"
            mode="widthFix"
            @click="previewPoster"
          />
          <view v-else class="poster-loading">正在生成海报...</view>
        </view>
        <view class="poster-actions">
          <button class="modal-action primary-action" :disabled="!posterPath" @click="savePoster">保存海报</button>
          <button class="modal-action" @click="copyLink">复制链接</button>
          <!-- #ifdef MP-WEIXIN -->
          <button class="modal-action" open-type="share">发送给好友</button>
          <!-- #endif -->
        </view>
      </view>
    </view>

    <view v-if="manualBindVisible" class="modal-mask" @click="closeManualBind">
      <view class="bind-modal" @click.stop>
        <view class="modal-header">
          <text class="modal-title">输入邀请码</text>
          <button class="close-btn" aria-label="关闭" @click="closeManualBind">×</button>
        </view>
        <input
          v-model="manualInviteCode"
          class="invite-input"
          maxlength="32"
          placeholder="请输入对方的邀请码"
          confirm-type="done"
          @confirm="submitManualBind"
        />
        <button class="bind-confirm" :disabled="binding" @click="submitManualBind">
          {{ binding ? '绑定中...' : '确认绑定' }}
        </button>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed, nextTick, ref } from 'vue';
import { onPullDownRefresh, onShareAppMessage, onShow } from '@dcloudio/uni-app';
import QRCode from 'qrcode';

import { userApi } from '@/api/modules';
import { getInviteWebBaseUrl } from '@/config';
import { pickListPayload, toInviteStats } from '@/utils/adapters';
import { buildInviteUrl, extractInviteCode } from '@/utils/invite';
import { trackPageView } from '@/utils/track';

const POSTER_WIDTH = 600;
const POSTER_HEIGHT = 840;
const POSTER_CANVAS_ID = 'invitePosterCanvas';

const loading = ref(false);
const failed = ref(false);
const binding = ref(false);
const posterGenerating = ref(false);
const posterVisible = ref(false);
const manualBindVisible = ref(false);
const inviteCode = ref('');
const manualInviteCode = ref('');
const posterPath = ref('');
const posterCode = ref('');
const stats = ref({ total: 0, valid: 0 });

const inviteUrl = computed(() => buildInviteUrl(getInviteWebBaseUrl(), inviteCode.value));

const loadInvite = async () => {
  loading.value = true;
  failed.value = false;
  try {
    const [codeRes, recordsRes] = await Promise.allSettled([
      userApi.inviteCode(),
      userApi.inviteRecords({ page: 1, page_size: 50 })
    ]);

    if (codeRes.status === 'fulfilled') {
      const nextCode = codeRes.value?.invite_code || codeRes.value?.code || '';
      if (nextCode !== inviteCode.value) {
        inviteCode.value = nextCode;
        posterPath.value = '';
        posterCode.value = '';
      }
    }
    if (recordsRes.status === 'fulfilled') {
      stats.value = toInviteStats(pickListPayload(recordsRes.value));
    }

    if (codeRes.status === 'rejected' && recordsRes.status === 'rejected') {
      failed.value = true;
    }
  } catch (error) {
    failed.value = true;
  } finally {
    loading.value = false;
  }
};

function roundedRect(context, x, y, width, height, radius, color) {
  context.beginPath();
  context.moveTo(x + radius, y);
  context.lineTo(x + width - radius, y);
  context.quadraticCurveTo(x + width, y, x + width, y + radius);
  context.lineTo(x + width, y + height - radius);
  context.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
  context.lineTo(x + radius, y + height);
  context.quadraticCurveTo(x, y + height, x, y + height - radius);
  context.lineTo(x, y + radius);
  context.quadraticCurveTo(x, y, x + radius, y);
  context.closePath();
  context.setFillStyle(color);
  context.fill();
}

function drawQrCode(context, value, x, y, size) {
  const qr = QRCode.create(value, { errorCorrectionLevel: 'M' });
  const moduleCount = qr.modules.size;
  const cellSize = Math.floor(size / moduleCount);
  const actualSize = cellSize * moduleCount;
  const offsetX = x + Math.floor((size - actualSize) / 2);
  const offsetY = y + Math.floor((size - actualSize) / 2);

  context.setFillStyle('#FFFFFF');
  context.fillRect(x - 18, y - 18, size + 36, size + 36);
  context.setFillStyle('#13251D');
  for (let row = 0; row < moduleCount; row += 1) {
    for (let column = 0; column < moduleCount; column += 1) {
      if (qr.modules.get(row, column)) {
        context.fillRect(offsetX + column * cellSize, offsetY + row * cellSize, cellSize, cellSize);
      }
    }
  }
}

function drawPoster() {
  return new Promise((resolve) => {
    const context = uni.createCanvasContext(POSTER_CANVAS_ID);

    context.setFillStyle('#F4FBF7');
    context.fillRect(0, 0, POSTER_WIDTH, POSTER_HEIGHT);
    context.setFillStyle('#0F6B46');
    context.fillRect(0, 0, POSTER_WIDTH, 238);
    context.setFillStyle('#F2A65A');
    context.fillRect(0, 228, POSTER_WIDTH, 10);

    context.setTextAlign('center');
    context.setFillStyle('#FFFFFF');
    context.setFontSize(34);
    context.fillText('卓越商城', POSTER_WIDTH / 2, 72);
    context.setFontSize(48);
    context.fillText('好物一起分享', POSTER_WIDTH / 2, 140);
    context.setFontSize(24);
    context.fillText('扫码加入，开启品质生活', POSTER_WIDTH / 2, 190);

    roundedRect(context, 54, 274, 492, 470, 18, '#FFFFFF');
    drawQrCode(context, inviteUrl.value, 150, 316, 300);

    context.setFillStyle('#173D2D');
    context.setFontSize(28);
    context.fillText('长按识别或使用扫一扫', POSTER_WIDTH / 2, 670);
    context.setFillStyle('#678075');
    context.setFontSize(21);
    context.fillText('邀请码', 247, 713);
    context.setTextAlign('left');
    context.setFillStyle('#0F6B46');
    context.setFontSize(24);
    context.fillText(inviteCode.value, 303, 713);

    context.setTextAlign('center');
    context.setFillStyle('#73867D');
    context.setFontSize(20);
    context.fillText('卓越商城 · 品质好物 优享生活', POSTER_WIDTH / 2, 795);

    context.draw(false, () => resolve());
  });
}

function exportPoster() {
  return new Promise((resolve, reject) => {
    uni.canvasToTempFilePath({
      canvasId: POSTER_CANVAS_ID,
      width: POSTER_WIDTH,
      height: POSTER_HEIGHT,
      destWidth: POSTER_WIDTH * 2,
      destHeight: POSTER_HEIGHT * 2,
      quality: 1,
      success: ({ tempFilePath }) => resolve(tempFilePath),
      fail: reject
    });
  });
}

async function generatePoster() {
  if (!inviteUrl.value) {
    throw new Error('邀请链接未就绪');
  }
  await nextTick();
  await drawPoster();
  posterPath.value = await exportPoster();
  posterCode.value = inviteCode.value;
}

const share = async () => {
  if (!inviteCode.value) {
    await loadInvite();
  }
  if (!inviteCode.value || !inviteUrl.value) {
    uni.showToast({ title: '邀请码加载失败，请稍后重试', icon: 'none' });
    return;
  }

  posterVisible.value = true;
  if (posterPath.value && posterCode.value === inviteCode.value) return;

  posterGenerating.value = true;
  try {
    await generatePoster();
  } catch (error) {
    posterVisible.value = false;
    uni.showToast({ title: '海报生成失败，请稍后重试', icon: 'none' });
  } finally {
    posterGenerating.value = false;
  }
};

const copyCode = async () => {
  if (!inviteCode.value) return;
  await uni.setClipboardData({ data: inviteCode.value });
  uni.showToast({ title: '邀请码已复制', icon: 'none' });
};

const copyLink = async () => {
  if (!inviteUrl.value) return;
  await uni.setClipboardData({ data: inviteUrl.value });
  uni.showToast({ title: '邀请链接已复制', icon: 'none' });
};

const previewPoster = () => {
  if (!posterPath.value) return;
  uni.previewImage({ urls: [posterPath.value], current: posterPath.value });
};

const savePoster = () => {
  if (!posterPath.value) return;

  if (typeof document !== 'undefined') {
    const anchor = document.createElement('a');
    anchor.href = posterPath.value;
    anchor.download = `卓越商城邀请海报-${inviteCode.value}.png`;
    anchor.click();
    uni.showToast({ title: '海报已下载', icon: 'none' });
    return;
  }

  uni.saveImageToPhotosAlbum({
    filePath: posterPath.value,
    success: () => uni.showToast({ title: '海报已保存', icon: 'success' }),
    fail: (error) => {
      if (!String(error?.errMsg || '').includes('cancel')) {
        uni.showToast({ title: '保存失败，请检查相册权限', icon: 'none' });
      }
    }
  });
};

function confirmBind(inviterCode) {
  return new Promise((resolve) => {
    uni.showModal({
      title: '确认绑定上级',
      content: `绑定邀请码 ${inviterCode} 后不可更改，是否继续？`,
      confirmText: '确认绑定',
      success: ({ confirm }) => resolve(confirm)
    });
  });
}

async function bindByCode(value) {
  const code = extractInviteCode(value);
  if (!code) {
    uni.showToast({ title: '未识别到有效邀请码', icon: 'none' });
    return;
  }
  if (!(await confirmBind(code))) return;

  binding.value = true;
  try {
    const result = await userApi.bindInviter(code);
    manualBindVisible.value = false;
    manualInviteCode.value = '';
    const inviterName = result?.inviter?.nickname || result?.inviter?.invite_code || code;
    uni.showModal({
      title: result?.already_bound ? '已绑定' : '绑定成功',
      content: `你的直属上级：${inviterName}`,
      showCancel: false
    });
  } catch (error) {
    // The request layer displays the API error.
  } finally {
    binding.value = false;
  }
}

const scanInvite = () => {
  if (typeof window !== 'undefined') {
    openManualBind();
    return;
  }

  uni.scanCode({
    scanType: ['qrCode'],
    success: ({ result }) => bindByCode(result),
    fail: (error) => {
      if (!String(error?.errMsg || '').includes('cancel')) {
        uni.showToast({ title: '扫码失败，请重试', icon: 'none' });
      }
    }
  });
};

const openManualBind = () => {
  manualInviteCode.value = '';
  manualBindVisible.value = true;
};

const closeManualBind = () => {
  if (!binding.value) manualBindVisible.value = false;
};

const submitManualBind = () => bindByCode(manualInviteCode.value);
const closePoster = () => { posterVisible.value = false; };
const goBack = () => uni.navigateBack();

onShareAppMessage(() => ({
  title: '我在卓越商城发现了好物，邀请你一起加入',
  path: `/pages/login/index?invite_code=${encodeURIComponent(inviteCode.value)}`,
  imageUrl: posterPath.value || undefined
}));

onShow(() => {
  trackPageView('invite');
  loadInvite();
});

onPullDownRefresh(async () => {
  await loadInvite();
  uni.stopPullDownRefresh();
});
</script>

<style scoped>
@import '@/styles/elegant.css';

.invite-page {
  min-height: 100vh;
  padding-bottom: calc(48rpx + env(safe-area-inset-bottom));
  background: var(--bg);
}

.page-header {
  padding: calc(24rpx + env(safe-area-inset-top)) 32rpx 24rpx;
  border-bottom: 1rpx solid var(--border);
  background: var(--card);
}

.header-content,
.card-header,
.modal-header {
  display: flex;
  align-items: center;
}

.header-content { gap: 16rpx; }

.logo-mark {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 56rpx;
  height: 56rpx;
  border-radius: var(--radius-md);
  background: var(--primary);
  color: #FFFFFF;
  font-size: 24rpx;
  font-weight: 700;
}

.page-title {
  flex: 1;
  color: var(--text);
  font-size: var(--text-xl);
  font-weight: var(--font-bold);
}

.header-badge,
.update-badge {
  padding: 8rpx 14rpx;
  border-radius: var(--radius-md);
  background: var(--primary-bg);
  color: var(--primary-dark);
  font-size: 20rpx;
  font-weight: 600;
}

.invite-card {
  margin: 24rpx;
  padding: 40rpx 32rpx 30rpx;
  border-radius: var(--radius-xl);
  background: var(--primary-dark);
  box-shadow: var(--shadow-md);
}

.card-kicker,
.card-title,
.card-subtitle { display: block; }

.card-kicker {
  margin-bottom: 12rpx;
  color: #A7F3D0;
  font-size: 22rpx;
  font-weight: 600;
}

.card-title {
  color: #FFFFFF;
  font-size: 36rpx;
  font-weight: 700;
  line-height: 1.35;
}

.card-subtitle {
  margin-top: 12rpx;
  color: rgba(255, 255, 255, 0.76);
  font-size: 24rpx;
  line-height: 1.55;
}

.code-wrap {
  display: flex;
  align-items: center;
  min-height: 100rpx;
  margin: 32rpx 0 24rpx;
  padding: 0 24rpx;
  border: 1rpx solid rgba(255, 255, 255, 0.24);
  border-radius: var(--radius-lg);
  background: rgba(255, 255, 255, 0.1);
}

.code-label {
  margin-right: 20rpx;
  color: rgba(255, 255, 255, 0.7);
  font-size: 22rpx;
}

.code-value {
  flex: 1;
  min-width: 0;
  color: #FFFFFF;
  font-size: 34rpx;
  font-weight: 800;
}

.copy-btn {
  min-width: 88rpx;
  height: 56rpx;
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.16);
  color: #FFFFFF;
  font-size: 22rpx;
}

.action-row,
.poster-actions {
  display: flex;
  gap: 16rpx;
}

.action-btn {
  display: flex;
  flex: 1;
  align-items: center;
  justify-content: center;
  min-width: 0;
  height: 88rpx;
  border-radius: var(--radius-lg);
  font-size: 27rpx;
  font-weight: 700;
}

.action-btn.primary {
  background: #FFFFFF;
  color: var(--primary-dark);
}

.action-btn.secondary {
  border: 2rpx solid rgba(255, 255, 255, 0.55);
  background: transparent;
  color: #FFFFFF;
}

.action-btn[disabled],
.modal-action[disabled],
.bind-confirm[disabled] { opacity: 0.55; }

.manual-btn {
  height: 64rpx;
  margin: 12rpx auto 0;
  color: rgba(255, 255, 255, 0.8);
  font-size: 22rpx;
}

.stats-card {
  margin: 0 24rpx;
  padding: 32rpx;
  border: 1rpx solid var(--border-light);
  border-radius: var(--radius-xl);
  background: var(--card);
}

.card-header {
  justify-content: space-between;
  margin-bottom: 24rpx;
}

.section-title {
  color: var(--text);
  font-size: 30rpx;
  font-weight: 700;
}

.stats-grid,
.loading-stats {
  display: flex;
  align-items: center;
  gap: 16rpx;
}

.stats-grid {
  padding: 24rpx;
  border-radius: var(--radius-lg);
  background: var(--bg);
}

.stat-item {
  display: flex;
  flex: 1;
  flex-direction: column;
  align-items: center;
  gap: 8rpx;
}

.stat-value {
  color: var(--text);
  font-size: 40rpx;
  font-weight: 800;
}

.stat-label {
  color: var(--text-muted);
  font-size: 22rpx;
}

.stat-divider {
  width: 1rpx;
  height: 60rpx;
  background: var(--border-light);
}

.skeleton {
  flex: 1;
  height: 100rpx;
  border-radius: var(--radius-md);
  background: var(--border-light);
  animation: pulse 1.4s ease-in-out infinite;
}

.error-stats {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 24rpx;
}

.error-text {
  color: var(--text-muted);
  font-size: 26rpx;
}

.retry-text {
  height: 64rpx;
  color: var(--primary-dark);
  font-size: 24rpx;
  font-weight: 600;
}

.poster-canvas {
  position: fixed;
  top: 0;
  left: -10000px;
  pointer-events: none;
}

.modal-mask {
  position: fixed;
  z-index: 1000;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32rpx;
  background: rgba(10, 24, 18, 0.68);
}

.poster-modal,
.bind-modal {
  width: 100%;
  max-width: 620rpx;
  padding: 28rpx;
  border-radius: var(--radius-xl);
  background: var(--card);
  box-sizing: border-box;
}

.modal-header {
  justify-content: space-between;
  margin-bottom: 24rpx;
}

.modal-title {
  color: var(--text);
  font-size: 30rpx;
  font-weight: 700;
}

.close-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 64rpx;
  height: 64rpx;
  color: var(--text-muted);
  font-size: 44rpx;
  font-weight: 300;
}

.poster-preview {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 640rpx;
  overflow: hidden;
  border: 1rpx solid var(--border-light);
  border-radius: var(--radius-md);
  background: #F4FBF7;
}

.poster-image {
  width: 100%;
  height: auto;
}

.poster-loading {
  color: var(--text-muted);
  font-size: 24rpx;
}

.poster-actions { margin-top: 24rpx; }

.modal-action {
  flex: 1;
  min-width: 0;
  height: 76rpx;
  border: 1rpx solid var(--border);
  border-radius: var(--radius-md);
  background: var(--bg);
  color: var(--text-secondary);
  font-size: 24rpx;
  font-weight: 600;
}

.primary-action,
.bind-confirm {
  border: none;
  background: var(--primary-dark);
  color: #FFFFFF;
}

.invite-input {
  width: 100%;
  height: 92rpx;
  padding: 0 24rpx;
  border: 2rpx solid var(--border);
  border-radius: var(--radius-md);
  background: var(--bg);
  color: var(--text);
  font-size: 28rpx;
  box-sizing: border-box;
}

.bind-confirm {
  width: 100%;
  height: 84rpx;
  margin-top: 24rpx;
  border-radius: var(--radius-md);
  font-size: 27rpx;
  font-weight: 700;
}

@keyframes pulse {
  0%, 100% { opacity: 0.5; }
  50% { opacity: 1; }
}

@media (prefers-reduced-motion: reduce) {
  .skeleton { animation: none; }
}
</style>
