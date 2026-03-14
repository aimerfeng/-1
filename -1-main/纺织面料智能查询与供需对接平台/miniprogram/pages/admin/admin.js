/**
 * pages/admin/admin.js - 管理员审核页面
 *
 * 功能：
 * - 数据统计概览（用户数、面料数、订单数）
 * - 待审核用户列表（公司名称、联系方式、申请时间）
 * - Tab 筛选（待审核/已通过/已拒绝）
 * - 审核操作（通过/拒绝 + 拒绝原因输入）
 * - 下拉刷新
 * - 骨架屏加载
 * - 空状态展示
 *
 * 需求: 2.4, 2.6
 */

var request = require('../../utils/request');
var auth = require('../../utils/auth');
var util = require('../../utils/util');

/** 状态 Tab 配置 */
var STATUS_TABS = [
  { key: 'pending', label: '待审核' },
  { key: 'approved', label: '已通过' },
  { key: 'rejected', label: '已拒绝' }
];

/** 管理主 Tab 配置 */
var ADMIN_TABS = [
  { key: 'users', label: '用户审核' },
  { key: 'orders', label: '订单监控' },
  { key: 'conversations', label: '会话监控' }
];

/** 订单状态中文映射 */
var ORDER_STATUS_MAP = {
  'pending': '待确认',
  'confirmed': '已确认',
  'producing': '生产中',
  'shipped': '已发货',
  'received': '已签收',
  'completed': '已完成'
};

/** 认证状态中文映射 */
var CERT_STATUS_MAP = {
  'pending': '待审核',
  'approved': '已通过',
  'rejected': '已拒绝'
};

