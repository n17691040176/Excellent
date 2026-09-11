import { ref, onUnmounted } from 'vue';
import { onShow, onHide } from '@dcloudio/uni-app';
import { cityPartnerApi } from '@/api/modules';

export function useCityPartnerAvailability() {
  const enabled = ref(false);
  let timer;
  let generation = 0;
  async function refresh() {
    const current = ++generation;
    try {
      const result = await cityPartnerApi.availability();
      if (current === generation) enabled.value = result.enabled === true;
    } catch {
      if (current === generation) enabled.value = false;
    }
    return enabled.value;
  }
  function stop() {
    globalThis.clearInterval(timer);
    ++generation;
    enabled.value = false;
  }
  onShow(() => {
    stop();
    refresh();
    // Refresh while the page is visible, including an admin switch elsewhere.
    timer = globalThis.setInterval(refresh, 15000);
  });
  onHide(stop);
  onUnmounted(stop);
  return { enabled, refresh };
}
