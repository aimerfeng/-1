/**
 * pages/home/home.js - 首页
 *
 * 功能：
 * - 顶部搜索栏（跳转面料查询页）
 * - 功能入口网格（根据角色动态展示）
 * - 最新匹配推荐列表（调用匹配结果接口）
 * - 数据加载时展示骨架屏
 * - 下拉刷新
 *
 * 需求: 2.2, 2.3, 2.4, 10.2
 */

var request = require('../../utils/request');
var auth = require('../../utils/auth');

/** 采购方功能入口 */
var BUYER_ENTRIES = [
  { key: 'fabric_search', icon: '🔍', label: '面料查询', type: 'switchTab', url: '/pages/fabric/list/list' },
  { key: 'demand_publish', icon: '📝', label: '我的需求', type: 'navigate', url: '/pages/demand/list/list' },
  { key: 'sample_manage', icon: '📦', label: '样品管理', type: 'navigate', url: '/pages/sample/sample' },
  { key: 'order_manage', icon: '📋', label: '订单管理', type: 'navigate', url: '/pages/order/list/list' },
  { key: 'data_stats', icon: '📊', label: '数据统计', type: 'navigate', url: '/pages/stats/stats' }
];

/** 供应商功能入口 */
var SUPPLIER_ENTRIES = [
  { key: 'fabric_manage', icon: '🧵', label: '面料管理', type: 'navigate', url: '/pages/fabric/manage/manage' },
  { key: 'demand_browse', icon: '📄', label: '需求浏览', type: 'navigate', url: '/pages/demand/list/list' },
  { key: 'sample_manage', icon: '📦', label: '样品管理', type: 'navigate', url: '/pages/sample/sample' },
  { key: 'order_manage', icon: '📋', label: '订单管理', type: 'navigate', url: '/pages/order/list/list' },
  { key: 'data_stats', icon: '📊', label: '数据统计', type: 'navigate', url: '/pages/stats/stats' }
];

/** 管理员功能入口 */
var ADMIN_ENTRIES = [
  { key: 'user_audit', icon: '✅', label: '用户审核', type: 'navigate', url: '/pages/admin/admin' },
  { key: 'fabric_search', icon: '🔍', label: '面料查询', type: 'switchTab', url: '/pages/fabric/list/list' },
  { key: 'order_manage', icon: '📋', label: '订单管理', type: 'navigate', url: '/pages/order/list/list' },
  { key: 'data_stats', icon: '📊', label: '数据统计', type: 'navigate', url: '/pages/stats/stats' }
];

/** 未登录时的默认功能入口 */
var DEFAULT_ENTRIES = [
  { key: 'fabric_search', icon: '🔍', label: '面料查询', type: 'switchTab', url: '/pages/fabric/list/list' },
  { key: 'demand_publish', icon: '📝', label: '需求发布', type: 'navigate', url: '' },
  { key: 'sample_manage', icon: '📦', label: '样品管理', type: 'navigate', url: '' },
  { key: 'order_manage', icon: '📋', label: '订单管理', type: 'navigate', url: '' }
];

