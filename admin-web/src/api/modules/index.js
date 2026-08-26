import request from '@/api/request'

export const dashboardApi = {
  overview() {
    return request.get('/api/v1/admin/dashboard/overview')
  }
}

export const decorationApi = {
  mobileHome() {
    return request.get('/api/v1/admin/decorations/mobile-home')
  },
  updateMobileHome(payload) {
    return request.put('/api/v1/admin/decorations/mobile-home', { payload })
  },
  uploadMobileHomeImage(file) {
    const formData = new FormData()
    formData.append('file', file)
    return request.post('/api/v1/admin/decorations/mobile-home/upload-image', formData, {
      timeout: 60000
    })
  }
}

export const userApi = {
  list(params) {
    return request.get('/api/v1/admin/users', { params })
  },
  detail(id) {
    return request.get(`/api/v1/admin/users/${id}`)
  },
  legacyProfile(id) {
    return request.get(`/api/v1/admin/users/${id}/legacy-profile`)
  },
  updateStatus(id, data) {
    return request.patch(`/api/v1/admin/users/${id}/status`, data)
  },
  updateMemberLevel(id, data) {
    return request.patch(`/api/v1/admin/users/${id}/member-level`, data)
  },
  createAddress(id, data) {
    return request.post(`/api/v1/admin/users/${id}/addresses`, data)
  },
  updateAddress(id, addressId, data) {
    return request.put(`/api/v1/admin/users/${id}/addresses/${addressId}`, data)
  },
  deleteAddress(id, addressId) {
    return request.delete(`/api/v1/admin/users/${id}/addresses/${addressId}`)
  },
  setDefaultAddress(id, addressId) {
    return request.patch(`/api/v1/admin/users/${id}/addresses/${addressId}/default`)
  },
  deleteFavorite(id, productId) {
    return request.delete(`/api/v1/admin/users/${id}/favorites/${productId}`)
  },
  deleteFootprint(id, productId) {
    return request.delete(`/api/v1/admin/users/${id}/footprints/${productId}`)
  },
  deleteCartItem(id, itemId) {
    return request.delete(`/api/v1/admin/users/${id}/cart-items/${itemId}`)
  },
  inviteTree(id) {
    return request.get(`/api/v1/admin/users/${id}/invite-tree`)
  },
  powerBanks(id) {
    return request.get(`/api/v1/admin/users/${id}/power-banks`)
  },
  bindPowerBank(id, data) {
    return request.post(`/api/v1/admin/users/${id}/power-banks`, data)
  },
  updatePowerBank(id, powerBankId, data) {
    return request.patch(`/api/v1/admin/users/${id}/power-banks/${powerBankId}`, data)
  },
  profile() {
    return request.get('/api/v1/app/users/profile')
  },
  updateProfile(data) {
    return request.put('/api/v1/app/users/profile', data)
  }
}

export const teamApi = {
  current() {
    return request.get('/api/v1/app/teams/current')
  },
  members(id) {
    return request.get(`/api/v1/app/teams/${id}/members`)
  }
}

export const packageApi = {
  list() {
    return request.get('/api/v1/admin/packages')
  },
  create(data) {
    return request.post('/api/v1/admin/packages', data)
  },
  update(id, data) {
    return request.put(`/api/v1/admin/packages/${id}`, data)
  },
  updateStatus(id, data) {
    return request.patch(`/api/v1/admin/packages/${id}/status`, data)
  },
  remove(id) {
    return request.delete(`/api/v1/admin/packages/${id}`)
  },
  qualifications() {
    return request.get('/api/v1/app/packages/my-qualifications')
  }
}

export const orderApi = {
  list(params) {
    return request.get('/api/v1/admin/orders', { params })
  },
  detail(id) {
    return request.get(`/api/v1/admin/orders/${id}`)
  },
  markPaid(id) {
    return request.post(`/api/v1/admin/orders/${id}/pay`)
  },
  ship(id, data = {}) {
    return request.post(`/api/v1/admin/orders/${id}/ship`, null, { params: data })
  },
  confirm(id) {
    return request.post(`/api/v1/admin/orders/${id}/confirm`)
  },
  close(id) {
    return request.post(`/api/v1/admin/orders/${id}/close`)
  },
  refund(id) {
    return request.post(`/api/v1/admin/orders/${id}/refund`)
  }
}

export const commissionApi = {
  users(params) {
    return request.get('/api/v1/admin/commission/users', { params })
  },
  flows(params) {
    return request.get('/api/v1/admin/commission/flows', { params })
  },
  productRules(params) {
    return request.get('/api/v1/admin/commission/product-rules', { params })
  },
  withdraws(params) {
    return request.get('/api/v1/admin/withdraws', { params })
  },
  approveWithdraw(id, remark = '') {
    return request.patch(`/api/v1/admin/withdraws/${id}/approve`, { remark })
  },
  rejectWithdraw(id, remark = '') {
    return request.patch(`/api/v1/admin/withdraws/${id}/reject`, { remark })
  },
  payWithdraw(id) {
    return request.patch(`/api/v1/admin/withdraws/${id}/pay`)
  },
  withdrawConfig() {
    return request.get('/api/v1/admin/commission/withdraw-config')
  },
  updateWithdrawConfig(data) {
    return request.put('/api/v1/admin/commission/withdraw-config', data)
  },
  exportWithdraws(params) {
    return request.get('/api/v1/admin/withdraws/export', { params, responseType: 'blob' })
  }
}

