/**
 * request.js - 网络请求封装模块
 * 统一封装 wx.request，处理认证、错误提示和网络重试
 * 
 * 功能：
 * - 自动注入 Authorization Bearer token
 * - 401 响应自动清除登录态并跳转登录页
 * - >= 400 响应展示错误 Toast 提示
 * - 网络失败展示重试弹窗
 * 
 * 需求: 10.5 - 网络请求失败展示友好错误提示并提供重试选项
 */

var auth = require('./auth');

/**
 * 发起网络请求
 * @param {Object} options - 请求配置
 * @param {string} options.url - 请求路径（相对路径，会自动拼接 baseUrl）
 * @param {string} [options.method='GET'] - 请求方法
 * @param {Object} [options.data] - 请求数据
 * @param {Object} [options.header] - 自定义请求头（会与默认头合并）
 * @param {boolean} [options.showError=true] - 是否自动展示错误提示
 * @param {boolean} [options.showLoading=false] - 是否展示加载提示
 * @param {string} [options.loadingText='加载中...'] - 加载提示文案
 * @returns {Promise<Object>} 响应数据
 */
function request(options) {
  var app = getApp();
  var baseUrl = (app && app.globalData && app.globalData.baseUrl) || 'http://localhost:5000/api';
  var token = auth.getToken();

  // 默认配置
  var url = options.url || '';
  var method = options.method || 'GET';
  var data = options.data || {};
  var showError = options.showError !== false;
  var showLoading = options.showLoading || false;
  var loadingText = options.loadingText || '加载中...';

  // 构建完整 URL：如果已经是完整 URL 则不拼接 baseUrl
  var fullUrl = url.indexOf('http') === 0 ? url : baseUrl + url;

  // 构建请求头
  var header = {
    'Content-Type': 'application/json'
  };
  if (token) {
    header['Authorization'] = 'Bearer ' + token;
  }
  // 合并自定义请求头
  if (options.header) {
    for (var key in options.header) {
      if (options.header.hasOwnProperty(key)) {
        header[key] = options.header[key];
      }
    }
  }

  // 展示加载提示
  if (showLoading) {
    wx.showLoading({
      title: loadingText,
      mask: true
    });
  }

  return new Promise(function (resolve, reject) {
    wx.request({
      url: fullUrl,
      method: method,
      data: data,
      header: header,
      success: function (res) {
        if (showLoading) {
          wx.hideLoading();
        }

        var statusCode = res.statusCode;

        // 处理 401 未授权：清除登录态并跳转登录页
        if (statusCode === 401) {
          auth.clearToken();
          wx.showToast({
            title: '登录已过期，请重新登录',
            icon: 'none',
            duration: 2000
          });
          setTimeout(function () {
            wx.redirectTo({
              url: '/pages/login/login'
            });
          }, 1500);
          reject({
            code: 401,
            message: '登录已过期'
          });
          return;
        }

        // 处理 >= 400 的错误响应
        if (statusCode >= 400) {
          var errorMsg = (res.data && res.data.message) || '操作失败';
          if (showError) {
            wx.showToast({
              title: errorMsg,
              icon: 'none',
              duration: 2000
            });
          }
          reject({
            code: statusCode,
            message: errorMsg,
            errors: res.data && res.data.errors
          });
          return;
        }

        // 请求成功
        resolve(res.data);
      },
      fail: function (err) {
        if (showLoading) {
          wx.hideLoading();
        }

        // 网络失败：展示重试弹窗
        wx.showModal({
          title: '网络异常',
          content: '网络连接失败，请检查网络设置后重试',
          confirmText: '重试',
          cancelText: '取消',
          success: function (modalRes) {
            if (modalRes.confirm) {
              // 用户点击重试，重新发起请求
              request(options).then(resolve).catch(reject);
            } else {
              reject({
                code: -1,
                message: '网络连接失败'
              });
            }
          }
        });
      }
    });
  });
}

/**
 * GET 请求快捷方法
 * @param {string} url - 请求路径
 * @param {Object} [data] - 查询参数
 * @param {Object} [options] - 额外配置
 * @returns {Promise<Object>} 响应数据
 */
function get(url, data, options) {
  return request(Object.assign({
    url: url,
    method: 'GET',
    data: data
  }, options || {}));
}

/**
 * POST 请求快捷方法
 * @param {string} url - 请求路径
 * @param {Object} [data] - 请求体数据
 * @param {Object} [options] - 额外配置
 * @returns {Promise<Object>} 响应数据
 */
function post(url, data, options) {
  return request(Object.assign({
    url: url,
    method: 'POST',
    data: data
  }, options || {}));
}

/**
 * PUT 请求快捷方法
 * @param {string} url - 请求路径
 * @param {Object} [data] - 请求体数据
 * @param {Object} [options] - 额外配置
 * @returns {Promise<Object>} 响应数据
 */
function put(url, data, options) {
  return request(Object.assign({
    url: url,
    method: 'PUT',
    data: data
  }, options || {}));
}

/**
 * DELETE 请求快捷方法
 * @param {string} url - 请求路径
 * @param {Object} [data] - 请求数据
 * @param {Object} [options] - 额外配置
 * @returns {Promise<Object>} 响应数据
 */
function del(url, data, options) {
  return request(Object.assign({
    url: url,
    method: 'DELETE',
    data: data
  }, options || {}));
}

module.exports = {
  request: request,
  get: get,
  post: post,
  put: put,
  del: del
};
