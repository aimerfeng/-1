/**
 * auth.js - 认证工具模块
 * 封装登录态检查、token 存取等认证相关功能
 * 
 * 注意：getApp() 是微信小程序全局函数，无需额外引入
 */

/**
 * 检查用户是否已登录
 * @returns {boolean} 是否已登录
 */
function isLoggedIn() {
  // 先检查本地存储（最可靠的来源）
  var token = wx.getStorageSync('token');
  if (token) {
    // 确保 globalData 也同步
    var app = getApp();
    if (app && app.globalData && !app.globalData.isLoggedIn) {
      var userInfo = wx.getStorageSync('userInfo');
      app.globalData.token = token;
      app.globalData.userInfo = userInfo || null;
      app.globalData.isLoggedIn = true;
    }
    return true;
  }
  // 再检查 globalData
  var app = getApp();
  if (app && app.globalData && app.globalData.isLoggedIn && app.globalData.token) {
    return true;
  }
  return false;
}

/**
 * 获取当前存储的 token
 * @returns {string} JWT token，未登录时返回空字符串
 */
function getToken() {
  // 优先从本地存储获取（最可靠）
  var token = wx.getStorageSync('token') || '';
  if (token) return token;
  // 降级从 globalData 获取
  var app = getApp();
  if (app && app.globalData && app.globalData.token) {
    return app.globalData.token;
  }
  return '';
}

/**
 * 保存 token 到本地存储和全局状态
 * @param {string} token - JWT token
 * @param {Object} [userInfo] - 用户信息（可选）
 */
function setToken(token, userInfo) {
  var app = getApp();
  if (app && app.setLoginState) {
    app.setLoginState(token, userInfo || app.globalData.userInfo);
  } else {
    // 降级直接操作存储
    wx.setStorageSync('token', token);
    if (userInfo) {
      wx.setStorageSync('userInfo', userInfo);
    }
  }
}

/**
 * 清除登录态
 */
function clearToken() {
  var app = getApp();
  if (app && app.clearLoginState) {
    app.clearLoginState();
  } else {
    wx.removeStorageSync('token');
    wx.removeStorageSync('userInfo');
  }
}

/**
 * 获取当前用户信息
 * @returns {Object|null} 用户信息对象
 */
function getUserInfo() {
  var app = getApp();
  if (app && app.globalData && app.globalData.userInfo) {
    return app.globalData.userInfo;
  }
  return wx.getStorageSync('userInfo') || null;
}

/**
 * 获取当前用户角色
 * @returns {string|null} 用户角色：'buyer'、'supplier'、'admin' 或 null
 */
function getUserRole() {
  var userInfo = getUserInfo();
  return userInfo ? userInfo.role : null;
}

/**
 * 要求用户登录，未登录时自动跳转到登录页
 * @param {string} [redirectUrl] - 登录成功后的回跳页面路径（可选）
 * @returns {boolean} 是否已登录
 */
function requireAuth(redirectUrl) {
  if (isLoggedIn()) {
    return true;
  }
  // 构建登录页 URL，附带回跳参数
  var loginUrl = '/pages/login/login';
  if (redirectUrl) {
    loginUrl += '?redirect=' + encodeURIComponent(redirectUrl);
  }
  wx.navigateTo({
    url: loginUrl
  });
  return false;
}

module.exports = {
  isLoggedIn: isLoggedIn,
  getToken: getToken,
  setToken: setToken,
  clearToken: clearToken,
  getUserInfo: getUserInfo,
  getUserRole: getUserRole,
  requireAuth: requireAuth
};