Page({
  data: {
    /** 是否正在加载（首次加载，展示骨架屏） */
    loading: true,
    /** 是否已登录 */
    isLoggedIn: false,
    /** 用户角色 */
    userRole: null,
    /** 用户信息 */
    userInfo: null,
    /** 功能入口列表 */
    functionEntries: [],
    /** 推荐面料列表 */
    recommendList: [],
    /** 推荐列表是否正在加载 */
    recommendLoading: false,
    /** 推荐区域标题 */
    recommendTitle: '最新推荐',
    /** 是否有推荐数据 */
    hasRecommend: false
  },

  onLoad: function () {
    this._loaded = false;
    this._initPage();
  },

  onShow: function () {
    // 只在登录态变化时重新加载，避免每次切换 tab 都全量刷新
    var app = getApp();
    var currentLoginState = app.globalData.isLoggedIn;
    if (this._loaded && currentLoginState === this.data.isLoggedIn) return;
    this._initPage();
  },

  /**
   * 下拉刷新
   */
  onPullDownRefresh: function () {
    this._initPage(function () {
      wx.stopPullDownRefresh();
    });
  },

  /**
   * 初始化页面数据
   * @param {Function} [callback] - 完成回调
   */
  _initPage: function (callback) {
    // 双重检查登录态：globalData + Storage
    var app = getApp();
    var isLoggedIn = auth.isLoggedIn();
    var token = wx.getStorageSync('token');

    if (!isLoggedIn && token) {
      var userInfo = wx.getStorageSync('userInfo');
      if (app && app.setLoginState) {
        app.setLoginState(token, userInfo);
      }
      isLoggedIn = true;
    }

    var userRole = auth.getUserRole();
    var userInfo = auth.getUserInfo();

    // 设置功能入口
    var entries = this._getEntriesByRole(userRole, isLoggedIn);

    this.setData({
      isLoggedIn: isLoggedIn,
      userRole: userRole,
      userInfo: userInfo,
      functionEntries: entries
    });

    this._loaded = true;

    if (isLoggedIn) {
      this._loadRecommendations(callback);
    } else {
      this.setData({
        loading: false,
        recommendList: [],
        hasRecommend: false
      });
      if (typeof callback === 'function') callback();
    }
  },

  /**
   * 根据角色获取功能入口
   * @param {string|null} role - 用户角色
   * @param {boolean} isLoggedIn - 是否已登录
   * @returns {Array} 功能入口列表
   */
  _getEntriesByRole: function (role, isLoggedIn) {
    if (!isLoggedIn) return DEFAULT_ENTRIES;

    if (role === 'buyer') return BUYER_ENTRIES;
    if (role === 'supplier') return SUPPLIER_ENTRIES;
    if (role === 'admin') return ADMIN_ENTRIES;

    return DEFAULT_ENTRIES;
  },

  /**
   * 加载推荐数据
   * 采购方：获取最新需求的匹配结果
   * 供应商：获取最新面料列表
   * @param {Function} [callback] - 完成回调
   */
  _loadRecommendations: function (callback) {
    var role = this.data.userRole;

    this.setData({ loading: true, recommendLoading: true });

    if (role === 'buyer') {
      this.setData({ recommendTitle: '最新匹配推荐' });
      this._loadBuyerRecommendations(callback);
    } else if (role === 'supplier') {
      this.setData({ recommendTitle: '最新面料动态' });
      this._loadSupplierRecommendations(callback);
    } else {
      // admin or other
      this.setData({ recommendTitle: '最新面料' });
      this._loadLatestFabrics(callback);
    }
  },

  /**
   * 采购方推荐：获取最新需求的匹配结果
   * @param {Function} [callback]
   */
  _loadBuyerRecommendations: function (callback) {
    var that = this;

    // 先获取采购方的需求列表
    request.get('/demands', { page: 1, per_page: 3 }, { showError: false }).then(function (res) {
      var demands = res.items || res.demands || [];
      if (demands.length === 0) {
        // 没有需求，降级展示最新面料
        that._loadLatestFabrics(callback);
        return;
      }

      // 获取第一个需求的匹配结果
      var firstDemand = demands[0];
      request.get('/demands/' + firstDemand.id + '/matches', {}, { showError: false }).then(function (matchRes) {
        var matches = matchRes.matches || matchRes.items || [];
        var fabricList = [];

        for (var i = 0; i < matches.length && i < 6; i++) {
          var match = matches[i];
          if (match.fabric) {
            match.fabric._matchScore = match.score;
            fabricList.push(match.fabric);
          }
        }

        that.setData({
          loading: false,
          recommendLoading: false,
          recommendList: fabricList,
          hasRecommend: fabricList.length > 0
        });

        if (fabricList.length === 0) {
          // 没有匹配结果，降级展示最新面料
          that._loadLatestFabrics(callback);
          return;
        }

        if (typeof callback === 'function') callback();
      }).catch(function () {
        that._loadLatestFabrics(callback);
      });
    }).catch(function () {
      that._loadLatestFabrics(callback);
    });
  },

  /**
   * 供应商推荐：获取最新面料列表
   * @param {Function} [callback]
   */
  _loadSupplierRecommendations: function (callback) {
    this._loadLatestFabrics(callback);
  },

  /**
   * 加载最新面料列表（通用降级方案）
   * @param {Function} [callback]
   */
  _loadLatestFabrics: function (callback) {
    var that = this;

    request.get('/fabrics', { page: 1, per_page: 6 }, { showError: false }).then(function (res) {
      var items = res.items || [];

      that.setData({
        loading: false,
        recommendLoading: false,
        recommendList: items,
        hasRecommend: items.length > 0
      });

      if (typeof callback === 'function') callback();
    }).catch(function () {
      that.setData({
        loading: false,
        recommendLoading: false,
        recommendList: [],
        hasRecommend: false
      });
      if (typeof callback === 'function') callback();
    });
  },

  /**
   * 搜索栏点击 - 跳转面料查询页
   */
  onSearchTap: function () {
    wx.switchTab({
      url: '/pages/fabric/list/list'
    });
  },

  /**
   * 功能入口点击
   */
  onEntryTap: function (e) {
    var entry = e.currentTarget.dataset.entry;
    if (!entry) return;

    // 未登录时，除面料查询外需要先登录
    if (!this.data.isLoggedIn && entry.key !== 'fabric_search') {
      wx.navigateTo({ url: '/pages/login/login' });
      return;
    }

    // 功能开发中提示
    if (!entry.url) {
      wx.showToast({ title: '功能开发中', icon: 'none' });
      return;
    }

    if (entry.type === 'switchTab') {
      wx.switchTab({ url: entry.url });
    } else {
      wx.navigateTo({ url: entry.url });
    }
  },

  /**
   * 面料卡片点击 - 跳转面料详情
   */
  onFabricTap: function (e) {
    var fabric = e.detail && e.detail.fabric;
    if (fabric && fabric.id) {
      wx.navigateTo({
        url: '/pages/fabric/detail/detail?id=' + fabric.id
      });
    }
  },

  /**
   * 查看更多推荐
   */
  onViewMoreTap: function () {
    if (this.data.userRole === 'buyer') {
      wx.navigateTo({ url: '/pages/demand/match/match' });
    } else {
      wx.switchTab({ url: '/pages/fabric/list/list' });
    }
  },

  /**
   * 空状态操作按钮点击
   */
  onEmptyAction: function () {
    if (this.data.userRole === 'buyer') {
      wx.navigateTo({ url: '/pages/demand/publish/publish' });
    } else {
      wx.switchTab({ url: '/pages/fabric/list/list' });
    }
  },

  /**
   * 跳转登录页
   */
  goLogin: function () {
    wx.navigateTo({ url: '/pages/login/login' });
  }
});
