import request from '@/api/request'

export const authApi = {
  adminLogin(data) {
    return request.post('/api/v1/auth/admin-login', data)
  },
  me() {
    return request.get('/api/v1/auth/me')
  },
  resetPassword(data) {
    return request.post('/api/v1/auth/reset-password', data)
  }
}
