/**
 * pages/demand/list/list.js - 需求列表页面
 * 采购方查看自己发布的需求，供应商浏览所有公开需求
 */
var request = require('../../../utils/request.js');
var auth = require('../../../utils/auth.js');

Page({
  data: {
    /** 需求列表 */
    demandList: [],
    /** 是否正在加载 */
    loading: true,
    /** 加载更多中 */
    loadingMore: false,
    /** 是否还有更多数据 */
    hasMore: true,
    /** 当前页码 */
    page: 1,
    /** 每页条数 */
    perPage: 20,
    /** 总数 */
    total: 0,
    /** 用户角色 */
    userRole: '',
    /** 页面标题 */
    pageTitle: '需求列表',
    /** 页面描述 */
    pageDesc: ''
  },

  onLoad: function () {
    if (!auth.isLoggedIn()) {
      auth.requireAuth('/pages/demand/list/list');
      return;
    }
    var role = auth.getUserRole();
    var title = role === 'buyer' ? '我的需求' : '采购需求';
    var desc = role === 'buyer' ? '查看和管理您发布的采购需求' : '浏览采购方发布的需求，寻找合作机会';
    this.setData({
      userRole: role,
      pageTitle: title,
      pageDesc: desc
    });
    this._loadDemands();
  },

  onShow: function () {
    if (auth.isLoggedIn() && this.data.demandList.length > 0) {
      // 从其他页面返回时刷新
      this._refreshDemands();
    }
  },

  onPullDownRefresh: function () {
    this._refreshDemands();
  },

  onReachBottom: function () {
    if (this.data.hasMore && !this.data.loadingMore) {
      this._loadMore();
    }
  },

  _refreshDemands: function () {
    this.setData({ page: 1, hasMore: true });
    this._loadDemands(true);
  },

  _loadDemands: function (isRefresh) {
    var that = this;
    if (!isRefresh) {
      this.setData({ loading: true });
    }

    request.get('/demands', {
      page: this.data.page,
      per_page: this.data.perPage
    }).then(function (res) {
      var items = (res.items || []).map(function (item) {
        return that._formatDemand(item);
      });
      that.setData({
        demandList: items,
        total: res.total || 0,
        loading: false,
        hasMore: items.length >= that.data.perPage
      });
      if (isRefresh) wx.stopPullDownRefresh();
    }).catch(function () {
      that.setData({ loading: false });
      if (isRefresh) wx.stopPullDownRefresh();
    });
  },

  _loadMore: function () {
    var that = this;
    var nextPage = this.data.page + 1;
    this.setData({ loadingMore: true });

    request.get('/demands', {
      page: nextPage,
      per_page: this.data.perPage
    }).then(function (res) {
      var items = (res.items || []).map(function (item) {
        return that._formatDemand(item);
      });
      that.setData({
        demandList: that.data.demandList.concat(items),
        page: nextPage,
        loadingMore: false,
        hasMore: items.length >= that.data.perPage
      });
    }).catch(function () {
      that.setData({ loadingMore: false });
    });
  },

  _formatDemand: function (item) {
    // 状态文本
    var statusMap = {
      'open': '进行中',
      'closed': '已关闭',
      'matched': '已匹配'
    };
    item._statusText = statusMap[item.status] || item.status || '未知';
    item._statusClass = item.status === 'open' ? 'status--open' : 'status--closed';

    // 参数摘要
    var params = [];
    if (item.composition) params.push(item.composition);
    if (item.weight_min || item.weight_max) {
      var w = '';
      if (item.weight_min && item.weight_max) w = item.weight_min + '-' + item.weight_max + ' g/m²';
      else if (item.weight_min) w = '≥' + item.weight_min + ' g/m²';
      else w = '≤' + item.weight_max + ' g/m²';
      params.push(w);
    }
    if (item.craft) params.push(item.craft);
    if (item.color) params.push(item.color);
    item._paramSummary = params.join(' · ') || '暂无详细参数';

    // 价格
    if (item.price_min || item.price_max) {
      if (item.price_min && item.price_max) {
        item._priceText = '¥' + item.price_min + ' - ¥' + item.price_max + '/米';
      } else if (item.price_min) {
        item._priceText = '¥' + item.price_min + '起/米';
      } else {
        item._priceText = '≤¥' + item.price_max + '/米';
      }
    } else {
      item._priceText = '价格面议';
    }

    // 数量
    item._quantityText = item.quantity ? item.quantity + '米' : '';

    // 时间
    if (item.created_at) {
      item._timeText = item.created_at.substring(0, 10);
    }

    return item;
  },

  /** 点击需求项 */
  onDemandTap: function (e) {
    var id = e.currentTarget.dataset.id;
    if (!id) return;
    wx.navigateTo({ url: '/pages/demand/detail/detail?id=' + id });
  },

  /** 跳转发布需求 */
  goPublish: function () {
    wx.navigateTo({ url: '/pages/demand/publish/publish' });
  }
});