Page({
  data: {
    /** 是否为管理员 */
    isAdmin: false,
    /** 是否正在加载（首次加载，展示骨架屏） */
    loading: true,
    /** 管理主 Tab 列表 */
    adminTabs: ADMIN_TABS,
    /** 当前选中的管理主 Tab */
    activeAdminTab: 'users',
    /** 状态 Tab 列表 */
    statusTabs: STATUS_TABS,
    /** 当前选中的状态 Tab */
    activeStatus: 'pending',
    /** 认证状态中文映射 */
    certStatusMap: CERT_STATUS_MAP,
    /** 订单状态中文映射 */
    orderStatusMap: ORDER_STATUS_MAP,

    /** 数据统计 */
    stats: {
      userCount: 0,
      fabricCount: 0,
      orderCount: 0,
      conversationCount: 0
    },
    /** 统计数据是否加载中 */
    statsLoading: true,

    /** 用户列表 */
    userList: [],
    /** 列表是否加载中 */
    listLoading: false,
    /** 是否正在加载更多 */
    loadingMore: false,
    /** 是否还有更多数据 */
    hasMore: true,
    /** 当前页码 */
    page: 1,
    /** 每页条数 */
    perPage: 10,
    /** 总记录数 */
    total: 0,

    /** 订单监控列表 */
    orderList: [],
    orderListLoading: false,
    orderLoadingMore: false,
    orderHasMore: true,
    orderPage: 1,
    orderPerPage: 10,
    orderTotal: 0,
    /** 订单状态筛选 */
    orderStatusFilter: '',

    /** 会话监控列表 */
    conversationList: [],
    convListLoading: false,
    convLoadingMore: false,
    convHasMore: true,
    convPage: 1,
    convPerPage: 10,
    convTotal: 0,

    /** 审核弹窗是否显示 */
    reviewModalVisible: false,
    /** 当前审核的用户 */
    reviewingUser: null,
    /** 拒绝原因输入 */
    rejectReason: '',
    /** 审核操作加载中 */
    reviewLoading: false
  },

  onLoad: function () {
    this._checkAdminRole();
  },

  onShow: function () {
    if (this.data.isAdmin) {
      this._loadStats();
      var tab = this.data.activeAdminTab;
      if (tab === 'users') {
        this._loadUsers(true);
      } else if (tab === 'orders') {
        this._loadOrders(true);
      } else if (tab === 'conversations') {
        this._loadConversations(true);
      }
    }
  },

  /**
   * 下拉刷新
   */
  onPullDownRefresh: function () {
    this._loadStats();
    var tab = this.data.activeAdminTab;
    if (tab === 'users') {
      this._loadUsers(true);
    } else if (tab === 'orders') {
      this._loadOrders(true);
    } else if (tab === 'conversations') {
      this._loadConversations(true);
    }
  },

  /**
   * 上拉加载更多
   */
  onReachBottom: function () {
    var tab = this.data.activeAdminTab;
    if (tab === 'users') {
      if (this.data.hasMore && !this.data.loadingMore) {
        this._loadMore();
      }
    } else if (tab === 'orders') {
      if (this.data.orderHasMore && !this.data.orderLoadingMore) {
        this._loadMoreOrders();
      }
    } else if (tab === 'conversations') {
      if (this.data.convHasMore && !this.data.convLoadingMore) {
        this._loadMoreConversations();
      }
    }
  },

  /**
   * 检查管理员权限
   */
  _checkAdminRole: function () {
    var app = getApp();
    var userInfo = app.globalData.userInfo;

    if (!userInfo || userInfo.role !== 'admin') {
      this.setData({ isAdmin: false, loading: false });
      wx.showToast({ title: '无权限访问', icon: 'none', duration: 2000 });
      setTimeout(function () {
        wx.navigateBack();
      }, 1500);
      return;
    }

    this.setData({ isAdmin: true });
    this._loadStats();
    this._loadUsers(true);
  },

  // ============================================================
  // 数据统计
  // ============================================================

  /**
   * 加载数据统计概览
   */
  _loadStats: function () {
    var that = this;
    this.setData({ statsLoading: true });

    var userPromise = request.get('/admin/users', { status: 'approved', page: 1, per_page: 1 }, { showError: false });
    var fabricPromise = request.get('/fabrics', { page: 1, per_page: 1 }, { showError: false });
    var orderPromise = request.get('/orders', { page: 1, per_page: 1 }, { showError: false });
    var convPromise = request.get('/conversations', { page: 1, per_page: 1 }, { showError: false });

    var results = { userCount: 0, fabricCount: 0, orderCount: 0, conversationCount: 0 };
    var completed = 0;
    var totalRequests = 4;

    function checkDone() {
      completed++;
      if (completed >= totalRequests) {
        that.setData({
          stats: results,
          statsLoading: false
        });
      }
    }

    userPromise.then(function (res) {
      results.userCount = res.total || 0;
      checkDone();
    }).catch(function () {
      checkDone();
    });

    fabricPromise.then(function (res) {
      results.fabricCount = res.total || 0;
      checkDone();
    }).catch(function () {
      checkDone();
    });

    orderPromise.then(function (res) {
      results.orderCount = res.total || 0;
      checkDone();
    }).catch(function () {
      checkDone();
    });

    convPromise.then(function (res) {
      results.conversationCount = res.total || 0;
      checkDone();
    }).catch(function () {
      checkDone();
    });
  },

  // ============================================================
  // 管理主 Tab 切换
  // ============================================================

  /**
   * 切换管理主 Tab
   */
  onAdminTabChange: function (e) {
    var tab = e.currentTarget.dataset.tab;
    if (tab === this.data.activeAdminTab) return;

    this.setData({ activeAdminTab: tab });

    if (tab === 'users') {
      this._loadUsers(true);
    } else if (tab === 'orders') {
      if (this.data.orderList.length === 0) {
        this._loadOrders(true);
      }
    } else if (tab === 'conversations') {
      if (this.data.conversationList.length === 0) {
        this._loadConversations(true);
      }
    }
  },

  // ============================================================
  // 用户列表
  // ============================================================

  /**
   * 切换状态 Tab
   */
  onTabChange: function (e) {
    var status = e.currentTarget.dataset.status;
    if (status === this.data.activeStatus) return;

    this.setData({ activeStatus: status });
    this._loadUsers(true);
  },

  /**
   * 加载用户列表
   * @param {boolean} isRefresh - 是否为刷新（重置页码）
   */
  _loadUsers: function (isRefresh) {
    var that = this;

    if (isRefresh) {
      this.setData({
        page: 1,
        listLoading: true,
        hasMore: true,
        userList: []
      });
    }

    var params = {
      status: this.data.activeStatus,
      page: this.data.page,
      per_page: this.data.perPage
    };

    request.get('/admin/users', params).then(function (res) {
      var items = res.items || [];
      var total = res.total || 0;
      var currentPage = res.page || 1;
      var perPage = res.per_page || that.data.perPage;

      // 格式化时间
      for (var i = 0; i < items.length; i++) {
        items[i]._relativeTime = util.getRelativeTime(items[i].created_at);
        items[i]._formattedTime = util.formatDate(items[i].created_at, 'YYYY-MM-DD HH:mm');
      }

      that.setData({
        userList: items,
        total: total,
        page: currentPage,
        loading: false,
        listLoading: false,
        hasMore: currentPage * perPage < total
      });

      wx.stopPullDownRefresh();
    }).catch(function () {
      that.setData({ loading: false, listLoading: false });
      wx.stopPullDownRefresh();
    });
  },

  /**
   * 加载更多数据
   */
  _loadMore: function () {
    var that = this;
    var nextPage = this.data.page + 1;

    this.setData({ loadingMore: true });

    var params = {
      status: this.data.activeStatus,
      page: nextPage,
      per_page: this.data.perPage
    };

    request.get('/admin/users', params).then(function (res) {
      var items = res.items || [];
      var total = res.total || 0;
      var currentPage = res.page || nextPage;
      var perPage = res.per_page || that.data.perPage;

      // 格式化时间
      for (var i = 0; i < items.length; i++) {
        items[i]._relativeTime = util.getRelativeTime(items[i].created_at);
        items[i]._formattedTime = util.formatDate(items[i].created_at, 'YYYY-MM-DD HH:mm');
      }

      that.setData({
        userList: that.data.userList.concat(items),
        total: total,
        page: currentPage,
        loadingMore: false,
        hasMore: currentPage * perPage < total
      });
    }).catch(function () {
      that.setData({ loadingMore: false });
    });
  },

  // ============================================================
  // 订单监控
  // ============================================================

  /**
   * 订单状态筛选切换
   */
  onOrderStatusFilter: function (e) {
    var status = e.currentTarget.dataset.status || '';
    if (status === this.data.orderStatusFilter) {
      // 点击已选中的状态，取消筛选
      this.setData({ orderStatusFilter: '' });
    } else {
      this.setData({ orderStatusFilter: status });
    }
    this._loadOrders(true);
  },

  /**
   * 加载订单列表（admin 看全部）
   */
  _loadOrders: function (isRefresh) {
    var that = this;

    if (isRefresh) {
      this.setData({
        orderPage: 1,
        orderListLoading: true,
        orderHasMore: true,
        orderList: []
      });
    }

    var params = {
      page: this.data.orderPage,
      per_page: this.data.orderPerPage
    };
    if (this.data.orderStatusFilter) {
      params.status = this.data.orderStatusFilter;
    }

    request.get('/orders', params).then(function (res) {
      var items = res.items || [];
      var total = res.total || 0;
      var currentPage = res.page || 1;
      var perPage = res.per_page || that.data.orderPerPage;

      for (var i = 0; i < items.length; i++) {
        items[i]._statusText = ORDER_STATUS_MAP[items[i].status] || items[i].status;
        items[i]._createdTime = util.formatDate(items[i].created_at, 'YYYY-MM-DD HH:mm');
        // Admin counterparty is an object with buyer/supplier
        var cp = items[i].counterparty;
        if (cp && typeof cp === 'object') {
          items[i]._buyerName = cp.buyer_company_name || '未知';
          items[i]._supplierName = cp.supplier_company_name || '未知';
        }
      }

      that.setData({
        orderList: items,
        orderTotal: total,
        orderPage: currentPage,
        loading: false,
        orderListLoading: false,
        orderHasMore: currentPage * perPage < total
      });

      wx.stopPullDownRefresh();
    }).catch(function () {
      that.setData({ loading: false, orderListLoading: false });
      wx.stopPullDownRefresh();
    });
  },

  /**
   * 加载更多订单
   */
  _loadMoreOrders: function () {
    var that = this;
    var nextPage = this.data.orderPage + 1;

    this.setData({ orderLoadingMore: true });

    var params = {
      page: nextPage,
      per_page: this.data.orderPerPage
    };
    if (this.data.orderStatusFilter) {
      params.status = this.data.orderStatusFilter;
    }

    request.get('/orders', params).then(function (res) {
      var items = res.items || [];
      var total = res.total || 0;
      var currentPage = res.page || nextPage;
      var perPage = res.per_page || that.data.orderPerPage;

      for (var i = 0; i < items.length; i++) {
        items[i]._statusText = ORDER_STATUS_MAP[items[i].status] || items[i].status;
        items[i]._createdTime = util.formatDate(items[i].created_at, 'YYYY-MM-DD HH:mm');
        var cp = items[i].counterparty;
        if (cp && typeof cp === 'object') {
          items[i]._buyerName = cp.buyer_company_name || '未知';
          items[i]._supplierName = cp.supplier_company_name || '未知';
        }
      }

      that.setData({
        orderList: that.data.orderList.concat(items),
        orderTotal: total,
        orderPage: currentPage,
        orderLoadingMore: false,
        orderHasMore: currentPage * perPage < total
      });
    }).catch(function () {
      that.setData({ orderLoadingMore: false });
    });
  },

  /**
   * 点击订单卡片，跳转到订单详情
   */
  onOrderTap: function (e) {
    var orderId = e.currentTarget.dataset.id;
    wx.navigateTo({
      url: '/pages/order/detail/detail?id=' + orderId
    });
  },

  // ============================================================
  // 会话监控
  // ============================================================

  /**
   * 加载会话列表（admin 看全部）
   */
  _loadConversations: function (isRefresh) {
    var that = this;

    if (isRefresh) {
      this.setData({
        convPage: 1,
        convListLoading: true,
        convHasMore: true,
        conversationList: []
      });
    }

    var params = {
      page: this.data.convPage,
      per_page: this.data.convPerPage
    };

    request.get('/conversations', params).then(function (res) {
      var items = res.items || [];
      var total = res.total || 0;
      var currentPage = res.page || 1;
      var perPage = res.per_page || that.data.convPerPage;

      for (var i = 0; i < items.length; i++) {
        var item = items[i];
        item._lastTime = item.last_message_at ? util.getRelativeTime(item.last_message_at) : '';
        // Admin counterparty is an object
        var cp = item.counterparty;
        if (cp && typeof cp === 'object') {
          item._buyerName = cp.buyer_company_name || '未知';
          item._supplierName = cp.supplier_company_name || '未知';
        }
      }

      that.setData({
        conversationList: items,
        convTotal: total,
        convPage: currentPage,
        loading: false,
        convListLoading: false,
        convHasMore: currentPage * perPage < total
      });

      wx.stopPullDownRefresh();
    }).catch(function () {
      that.setData({ loading: false, convListLoading: false });
      wx.stopPullDownRefresh();
    });
  },

  /**
   * 加载更多会话
   */
  _loadMoreConversations: function () {
    var that = this;
    var nextPage = this.data.convPage + 1;

    this.setData({ convLoadingMore: true });

    var params = {
      page: nextPage,
      per_page: this.data.convPerPage
    };

    request.get('/conversations', params).then(function (res) {
      var items = res.items || [];
      var total = res.total || 0;
      var currentPage = res.page || nextPage;
      var perPage = res.per_page || that.data.convPerPage;

      for (var i = 0; i < items.length; i++) {
        var item = items[i];
        item._lastTime = item.last_message_at ? util.getRelativeTime(item.last_message_at) : '';
        var cp = item.counterparty;
        if (cp && typeof cp === 'object') {
          item._buyerName = cp.buyer_company_name || '未知';
          item._supplierName = cp.supplier_company_name || '未知';
        }
      }

      that.setData({
        conversationList: that.data.conversationList.concat(items),
        convTotal: total,
        convPage: currentPage,
        convLoadingMore: false,
        convHasMore: currentPage * perPage < total
      });
    }).catch(function () {
      that.setData({ convLoadingMore: false });
    });
  },

  /**
   * 点击会话卡片，跳转到聊天详情（admin 只读）
   */
  onConversationTap: function (e) {
    var convId = e.currentTarget.dataset.id;
    wx.navigateTo({
      url: '/pages/message/chat/chat?id=' + convId
    });
  },

  // ============================================================
  // 审核操作
  // ============================================================

  /**
   * 打开审核弹窗
   */
  onReviewTap: function (e) {
    var user = e.currentTarget.dataset.user;
    this.setData({
      reviewModalVisible: true,
      reviewingUser: user,
      rejectReason: ''
    });
  },

  /**
   * 关闭审核弹窗
   */
  closeReviewModal: function () {
    if (this.data.reviewLoading) return;
    this.setData({
      reviewModalVisible: false,
      reviewingUser: null,
      rejectReason: ''
    });
  },

  /**
   * 阻止事件冒泡
   */
  preventBubble: function () {
    // 空函数，仅用于阻止冒泡
  },

  /**
   * 拒绝原因输入
   */
  onRejectReasonInput: function (e) {
    this.setData({ rejectReason: e.detail.value });
  },

  /**
   * 审核通过
   */
  onApprove: function () {
    var that = this;
    var user = this.data.reviewingUser;
    if (!user) return;

    this.setData({ reviewLoading: true });

    request.put('/admin/users/' + user.id + '/certify', {
      status: 'approved'
    }).then(function () {
      wx.showToast({ title: '已通过审核', icon: 'success' });
      that.setData({
        reviewModalVisible: false,
        reviewingUser: null,
        reviewLoading: false
      });
      that._loadStats();
      that._loadUsers(true);
    }).catch(function () {
      that.setData({ reviewLoading: false });
    });
  },

  /**
   * 审核拒绝
   */
  onReject: function () {
    var that = this;
    var user = this.data.reviewingUser;
    if (!user) return;

    var reason = this.data.rejectReason.trim();
    if (!reason) {
      wx.showToast({ title: '请输入拒绝原因', icon: 'none' });
      return;
    }

    this.setData({ reviewLoading: true });

    request.put('/admin/users/' + user.id + '/certify', {
      status: 'rejected',
      reason: reason
    }).then(function () {
      wx.showToast({ title: '已拒绝申请', icon: 'success' });
      that.setData({
        reviewModalVisible: false,
        reviewingUser: null,
        rejectReason: '',
        reviewLoading: false
      });
      that._loadStats();
      that._loadUsers(true);
    }).catch(function () {
      that.setData({ reviewLoading: false });
    });
  }
});
