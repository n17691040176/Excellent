import request from './request';

export const authApi = {
  login(data) {
    return request.post('/api/v1/auth/login', data);
  },
  sendLoginCode(data) {
    return request.post('/api/v1/auth/send-login-code', data, { hideLoading: true });
  },
  loginByCode(data) {
    return request.post('/api/v1/auth/login-by-code', data);
  },
  // 一键登录（阿里云SDK方案）
  oneClickLogin(data) {
    return request.post('/api/v1/auth/one-click-login', data);
  },
  // 一键登录新用户注册
  oneClickRegister(data) {
    return request.post('/api/v1/auth/one-click-register', data);
  },
  // App传递手机号免注册登录
  appLogin(data) {
    return request.post('/api/v1/auth/app-login', data);
  },
  me() {
    return request.get('/api/v1/auth/me', { hideLoading: true });
  }
};

export const homeApi = {
  repurchase() {
    return request.get('/api/v1/app/zones/repurchase/products', { hideLoading: true });
  },
  hotSale() {
    return request.get('/api/v1/app/zones/hot-sale/products', { hideLoading: true });
  },
  decoration() {
    return request.get('/api/v1/app/decorations/mobile-home', { hideLoading: true });
  }
};

export const packageApi = {
  list(params = {}) {
    return request.get('/api/v1/app/products', { params, hideLoading: true });
  },
  detail(id) {
    return request.get(`/api/v1/app/products/${id}`);
  }
};

export const userApi = {
  profile() {
    return request.get('/api/v1/app/users/profile', { hideLoading: true });
  },
  inviteCode() {
    return request.get('/api/v1/app/users/invite-code', { hideLoading: true });
  },
  inviteRecords(params = {}) {
    return request.get('/api/v1/app/users/invite-records', { params, hideLoading: true });
  },
  teamSummary() {
    return request.get('/api/v1/app/users/team-summary', { hideLoading: true });
  }
};

export const assetApi = {
  summary() {
    return request.get('/api/v1/app/assets/summary', { hideLoading: true });
  },
  powerBanks() {
    return request.get('/api/v1/app/assets/power-banks', { hideLoading: true });
  },
  detail(type = 'balance', params = {}) {
    return request.get(`/api/v1/app/assets/${type}`, { params, hideLoading: true });
  },
  ledgers(type = 'balance', params = {}) {
    return request.get(`/api/v1/app/assets/${type}/ledgers`, { params, hideLoading: true });
  }
};

export const commissionApi = {
  summary() {
    return request.get('/api/v1/app/commission/summary', { hideLoading: true });
  },
  flows(params = {}) {
    return request.get('/api/v1/app/commission/flows', { params, hideLoading: true });
  },
  withdraws(params = {}) {
    return request.get('/api/v1/app/withdraws', { params, hideLoading: true });
  },
  createWithdraw(data) {
    return request.post('/api/v1/app/withdraws', data);
  }
};

export const orderApi = {
  create(data) {
    return request.post('/api/v1/app/orders', data);
  },
  preview(data) {
    return request.post('/api/v1/app/orders/preview', data, { hideLoading: true });
  },
  list(params = {}) {
    return request.get('/api/v1/app/orders', { params, hideLoading: true });
  },
  detail(id) {
    return request.get(`/api/v1/app/orders/${id}`);
  },
  confirm(id) {
    return request.post(`/api/v1/app/orders/${id}/confirm`, {});
  },
  cancel(id) {
    return request.post(`/api/v1/app/orders/${id}/cancel`, {});
  },
  refund(id) {
    return request.post(`/api/v1/app/orders/${id}/refund`, {});
  },
  payDemo(id) {
    return request.post(`/api/v1/app/orders/${id}/pay-demo`, {});
  },
  pay(id, data) {
    return request.post(`/api/v1/app/orders/${id}/pay`, data);
  },
  syncPayment(id, outTradeNo = '') {
    return request.post(`/api/v1/app/orders/${id}/payment-status`, {
      out_trade_no: outTradeNo
    }, { hideLoading: true });
  }
};

export const addressApi = {
  list() {
    return request.get('/api/v1/app/addresses', { hideLoading: true });
  },
  create(data) {
    return request.post('/api/v1/app/addresses', data);
  },
  update(id, data) {
    return request.put(`/api/v1/app/addresses/${id}`, data);
  },
  remove(id) {
    return request.delete(`/api/v1/app/addresses/${id}`);
  },
  setDefault(id) {
    return request.patch(`/api/v1/app/addresses/${id}/default`, {});
  }
};

export const commerceApi = {
  productStatus(productId) {
    return request.get(`/api/v1/app/commerce/products/${productId}/status`, { hideLoading: true });
  },
  favorite(productId) {
    return request.post(`/api/v1/app/commerce/products/${productId}/favorite`, {});
  },
  unfavorite(productId) {
    return request.delete(`/api/v1/app/commerce/products/${productId}/favorite`);
  },
  recordFootprint(productId) {
    return request.post(`/api/v1/app/commerce/products/${productId}/footprint`, {}, { hideLoading: true });
  },
  favorites(params = {}) {
    return request.get('/api/v1/app/commerce/favorites', { params, hideLoading: true });
  },
  removeFavorite(productId) {
    return request.delete(`/api/v1/app/commerce/favorites/${productId}`);
  },
  footprints(params = {}) {
    return request.get('/api/v1/app/commerce/footprints', { params, hideLoading: true });
  },
  removeFootprint(productId) {
    return request.delete(`/api/v1/app/commerce/footprints/${productId}`);
  },
  cart() {
    return request.get('/api/v1/app/commerce/cart', { hideLoading: true });
  },
  addCartItem(data) {
    return request.post('/api/v1/app/commerce/cart/items', data);
  },
  updateCartItem(id, data) {
    return request.patch(`/api/v1/app/commerce/cart/items/${id}`, data);
  },
  removeCartItem(id) {
    return request.delete(`/api/v1/app/commerce/cart/items/${id}`);
  },
  checkoutCart(data) {
    return request.post('/api/v1/app/commerce/cart/checkout', data);
  },
  shipments() {
    return request.get('/api/v1/app/commerce/shipments', { hideLoading: true });
  },
  shipmentDetail(orderId) {
    return request.get(`/api/v1/app/commerce/shipments/${orderId}`, { hideLoading: true });
  }
};

export const localLifeApi = {
  services(params = {}) {
    return request.get('/api/v1/app/local-life/services', {
      params,
      hideLoading: true
    });
  },
  serviceDetail(id) {
    return request.get(`/api/v1/app/local-life/services/${id}`);
  },
  orders(params = {}) {
    return request.get('/api/v1/app/local-life/orders', {
      params,
      hideLoading: true
    });
  }
};

export const categoryApi = {
  list() {
    return request.get('/api/v1/app/categories', { hideLoading: true });
  }
};
