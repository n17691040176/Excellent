import { BrowserQRCodeReader } from '@zxing/browser';

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

export async function scanQrCodeFromImage() {
  if (typeof document === 'undefined') {
    throw new Error('当前环境不支持图片扫码');
  }

  const file = await chooseQrImage();
  const objectUrl = URL.createObjectURL(file);
  try {
    const image = await loadImage(objectUrl);
    const result = await new BrowserQRCodeReader().decodeFromImageElement(image);
    return result.getText();
  } catch (error) {
    if (error?.code === 'SCAN_CANCELLED') throw error;
    const scanError = new Error('未识别到二维码，请重新拍摄清晰完整的二维码');
    scanError.cause = error;
    throw scanError;
  } finally {
    URL.revokeObjectURL(objectUrl);
  }
}
