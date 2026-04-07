import request from './request'

export const authApi = {
  login(data) {
    return request.post('/api/v1/auth/login', data)
  },
  register(data) {
    return request.post('/api/v1/auth/register', data)
  },
  me() {
    return request.get('/api/v1/auth/me', { hideLoading: true })
  },
  resetPassword(data) {
    return request.post('/api/v1/auth/reset-password', data)
  }
}

export const homeApi = {
  repurchase() {
    return request.get('/api/v1/app/zones/repurchase/products')
  },
  selfOperated() {
    return request.get('/api/v1/app/zones/self-operated/products')
  },
  hotSale() {
    return request.get('/api/v1/app/zones/hot-sale/products')
  },
  decoration() {
    return request.get('/api/v1/app/decorations/mobile-home', { hideLoading: true })
  }
}

export const productApi = {
  detail(id) {
    return request.get(`/api/v1/app/products/${id}`)
  }
}

export const packageApi = {
  list() {
    return request.get('/api/v1/app/packages')
  },
  detail(id) {
    return request.get(`/api/v1/app/packages/${id}`)
  },
  qualifications() {
    return request.get('/api/v1/app/packages/my-qualifications')
  },
  createOrder(id, data) {
    return request.post(`/api/v1/app/packages/${id}/orders`, data)
  }
}

export const userApi = {
  profile() {
    return request.get('/api/v1/app/users/profile')
  },
  updateProfile(data) {
    return request.put('/api/v1/app/users/profile', data)
  },
  inviteCode() {
    return request.get('/api/v1/app/users/invite-code', { hideLoading: true })
  },
  inviteRecords() {
    return request.get('/api/v1/app/users/invite-records')
  },
  teamSummary() {
    return request.get('/api/v1/app/users/team-summary', { hideLoading: true })
  }
}

export const teamApi = {
  current() {
    return request.get('/api/v1/app/teams/current')
  },
  create(data) {
    return request.post('/api/v1/app/teams', data)
  },
  update(id, data) {
    return request.put(`/api/v1/app/teams/${id}`, data)
  },
  dissolve(id) {
    return request.delete(`/api/v1/app/teams/${id}`)
  },
  members(id) {
    return request.get(`/api/v1/app/teams/${id}/members`)
  },
  join(id) {
    return request.post(`/api/v1/app/teams/${id}/join`)
  },
  updateRole(teamId, userId, data) {
    return request.patch(`/api/v1/app/teams/${teamId}/members/${userId}/role`, data)
  },
  removeMember(teamId, userId) {
    return request.delete(`/api/v1/app/teams/${teamId}/members/${userId}`)
  }
}

export const commissionApi = {
  summary() {
    return request.get('/api/v1/app/commission/summary')
  },
  flows() {
    return request.get('/api/v1/app/commission/flows')
  },
  withdraws() {
    return request.get('/api/v1/app/withdraws')
  },
  createWithdraw(data) {
    return request.post('/api/v1/app/withdraws', data)
  }
}

export const assetApi = {
  summary() {
    return request.get('/api/v1/app/assets/summary')
  },
  detail(type) {
    return request.get(`/api/v1/app/assets/${type}`)
  },
  ledgers(type) {
    return request.get(`/api/v1/app/assets/${type}/ledgers`)
  },
  signin() {
    return request.post('/api/v1/app/assets/signin')
  },
  transferPoints(data) {
    return request.post('/api/v1/app/assets/points/transfer', data)
  }
}

export const addressApi = {
  list() {
    return request.get('/api/v1/app/addresses')
  },
  create(data) {
    return request.post('/api/v1/app/addresses', data)
  },
  update(id, data) {
    return request.put(`/api/v1/app/addresses/${id}`, data)
  },
  remove(id) {
    return request.delete(`/api/v1/app/addresses/${id}`)
  },
  setDefault(id) {
    return request.patch(`/api/v1/app/addresses/${id}/default`)
  }
}

export const orderApi = {
  create(data) {
    return request.post('/api/v1/app/orders', data)
  },
  list() {
    return request.get('/api/v1/app/orders')
  },
  detail(id) {
    return request.get(`/api/v1/app/orders/${id}`)
  },
  confirm(id) {
    return request.post(`/api/v1/app/orders/${id}/confirm`)
  },
  cancel(id) {
    return request.post(`/api/v1/app/orders/${id}/cancel`)
  },
  payDemo(id) {
    return request.post(`/api/v1/app/orders/${id}/pay-demo`)
  }
}

export const localLifeApi = {
  merchants() {
    return request.get('/api/v1/app/local-life/merchants')
  },
  merchantDetail(id) {
    return request.get(`/api/v1/app/local-life/merchants/${id}`)
  },
  stores(merchantId) {
    return request.get(`/api/v1/app/local-life/merchants/${merchantId}/stores`)
  },
  services(merchantId) {
    return request.get('/api/v1/app/local-life/services', {
      params: merchantId ? { merchant_id: merchantId } : {},
      hideLoading: true
    })
  },
  serviceDetail(id) {
    return request.get(`/api/v1/app/local-life/services/${id}`)
  },
  createOrder(data) {
    return request.post('/api/v1/app/local-life/orders', data)
  },
  orders() {
    return request.get('/api/v1/app/local-life/orders')
  },
  orderDetail(id) {
    return request.get(`/api/v1/app/local-life/orders/${id}`)
  },
  revenueSummary() {
    return request.get('/api/v1/app/local-life/revenue-summary')
  }
}
