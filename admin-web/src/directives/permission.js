import { hasPermission } from '@/utils/permission'
import { useUserStore } from '@/stores/user'

export default {
  install(app) {
    app.directive('permission', {
      mounted(el, binding) {
        const userStore = useUserStore()
        const ok = hasPermission(userStore.role, binding.value, userStore.permissions)
        if (!ok) {
          el.parentNode?.removeChild(el)
        }
      }
    })
  }
}
