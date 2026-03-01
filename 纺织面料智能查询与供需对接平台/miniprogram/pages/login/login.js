/**
 * pages/login/login.js - 登录与注册页面逻辑
 * 
 * 功能：
 * - 手机号 + 密码登录
 * - 手机号 + 验证码注册
 * - 微信一键登录（wx.login）
 * - 首次登录角色选择弹窗
 * - 表单即时校验与 Toast 反馈
 * 
 * 需求: 1.1, 1.2, 1.5, 10.4
 */

var request = require('../../utils/request');

/** 手机号正则：1开头、第二位3-9、共11位数字 */
var PHONE_REGEX = /^1[3-9]\d{9}$/;

Page({
  data: {
    // Tab 状态
    activeTab: 'login', // 'login' | 'register'

    // 登录表单
    loginPhone: '',
    loginPassword: '',
    phoneError: '',
    showPassword: false,
    loginLoading: false,

    // 注册表单
    regPhone: '',
    regCode: '',
    regPassword: '',
    regPhoneError: '',
    showRegPassword: false,
    regLoading: false,
    regRole: '', // 'buyer' | 'supplier'

    // 验证码倒计时
    codeCountdown: 0,

    // 微信登录
    wxLoginLoading: false,

    // 角色选择弹窗
    showRoleModal: false,
    selectedRole: '',
    companyName: '',
    contactName: '',
    roleLoading: false,

    // 临时存储（微信登录后的 token 和用户信息）
    _tempToken: '',
    _tempUserInfo: null,

    // 登录后回跳地址
    redirectUrl: ''
  },

  /**
   * 计算属性：是否可以登录
   */
  get canLogin() {
    return this.data.loginPhone && this.data.loginPassword && !this.data.phoneError;
  },

  /**
   * 计算属性：是否可以注册
   */
  get canRegister() {
    return this.data.regPhone && this.data.regCode && this.data.regPassword && this.data.regRole && !this.data.regPhoneError;
  },

  /**
   * 计算属性：是否可以发送验证码
   */
  get canSendCode() {
    return PHONE_REGEX.test(this.data.regPhone) && this.data.codeCountdown === 0;
  },

  onLoad: function (options) {
    if (options && options.redirect) {
      this.setData({ redirectUrl: decodeURIComponent(options.redirect) });
    }
    // 更新计算属性
    this._updateComputed();
  },

  onUnload: function () {
    // 清除倒计时
    if (this._codeTimer) {
      clearInterval(this._codeTimer);
      this._codeTimer = null;
    }
  },

  // ============================================================
  // Tab 切换
  // ============================================================

  switchTab: function (e) {
    var tab = e.currentTarget.dataset.tab;
    if (tab !== this.data.activeTab) {
      this.setData({
        activeTab: tab,
        phoneError: '',
        regPhoneError: ''
      });
    }
  },

  // ============================================================
  // 登录表单事件
  // ============================================================

  onLoginPhoneInput: function (e) {
    var value = e.detail.value;
    var update = { loginPhone: value };
    // 即时校验：输入过程中清除错误
    if (this.data.phoneError && value.length < 11) {
      update.phoneError = '';
    }
    // 输入满11位时自动校验
    if (value.length === 11) {
      if (!PHONE_REGEX.test(value)) {
        update.phoneError = '请输入正确的手机号码';
      } else {
        update.phoneError = '';
      }
    }
    this.setData(update);
    this._updateComputed();
  },

  onLoginPhoneBlur: function () {
    var phone = this.data.loginPhone;
    if (phone && !PHONE_REGEX.test(phone)) {
      this.setData({ phoneError: '请输入正确的手机号码' });
    }
    this._updateComputed();
  },

  clearLoginPhone: function () {
    this.setData({ loginPhone: '', phoneError: '' });
    this._updateComputed();
  },

  onLoginPasswordInput: function (e) {
    this.setData({ loginPassword: e.detail.value });
    this._updateComputed();
  },

  togglePasswordVisibility: function () {
    this.setData({ showPassword: !this.data.showPassword });
  },

  // ============================================================
  // 注册表单事件
  // ============================================================

  onRegPhoneInput: function (e) {
    var value = e.detail.value;
    var update = { regPhone: value };
    if (this.data.regPhoneError && value.length < 11) {
      update.regPhoneError = '';
    }
    if (value.length === 11) {
      if (!PHONE_REGEX.test(value)) {
        update.regPhoneError = '请输入正确的手机号码';
      } else {
        update.regPhoneError = '';
      }
    }
    this.setData(update);
    this._updateComputed();
  },

  onRegPhoneBlur: function () {
    var phone = this.data.regPhone;
    if (phone && !PHONE_REGEX.test(phone)) {
      this.setData({ regPhoneError: '请输入正确的手机号码' });
    }
    this._updateComputed();
  },

  clearRegPhone: function () {
    this.setData({ regPhone: '', regPhoneError: '' });
    this._updateComputed();
  },

  onRegCodeInput: function (e) {
    this.setData({ regCode: e.detail.value });
    this._updateComputed();
  },

  onRegPasswordInput: function (e) {
    this.setData({ regPassword: e.detail.value });
    this._updateComputed();
  },

  toggleRegPasswordVisibility: function () {
    this.setData({ showRegPassword: !this.data.showRegPassword });
  },

  selectRegRole: function (e) {
    var role = e.currentTarget.dataset.role;
    this.setData({ regRole: role });
    this._updateComputed();
  },

  // ============================================================
  // 角色选择弹窗事件
  // ============================================================

  onCompanyNameInput: function (e) {
    this.setData({ companyName: e.detail.value });
  },

  onContactNameInput: function (e) {
    this.setData({ contactName: e.detail.value });
  },

  selectRole: function (e) {
    var role = e.currentTarget.dataset.role;
    this.setData({ selectedRole: role });
  },

  preventTouchMove: function () {
    // 阻止弹窗下层滚动
  },

  // ============================================================
  // 更新计算属性（小程序不支持 computed，手动更新）
  // ============================================================

  _updateComputed: function () {
    var data = this.data;
    this.setData({
      canLogin: !!(data.loginPhone && data.loginPassword && !data.phoneError),
      canRegister: !!(data.regPhone && data.regCode && data.regPassword && data.regRole && !data.regPhoneError),
      canSendCode: PHONE_REGEX.test(data.regPhone) && data.codeCountdown === 0
    });
  },

  // ============================================================
  // 手机号 + 密码登录
  // ============================================================

  handleLogin: function () {
    var that = this;
    var phone = this.data.loginPhone;
    var password = this.data.loginPassword;

    // 前端校验
    if (!PHONE_REGEX.test(phone)) {
      this.setData({ phoneError: '请输入正确的手机号码' });
      return;
    }
    if (!password) {
      wx.showToast({ title: '请输入密码', icon: 'none' });
      return;
    }

    this.setData({ loginLoading: true });

    request.post('/auth/login', {
      phone: phone,
      password: password
    }).then(function (res) {
      that.setData({ loginLoading: false });
      that._handleLoginSuccess(res.token, res.user, res.is_new);
    }).catch(function (err) {
      that.setData({ loginLoading: false });
      // 错误已由 request.js 统一处理 Toast
    });
  },

  // ============================================================
  // 微信一键登录
  // ============================================================

  handleWxLogin: function () {
    var that = this;
    this.setData({ wxLoginLoading: true });

    wx.login({
      success: function (loginRes) {
        if (!loginRes.code) {
          that.setData({ wxLoginLoading: false });
          wx.showToast({ title: '微信登录失败，请重试', icon: 'none' });
          return;
        }

        request.post('/auth/wx-login', {
          code: loginRes.code
        }).then(function (res) {
          that.setData({ wxLoginLoading: false });
          that._handleLoginSuccess(res.token, res.user, res.is_new);
        }).catch(function (err) {
          that.setData({ wxLoginLoading: false });
          // 错误已由 request.js 统一处理 Toast
        });
      },
      fail: function () {
        that.setData({ wxLoginLoading: false });
        wx.showToast({ title: '微信登录失败，请重试', icon: 'none' });
      }
    });
  },

  // ============================================================
  // 发送验证码
  // ============================================================

  sendVerifyCode: function () {
    var that = this;
    var phone = this.data.regPhone;

    if (!PHONE_REGEX.test(phone)) {
      this.setData({ regPhoneError: '请输入正确的手机号码' });
      return;
    }

    // 开始倒计时
    this.setData({ codeCountdown: 60 });
    this._updateComputed();

    this._codeTimer = setInterval(function () {
      var countdown = that.data.codeCountdown - 1;
      if (countdown <= 0) {
        clearInterval(that._codeTimer);
        that._codeTimer = null;
        countdown = 0;
      }
      that.setData({ codeCountdown: countdown });
      that._updateComputed();
    }, 1000);

    // 请求发送验证码（后端可能暂未实现，先做前端逻辑）
    request.post('/auth/send-code', {
      phone: phone
    }).then(function () {
      wx.showToast({ title: '验证码已发送', icon: 'success' });
    }).catch(function () {
      // 即使发送失败也保持倒计时（防止频繁请求）
      wx.showToast({ title: '验证码发送失败，请稍后重试', icon: 'none' });
    });
  },

  // ============================================================
  // 手机号 + 验证码注册
  // ============================================================

  handleRegister: function () {
    var that = this;
    var phone = this.data.regPhone;
    var code = this.data.regCode;
    var password = this.data.regPassword;
    var role = this.data.regRole;

    // 前端校验
    if (!PHONE_REGEX.test(phone)) {
      this.setData({ regPhoneError: '请输入正确的手机号码' });
      return;
    }
    if (!code || code.length < 4) {
      wx.showToast({ title: '请输入正确的验证码', icon: 'none' });
      return;
    }
    if (!password || password.length < 6) {
      wx.showToast({ title: '密码长度不能少于6位', icon: 'none' });
      return;
    }
    if (password.length > 20) {
      wx.showToast({ title: '密码长度不能超过20位', icon: 'none' });
      return;
    }
    if (!role) {
      wx.showToast({ title: '请选择您的角色', icon: 'none' });
      return;
    }

    this.setData({ regLoading: true });

    request.post('/auth/register', {
      phone: phone,
      code: code,
      password: password,
      role: role
    }).then(function (res) {
      that.setData({ regLoading: false });
      // 注册时已选角色，直接进入（不弹角色弹窗）
      that._saveAndNavigate(res.token, res.user);
    }).catch(function (err) {
      that.setData({ regLoading: false });
    });
  },

  // ============================================================
  // 登录成功统一处理
  // ============================================================

  _handleLoginSuccess: function (token, userInfo, isNew) {
    if (isNew) {
      // 首次登录：显示角色选择弹窗
      this.setData({
        showRoleModal: true,
        _tempToken: token,
        _tempUserInfo: userInfo
      });
    } else {
      // 非首次登录：直接保存登录态并跳转
      this._saveAndNavigate(token, userInfo);
    }
  },

  // ============================================================
  // 确认角色选择
  // ============================================================

  confirmRole: function () {
    var that = this;
    var role = this.data.selectedRole;
    var companyName = this.data.companyName;
    var contactName = this.data.contactName;

    if (!role) {
      wx.showToast({ title: '请选择您的角色', icon: 'none' });
      return;
    }

    this.setData({ roleLoading: true });

    // 先保存 token 以便请求带上认证头
    var app = getApp();
    app.setLoginState(this.data._tempToken, this.data._tempUserInfo);

    // 调用 PUT /api/auth/profile 更新角色和基本信息
    var profileData = { role: role };
    if (companyName) {
      profileData.company_name = companyName;
    }
    if (contactName) {
      profileData.contact_name = contactName;
    }

    request.put('/auth/profile', profileData).then(function (res) {
      that.setData({ roleLoading: false, showRoleModal: false });

      // 更新用户信息中的角色
      var updatedUser = res.user || that.data._tempUserInfo;
      if (updatedUser) {
        updatedUser.role = role;
        if (companyName) updatedUser.company_name = companyName;
        if (contactName) updatedUser.contact_name = contactName;
      }

      that._saveAndNavigate(that.data._tempToken, updatedUser);
    }).catch(function (err) {
      that.setData({ roleLoading: false });
      // 即使更新失败也允许进入（角色可以后续完善）
      wx.showToast({ title: '信息保存失败，可稍后在个人中心完善', icon: 'none', duration: 2000 });
      setTimeout(function () {
        that.setData({ showRoleModal: false });
        that._saveAndNavigate(that.data._tempToken, that.data._tempUserInfo);
      }, 1500);
    });
  },

  // ============================================================
  // 保存登录态并跳转
  // ============================================================

  _saveAndNavigate: function (token, userInfo) {
    console.log('[login] _saveAndNavigate called, token:', token ? token.substring(0, 20) + '...' : 'EMPTY');
    console.log('[login] _saveAndNavigate userInfo:', userInfo ? JSON.stringify(userInfo).substring(0, 80) : 'NULL');

    var app = getApp();
    app.setLoginState(token, userInfo);

    // 验证存储是否成功
    var storedToken = wx.getStorageSync('token');
    console.log('[login] Verification - stored token:', storedToken ? storedToken.substring(0, 20) + '...' : 'EMPTY');

    wx.showToast({
      title: '登录成功',
      icon: 'success',
      duration: 1500
    });

    var redirectUrl = this.data.redirectUrl;

    setTimeout(function () {
      if (redirectUrl) {
        wx.redirectTo({ url: redirectUrl });
      } else {
        // 登录成功后跳转到"我的"页面
        wx.switchTab({ url: '/pages/profile/profile' });
      }
    }, 1000);
  }
});
