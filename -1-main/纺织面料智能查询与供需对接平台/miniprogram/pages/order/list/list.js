/**
 * pages/order/list/list.js - 订单列表页面
 * 展示订单列表：订单号、面料摘要、金额、状态标签
 * 实现状态筛选 tab（全部/待确认/生产中/已发货/已完成）
 * 实现下拉刷新和分页加载
 * 需求: 7.4, 10.3
 */
var request = require('../../../utils/request');
var auth = require('../../../utils/auth');

Page({
  data: {
    /** 订单列表数据 */
    orderList: [],
    /** 是否正在加载（首次加载，展示骨架屏） */
    loading: true,
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

    /** 状态筛选 tab 列表 */
    statusTabs: [
      { key: '', label: '全部' },
      { key: 'pending', label: '待确认' },
      { key: 'producing', label: '生产中' },
      { key: 'shipped', label: '已发货' },
      { key: 'completed', label: '已完成' }
    ],
    /** 当前选中的状态筛选 */
    activeStatus: '',

    /** 当前用户角色 */
    userRole: '',

    /** 状态中文映射 */
    statusTextMap: {
      'pending': '待确认',
      'confirmed': '已确认',
      'producing': '生产中',
      'shipped': '已发货',
      'received': '已签收',
      'completed': '已完成'
    },

    /** 状态颜色类型映射 */
    statusTypeMap: {
      'pending': 'warning',
      'confirmed': 'info',
      'producing': 'primary',
      'shipped': 'primary',
      'received': 'success',
      'completed': 'success'
    }
  },

  onLoad: function () {
    var role = auth.getUserRole() || 'buyer';
    this.setData({ userRole: role });
    this._loadOrders(true);
  },

  onShow: function () {
    // 页面再次显示时可刷新数据（如从详情页返回）
  },

  /**
   * 下拉刷新
   */
  onPullDownRefresh: function () {
    this._loadOrders(true);
  },

  /**
   * 上拉加载更多
   */
  onReachBottom: function () {
    if (this.data.hasMore && !this.data.loadingMore) {
      this._loadMore();
    }
  },

  /**
   * 切换状态筛选 tab
   */
  onTabChange: function (e) {
    var status = e.currentTarget.dataset.status;
    if (status === this.data.activeStatus) return;

    this.setData({ activeStatus: status });
    this._loadOrders(true);
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

  /**
   * 加载订单列表
   * @param {boolean} isRefresh - 是否为刷新（重置页码）
   */
  _loadOrders: function (isRefresh) {
    var that = this;

    if (isRefresh) {
      this.setData({
        page: 1,
        loading: true,
        hasMore: true,
        orderList: []
      });
    }

    var params = {
      page: this.data.page,
      per_page: this.data.perPage
    };

    // 添加状态筛选参数
    if (this.data.activeStatus) {
      params.status = this.data.activeStatus;
    }

    request.get('/orders', params).then(function (res) {
      var items = res.items || [];
      var total = res.total || 0;
      var currentPage = res.page || 1;
      var perPage = res.per_page || that.data.perPage;

      // 处理订单数据，生成面料摘要
      var processedItems = items.map(function (item) {
        return that._processOrderItem(item);
      });

      that.setData({
        orderList: processedItems,
        total: total,
        page: currentPage,
        loading: false,
        hasMore: currentPage * perPage < total
      });

      if (isRefresh) {
        wx.stopPullDownRefresh();
      }
    }).catch(function () {
      that.setData({ loading: false });
      if (isRefresh) {
        wx.stopPullDownRefresh();
      }
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
      page: nextPage,
      per_page: this.data.perPage
    };

    if (this.data.activeStatus) {
      params.status = this.data.activeStatus;
    }

    request.get('/orders', params).then(function (res) {
      var items = res.items || [];
      var total = res.total || 0;
      var currentPage = res.page || nextPage;
      var perPage = res.per_page || that.data.perPage;

      var processedItems = items.map(function (item) {
        return that._processOrderItem(item);
      });

      that.setData({
        orderList: that.data.orderList.concat(processedItems),
        total: total,
        page: currentPage,
        loadingMore: false,
        hasMore: currentPage * perPage < total
      });
    }).catch(function () {
      that.setData({ loadingMore: false });
    });
  },

  /**
   * 处理单个订单数据，生成面料摘要文本和对方公司名
   * @param {Object} order - 订单数据
   * @returns {Object} 处理后的订单数据
   */
  _processOrderItem: function (order) {
    var fabricSummary = '';
    var role = this.data.userRole;

    // 优先使用需求标题作为摘要
    if (order.demand_title) {
      fabricSummary = order.demand_title;
    } else if (order.items && order.items.length > 0) {
      // 降级：使用面料名称摘要
      var names = order.items.map(function (item) {
        if (item.fabric && item.fabric.name) {
          return item.fabric.name;
        }
        return '面料#' + item.fabric_id;
      });
      if (names.length > 2) {
        fabricSummary = names.slice(0, 2).join('、') + ' 等' + names.length + '种面料';
      } else {
        fabricSummary = names.join('、');
      }
    }

    order.fabricSummary = fabricSummary || '面料订单';
    order.statusText = this.data.statusTextMap[order.status] || order.status;
    order.statusType = this.data.statusTypeMap[order.status] || 'info';

    // 提取对方公司名
    var counterpartyName = '';
    if (role === 'admin') {
      // admin 角色：counterparty 是对象，显示买卖双方
      if (order.counterparty && typeof order.counterparty === 'object') {
        var buyerName = order.counterparty.buyer_company_name || '';
        var supplierName = order.counterparty.supplier_company_name || '';
        counterpartyName = buyerName && supplierName ? buyerName + ' ↔ ' + supplierName : buyerName || supplierName;
      }
    } else {
      // buyer/supplier 角色：counterparty 是字符串
      if (order.counterparty && typeof order.counterparty === 'string') {
        counterpartyName = order.counterparty;
      }
    }
    order.counterpartyName = counterpartyName;

    return order;
  }
});
