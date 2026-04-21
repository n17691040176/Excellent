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
      headers: {
        'Content-Type': 'multipart/form-data'
      }
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

export const commissionApi = {
  config() {
    return request.get('/api/v1/admin/commission/config')
  },
  users(params) {
    return request.get('/api/v1/admin/commission/users', { params })
  },
  flows() {
    return request.get('/api/v1/admin/commission/flows')
  },
  withdraws() {
    return request.get('/api/v1/admin/withdraws')
  },
  approveWithdraw(id) {
    return request.patch(`/api/v1/admin/withdraws/${id}/approve`)
  },
  rejectWithdraw(id) {
    return request.patch(`/api/v1/admin/withdraws/${id}/reject`)
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
