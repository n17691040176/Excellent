import { BrowserQRCodeReader } from '@zxing/browser';
import { DecodeHintType } from '@zxing/library';

const MAX_DECODE_DIMENSION = 2048;
const CROP_RATIOS = [1, 0.85, 0.65, 0.45];

function cancelledError() {
  const error = new Error('未选择二维码图片');
  error.code = 'SCAN_CANCELLED';
  return error;
}

function chooseQrImage() {
  return new Promise((resolve, reject) => {
    const input = document.createElement('input');
    let settled = false;
    let focusTimer = null;

    const handleWindowFocus = () => {
      clearTimeout(focusTimer);
      focusTimer = setTimeout(() => {
        if (!settled && !input.files?.length) finish(reject, cancelledError());
      }, 500);
    };

    const cleanup = () => {
      clearTimeout(focusTimer);
      window.removeEventListener('focus', handleWindowFocus);
      input.remove();
    };
    const finish = (callback, value) => {
      if (settled) return;
      settled = true;
      cleanup();
      callback(value);
    };

    input.type = 'file';
    input.accept = 'image/*';
    input.setAttribute('capture', 'environment');
    input.style.display = 'none';
    input.addEventListener('change', () => {
      const file = input.files?.[0];
      if (file) finish(resolve, file);
      else finish(reject, cancelledError());
    }, { once: true });
    input.addEventListener('cancel', () => finish(reject, cancelledError()), { once: true });

    document.body.appendChild(input);
    window.addEventListener('focus', handleWindowFocus);
    input.click();
  });
}

function loadImage(sourceUrl) {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = () => reject(new Error('二维码图片读取失败'));
    image.src = sourceUrl;
  });
}

function createDecodeCanvas(image, cropRatio) {
  const sourceWidth = image.naturalWidth || image.width;
  const sourceHeight = image.naturalHeight || image.height;
  const cropWidth = Math.max(1, Math.round(sourceWidth * cropRatio));
  const cropHeight = Math.max(1, Math.round(sourceHeight * cropRatio));
  const sourceX = Math.round((sourceWidth - cropWidth) / 2);
  const sourceY = Math.round((sourceHeight - cropHeight) / 2);
  const scale = Math.min(1, MAX_DECODE_DIMENSION / Math.max(cropWidth, cropHeight));
  const targetWidth = Math.max(1, Math.round(cropWidth * scale));
  const targetHeight = Math.max(1, Math.round(cropHeight * scale));
  const canvas = document.createElement('canvas');
  const context = canvas.getContext('2d', { willReadFrequently: true });

  if (!context) throw new Error('当前环境不支持二维码图片处理');

  canvas.width = targetWidth;
  canvas.height = targetHeight;
  context.drawImage(
    image,
    sourceX,
    sourceY,
    cropWidth,
    cropHeight,
    0,
    0,
    targetWidth,
    targetHeight
  );
  return canvas;
}

function decodeQrImage(image) {
  const hints = new Map();
  hints.set(DecodeHintType.TRY_HARDER, true);
  const reader = new BrowserQRCodeReader(hints);
  let lastError;

  for (const cropRatio of CROP_RATIOS) {
    try {
      return reader.decodeFromCanvas(createDecodeCanvas(image, cropRatio)).getText();
    } catch (error) {
      lastError = error;
    }
  }

  throw lastError || new Error('未识别到二维码');
}

export async function scanQrCodeFromImage() {
  if (typeof document === 'undefined') {
    throw new Error('当前环境不支持图片扫码');
  }

  const file = await chooseQrImage();
  const objectUrl = URL.createObjectURL(file);
  try {
    const image = await loadImage(objectUrl);
    return decodeQrImage(image);
  } catch (error) {
    if (error?.code === 'SCAN_CANCELLED') throw error;
    const scanError = new Error('未识别到二维码，请重新拍摄清晰完整的二维码');
    scanError.cause = error;
    throw scanError;
  } finally {
    URL.revokeObjectURL(objectUrl);
  }
}
