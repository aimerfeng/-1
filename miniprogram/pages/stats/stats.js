var request = require('../../utils/request');
var auth = require('../../utils/auth');

Page({
  data: {
    loading: true,
    isAdmin: false,
    stats: {
      userCount: 0,
      fabricCount: 0,
      demandCount: 0,
      orderCount: 0,
      conversationCount: 0,
      favoriteCount: 0
    },
    trendDays: [],
    trendOrders: [],
    trendMax: 1
  },

  onLoad: function () {
    this.loadStats();
  },

  onPullDownRefresh: function () {
    this.loadStats();
  },

  loadStats: function () {
    if (!auth.isLoggedIn()) {
      this.setData({ loading: true, isAdmin: false });
      this._loadGuestStats();
      return;
    }
    var role = auth.getUserRole();
    var isAdmin = role === 'admin';
    this.setData({ loading: true, isAdmin: isAdmin });
    if (isAdmin) {
      this._loadAdminStats();
      return;
    }
    this._loadCommonStats();
  },

  _loadGuestStats: function () {
    var that = this;
    var stats = {
      userCount: 0,
      fabricCount: 0,
      demandCount: 0,
      orderCount: 0,
      conversationCount: 0,
      favoriteCount: 0
    };
    var done = 0;

    function finishOne() {
      done += 1;
      if (done >= 2) {
        that.setData({
          loading: false,
          stats: stats,
          trendDays: [],
          trendOrders: [],
          trendMax: 1
        });
        wx.stopPullDownRefresh();
      }
    }

    request.get('/fabrics', { page: 1, per_page: 1 }, { showError: false }).then(function (res) {
      stats.fabricCount = res.total || 0;
      finishOne();
    }).catch(function () {
      stats.fabricCount = 0;
      finishOne();
    });

    request.get('/demands', { page: 1, per_page: 1 }, { showError: false }).then(function (res) {
      stats.demandCount = res.total || 0;
      finishOne();
    }).catch(function () {
      stats.demandCount = 0;
      finishOne();
    });
  },

  _loadCommonStats: function () {
    var that = this;
    var metrics = [
      { key: 'fabricCount', url: '/fabrics' },
      { key: 'demandCount', url: '/demands' },
      { key: 'orderCount', url: '/orders' },
      { key: 'conversationCount', url: '/conversations' },
      { key: 'favoriteCount', url: '/fabrics/favorites' }
    ];
    var stats = {
      userCount: 0,
      fabricCount: 0,
      demandCount: 0,
      orderCount: 0,
      conversationCount: 0,
      favoriteCount: 0
    };
    var done = 0;

    function finishOne() {
      done += 1;
      if (done >= metrics.length) {
        that.setData({
          loading: false,
          stats: stats,
          trendDays: [],
          trendOrders: [],
          trendMax: 1
        });
        wx.stopPullDownRefresh();
      }
    }

    metrics.forEach(function (item) {
      request.get(item.url, { page: 1, per_page: 1 }, { showError: false }).then(function (res) {
        stats[item.key] = res.total || 0;
        finishOne();
      }).catch(function () {
        stats[item.key] = 0;
        finishOne();
      });
    });
  },

  _loadAdminStats: function () {
    var that = this;
    request.get('/admin/stats', {}, { showError: false }).then(function (res) {
      var overview = res.overview || {};
      var trends = res.trends || {};
      var trendOrders = trends.new_orders || [];
      var trendDays = trends.days || [];
      var trendMax = 1;
      for (var i = 0; i < trendOrders.length; i++) {
        if (trendOrders[i] > trendMax) trendMax = trendOrders[i];
      }
      that.setData({
        loading: false,
        stats: {
          userCount: overview.total_users || 0,
          fabricCount: overview.total_fabrics || 0,
          demandCount: overview.total_demands || 0,
          orderCount: overview.total_orders || 0,
          conversationCount: 0,
          favoriteCount: 0
        },
        trendDays: trendDays,
        trendOrders: trendOrders,
        trendMax: trendMax
      });
      wx.stopPullDownRefresh();
    }).catch(function () {
      that._loadCommonStats();
    });
  },

  goHome: function () {
    wx.switchTab({
      url: '/pages/home/home'
    });
  }
});
