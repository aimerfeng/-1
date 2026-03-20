// pages/profile/profile.js
var request = require('../../utils/request');
var auth = require('../../utils/auth');

var ROLE_TEXT_MAP = {
  'buyer': '采购方',
  'supplier': '供应商',
  'admin': '管理员'
};

var CERT_STATUS_MAP = {
  'pending': '待认证',
  'approved': '已认证',
  'rejected': '认证未通过'
};

Page({
  data: {
    loading: false,
    isLoggedIn: false,
    isEditing: false,
    saving: false,
    userInfo: null,
    roleText: '',
    certStatusText: '',
    avatarLetter: '',
    editForm: {
      company_name: '',
      contact_name: '',
      address: ''
    }
  },

  onLoad: function () {
    this._checkLoginAndLoad();
  },

  onShow: function () {
    var that = this;
    // 延迟检查避免渲染层未就绪时 setData 报警告
    setTimeout(function () {
      that._checkLoginAndLoad();
    }, 50);
  },

  onPullDownRefresh: function () {
    if (this.data.isLoggedIn) {
      this._fetchProfile(function () {
        wx.stopPullDownRefresh();
      });
    } else {
      wx.stopPullDownRefresh();
    }
  },

  _checkLoginAndLoad: function () {
    var token = wx.getStorageSync('token') || '';
    var userInfo = wx.getStorageSync('userInfo') || null;

    if (!token) {
      var app = getApp();
      if (app && app.globalData && app.globalData.token) {
        token = app.globalData.token;
        userInfo = app.globalData.userInfo;
      }
    }

    if (!token) {
      this.setData({
        loading: false,
        isLoggedIn: false,
        userInfo: null
      });
      return;
    }

    this.setData({ isLoggedIn: true });

    if (userInfo) {
      this._setUserData(userInfo);
    }

    this._fetchProfile();
  },

  _fetchProfile: function (callback) {
    var that = this;
    this.setData({ loading: true });

    request.get('/auth/profile').then(function (res) {
      var user = res.user || {};
      wx.setStorageSync('userInfo', user);
      that._setUserData(user);
      that.setData({ loading: false });
      if (callback) callback();
    }).catch(function () {
      that.setData({ loading: false });
      if (callback) callback();
    });
  },

  _setUserData: function (user) {
    var roleText = ROLE_TEXT_MAP[user.role] || '';
    var certStatus = user.certification_status || '';
    var certStatusText = CERT_STATUS_MAP[certStatus] || '';
    var avatarLetter = '用';

    if (user.contact_name) {
      avatarLetter = user.contact_name.charAt(0);
    } else if (user.company_name) {
      avatarLetter = user.company_name.charAt(0);
    } else if (user.phone) {
      avatarLetter = user.phone.charAt(0);
    }

    // 构建头像完整 URL
    if (user.avatar && !user.avatarUrl) {
      var app = getApp();
      var baseUrl = (app && app.globalData && app.globalData.baseUrl) || 'http://127.0.0.1:5000/api';
      var serverRoot = baseUrl.replace(/\/api\/?$/, '');
      user.avatarUrl = serverRoot + user.avatar;
    }

    this.setData({
      userInfo: user,
      roleText: roleText,
      certStatusText: certStatusText,
      avatarLetter: avatarLetter,
      editForm: {
        company_name: user.company_name || '',
        contact_name: user.contact_name || '',
        address: user.address || ''
      }
    });
  },

  toggleEdit: function () {
    this.setData({ isEditing: !this.data.isEditing });
  },

  onCompanyInput: function (e) {
    this.setData({ 'editForm.company_name': e.detail.value });
  },

  onContactInput: function (e) {
    this.setData({ 'editForm.contact_name': e.detail.value });
  },

  onAddressInput: function (e) {
    this.setData({ 'editForm.address': e.detail.value });
  },

  saveProfile: function () {
    var that = this;
    var form = this.data.editForm;

    this.setData({ saving: true });

    request.put('/auth/profile', {
      company_name: form.company_name,
      contact_name: form.contact_name,
      address: form.address
    }).then(function (res) {
      var updatedUser = res.user || {};
      wx.setStorageSync('userInfo', updatedUser);
      that._setUserData(updatedUser);
      that.setData({ saving: false, isEditing: false });
      wx.showToast({ title: '保存成功', icon: 'success' });
    }).catch(function () {
      that.setData({ saving: false });
    });
  },

  onAvatarTap: function () {
    var that = this;
    wx.chooseMedia({
      count: 1,
      mediaType: ['image'],
      sourceType: ['album', 'camera'],
      sizeType: ['compressed'],
      success: function (res) {
        var tempFilePath = res.tempFiles[0].tempFilePath;
        var app = getApp();
        var baseUrl = (app && app.globalData && app.globalData.baseUrl) || 'http://127.0.0.1:5000/api';
        var token = auth.getToken();

        wx.showLoading({ title: '上传中...', mask: true });

        wx.uploadFile({
          url: baseUrl + '/auth/avatar',
          filePath: tempFilePath,
          name: 'file',
          header: { 'Authorization': 'Bearer ' + token },
          success: function (uploadRes) {
            wx.hideLoading();
            if (uploadRes.statusCode !== 200) {
              try {
                var errData = JSON.parse(uploadRes.data);
                wx.showToast({ title: errData.message || '上传失败', icon: 'none' });
              } catch (e) {
                wx.showToast({ title: '上传失败', icon: 'none' });
              }
              return;
            }
            try {
              var data = JSON.parse(uploadRes.data);
              if (data.user) {
                wx.setStorageSync('userInfo', data.user);
                that._setUserData(data.user);
                wx.showToast({ title: '头像已更新', icon: 'success' });
              } else {
                wx.showToast({ title: data.message || '上传失败', icon: 'none' });
              }
            } catch (e) {
              wx.showToast({ title: '上传失败', icon: 'none' });
            }
          },
          fail: function () {
            wx.hideLoading();
            wx.showToast({ title: '上传失败，请重试', icon: 'none' });
          }
        });
      }
    });
  },

  goLogin: function () {
    wx.navigateTo({ url: '/pages/login/login' });
  },

  goToFavorites: function () {
    wx.navigateTo({ url: '/pages/favorites/favorites' });
  },

  goToOrders: function () {
    wx.navigateTo({ url: '/pages/order/list/list' });
  },

  goToSamples: function () {
    wx.navigateTo({ url: '/pages/sample/sample' });
  },

  goToDemands: function () {
    wx.navigateTo({ url: '/pages/demand/list/list' });
  },

  goToFabrics: function () {
    wx.switchTab({ url: '/pages/fabric/list/list' });
  },

  goPublishFabric: function () {
    wx.navigateTo({ url: '/pages/fabric/publish/publish' });
  },

  goManageFabrics: function () {
    wx.navigateTo({ url: '/pages/fabric/manage/manage' });
  },

  goToAudit: function () {
    wx.navigateTo({ url: '/pages/admin/admin?tab=users' });
  },

  goToStats: function () {
    wx.navigateTo({ url: '/pages/admin/admin?tab=stats' });
  },

  goToAbout: function () {
    wx.showModal({
      title: '关于平台',
      content: '纺织面料智能查询与供需对接平台 v1.0.0',
      showCancel: false
    });
  },

  handleLogout: function () {
    var that = this;
    wx.showModal({
      title: '提示',
      content: '确定要退出登录吗？',
      confirmText: '退出',
      success: function (res) {
        if (res.confirm) {
          // 清除全局登录态
          var app = getApp();
          if (app && app.clearLoginState) {
            app.clearLoginState();
          } else {
            auth.clearToken();
          }
          that.setData({
            isLoggedIn: false,
            userInfo: null,
            isEditing: false
          });
          wx.showToast({ title: '已退出登录', icon: 'success' });
        }
      }
    });
  }
});