export const earningRuleApi = {
  list(params) {
    return request.get('/api/v1/admin/earning-rules', { params })
  },
  create(data) {
    return request.post('/api/v1/admin/earning-rules', data)
  },
  update(id, data) {
    return request.put(`/api/v1/admin/earning-rules/${id}`, data)
  },
  updateStatus(id, data) {
    return request.patch(`/api/v1/admin/earning-rules/${id}/status`, data)
  },
  remove(id) {
    return request.delete(`/api/v1/admin/earning-rules/${id}`)
  }
}

export const regionApi = {
  agents(params) {
    return request.get('/api/v1/admin/region-agents/list', { params })
  },
  summary() {
    return request.get('/api/v1/admin/region-agents/summary')
  },
  createAgent(data) {
    return request.post('/api/v1/admin/region-agents', data)
  },
  updateAgent(id, data) {
    return request.put(`/api/v1/admin/region-agents/${id}`, data)
  },
  deleteAgent(id) {
    return request.delete(`/api/v1/admin/region-agents/${id}`)
  },
  dividends(params) {
    return request.get('/api/v1/admin/region-agents/dividends', { params })
  }
}

export const supplierApi = {
  list() {
    return request.get('/api/v1/admin/suppliers')
  },
  qualifications() {
    return request.get('/api/v1/admin/product-qualifications')
  },
  qualificationLedgers() {
    return request.get('/api/v1/admin/product-qualification-ledgers')
  },
  auditQualification(id, data) {
    return request.patch(`/api/v1/admin/product-qualifications/${id}/audit`, data)
  },
  mine() {
    return request.get('/api/v1/app/suppliers/my')
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
  powerBanks() {
    return request.get('/api/v1/app/assets/power-banks')
  }
}

export const productApi = {
  list(params) {
    return request.get('/api/v1/admin/products', { params })
  },
  uploadImage(file) {
    const formData = new FormData()
    formData.append('file', file)
    return request.post('/api/v1/admin/products/upload-image', formData, {
      timeout: 60000
    })
  },
  repurchase() {
    return request.get('/api/v1/admin/zones/repurchase/products')
  },
  selfOperated() {
    return request.get('/api/v1/admin/zones/self-operated/products')
  },
  hotSale() {
    return request.get('/api/v1/admin/zones/hot-sale/products')
  },
  localLife() {
    return request.get('/api/v1/admin/zones/local-life/services')
  },
  create(data) {
    return request.post('/api/v1/admin/products', data)
  },
  batchMerchandise(data) {
    return request.patch('/api/v1/admin/products/batch-merchandise', data)
  },
  batchStatus(data) {
    return request.patch('/api/v1/admin/products/batch-status', data)
  },
  update(id, data) {
    return request.put(`/api/v1/admin/products/${id}`, data)
  },
  submitReview(id) {
    return request.patch(`/api/v1/admin/products/${id}/submit-review`)
  },
  audit(id, data) {
    return request.patch(`/api/v1/admin/products/${id}/audit`, data)
  },
  updateStatus(id, data) {
    return request.patch(`/api/v1/admin/products/${id}/status`, data)
  },
  remove(id) {
    return request.delete(`/api/v1/admin/products/${id}`)
  },
  downloadImportTemplate() {
    return request.get('/api/v1/admin/products/import-template', {
      responseType: 'blob'
    })
  },
  importExcel(file) {
    const formData = new FormData()
    formData.append('file', file)
    return request.post('/api/v1/admin/products/import', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
  },
  zoneConfig(id) {
    return request.get(`/api/v1/admin/products/${id}/zone-config`)
  },
  updateZoneConfig(id, data) {
    return request.put(`/api/v1/admin/products/${id}/zone-config`, data)
  }
}

export const localLifeApi = {
  merchants() {
    return request.get('/api/v1/admin/local-life/merchants')
  },
  createMerchant(data) {
    return request.post('/api/v1/admin/local-life/merchants', data)
  },
  updateMerchant(id, data) {
    return request.put(`/api/v1/admin/local-life/merchants/${id}`, data)
  },
  removeMerchant(id) {
    return request.delete(`/api/v1/admin/local-life/merchants/${id}`)
  },
  stores() {
    return request.get('/api/v1/admin/local-life/stores')
  },
  createStore(data) {
    return request.post('/api/v1/admin/local-life/stores', data)
  },
  updateStore(id, data) {
    return request.put(`/api/v1/admin/local-life/stores/${id}`, data)
  },
  removeStore(id) {
    return request.delete(`/api/v1/admin/local-life/stores/${id}`)
  },
  services() {
    return request.get('/api/v1/admin/local-life/services')
  },
  createService(data) {
    return request.post('/api/v1/admin/local-life/services', data)
  },
  updateService(id, data) {
    return request.put(`/api/v1/admin/local-life/services/${id}`, data)
  },
  removeService(id) {
    return request.delete(`/api/v1/admin/local-life/services/${id}`)
  },
  orders() {
    return request.get('/api/v1/admin/local-life/orders')
  },
  verifyOrder(data) {
    return request.post('/api/v1/admin/local-life/orders/verify', data)
  },
  rules() {
    return request.get('/api/v1/admin/local-life/commission-rules')
  },
  createRule(data) {
    return request.post('/api/v1/admin/local-life/commission-rules', data)
  },
  updateRule(id, data) {
    return request.put(`/api/v1/admin/local-life/commission-rules/${id}`, data)
  },
  removeRule(id) {
    return request.delete(`/api/v1/admin/local-life/commission-rules/${id}`)
  },
  deviceRevenues() {
    return request.get('/api/v1/admin/local-life/device-revenues')
  },
  adRevenues() {
    return request.get('/api/v1/admin/local-life/ad-revenues')
  }
}

// 邀请裂变管理 API
export const inviteApi = {
  summary() {
    return request.get('/api/v1/admin/invites/summary')
  },
  users(params) {
    return request.get('/api/v1/admin/invites/users', { params })
  },
  records(params) {
    return request.get('/api/v1/admin/invites/records', { params })
  },
  tree(userId) {
    return request.get(`/api/v1/admin/invites/tree/${userId}`)
  }
}

// 快递物流管理 API
export const shipmentApi = {
  list(params) {
    return request.get('/api/v1/admin/commerce/shipments', { params })
  },
  detail(orderId) {
    return request.get(`/api/v1/admin/commerce/shipments/${orderId}`)
  },
  updateTracking(orderId, data) {
    return request.post(`/api/v1/admin/commerce/shipments/${orderId}/update-tracking`, null, { params: data })
  }
}

// 收藏管理 API
export const favoriteApi = {
  list(params) {
    return request.get('/api/v1/admin/commerce/favorites', { params })
  },
  remove(favoriteId) {
    return request.delete(`/api/v1/admin/commerce/favorites/${favoriteId}`)
  }
}

// 足迹管理 API
export const footprintApi = {
  list(params) {
    return request.get('/api/v1/admin/commerce/footprints', { params })
  },
  remove(footprintId) {
    return request.delete(`/api/v1/admin/commerce/footprints/${footprintId}`)
  }
}

// 商品分类管理 API
export const categoryApi = {
  list(params) {
    return request.get('/api/v1/admin/categories', { params })
  },
  create(data) {
    return request.post('/api/v1/admin/categories', data)
  },
  update(id, data) {
    return request.put(`/api/v1/admin/categories/${id}`, data)
  },
  updateStatus(id, data) {
    return request.patch(`/api/v1/admin/categories/${id}/status`, data)
  },
  remove(id) {
    return request.delete(`/api/v1/admin/categories/${id}`)
  },
  delete(id) {
    return request.delete(`/api/v1/admin/categories/${id}`)
  }
}

// 后台权限管理 API
export const permissionApi = {
  options() {
    return request.get('/api/v1/admin/permissions/options')
  },
  admins() {
    return request.get('/api/v1/admin/permissions/admins')
  },
  detail(userId) {
    return request.get(`/api/v1/admin/permissions/admins/${userId}`)
  },
  update(userId, data) {
    return request.put(`/api/v1/admin/permissions/admins/${userId}`, data)
  }
}

// 动态角色管理 API
export const roleApi = {
  options() {
    return request.get('/api/v1/admin/roles/options')
  },
  list(params = {}) {
    return request.get('/api/v1/admin/roles', { params })
  },
  detail(id) {
    return request.get(`/api/v1/admin/roles/${id}`)
  },
  create(data) {
    return request.post('/api/v1/admin/roles', data)
  },
  update(id, data) {
    return request.put(`/api/v1/admin/roles/${id}`, data)
  },
  remove(id) {
    return request.delete(`/api/v1/admin/roles/${id}`)
  }
}

// 管理员账号 API
export const adminAccountApi = {
  list(params = {}) {
    return request.get('/api/v1/admin/admins', { params })
  },
  candidates(params = {}) {
    return request.get('/api/v1/admin/admins/candidates', { params })
  },
  teams() {
    return request.get('/api/v1/admin/admins/teams')
  },
  create(data) {
    return request.post('/api/v1/admin/admins', data)
  },
  promote(data) {
    return request.post('/api/v1/admin/admins/promote', data)
  },
  update(id, data) {
    return request.put(`/api/v1/admin/admins/${id}`, data)
  },
  updateStatus(id, data) {
    return request.patch(`/api/v1/admin/admins/${id}/status`, data)
  },
  resetPassword(id, data) {
    return request.post(`/api/v1/admin/admins/${id}/reset-password`, data)
  },
  demote(id) {
    return request.post(`/api/v1/admin/admins/${id}/demote`)
  }
}

export const adminProfileApi = {
  get() {
    return request.get('/api/v1/admin/profile')
  },
  update(data) {
    return request.put('/api/v1/admin/profile', data)
  },
  changePassword(data) {
    return request.post('/api/v1/admin/profile/password', data)
  }
}
