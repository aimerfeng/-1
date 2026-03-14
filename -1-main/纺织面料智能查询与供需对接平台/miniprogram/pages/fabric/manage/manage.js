// pages/fabric/manage/manage.js
var request = require('../../../utils/request');

Page({
  data: {
    loading: false,
    fabrics: [],
    page: 1,
    total: 0,
    hasMore: true
  },

  onLoad: function () {
    this._loaded = false;
    this._loadFabrics();
  },

  onShow: function () {
    // 仅从其他页面返回时刷新，避免首次进入重复加载
    if (this._loaded) {
      this._loadFabrics();
    }
  },

  onReachBottom: function () {
    if (this.data.hasMore && !this.data.loading) {
      this.setData({ page: this.data.page + 1 });
      this._loadFabrics(true);
    }
  },

  _loadFabrics: function (append) {
    var that = this;
    var page = append ? this.data.page : 1;
    if (!append) {
      this.setData({ page: 1 });
    }
    this.setData({ loading: true });

    request.get('/fabrics/mine', { page: page, per_page: 20 }).then(function (res) {
      var items = res.items || [];
      var list = append ? that.data.fabrics.concat(items) : items;
      that._loaded = true;
      that.setData({
        loading: false,
        fabrics: list,
        total: res.total || 0,
        hasMore: list.length < (res.total || 0)
      });
    }).catch(function () {
      that.setData({ loading: false });
    });
  },

  goPublish: function () {
    wx.navigateTo({ url: '/pages/fabric/publish/publish' });
  },

  goEdit: function (e) {
    var id = e.currentTarget.dataset.id;
    wx.navigateTo({ url: '/pages/fabric/publish/publish?id=' + id });
  },

  goDetail: function (e) {
    var id = e.currentTarget.dataset.id;
    wx.navigateTo({ url: '/pages/fabric/detail/detail?id=' + id });
  }
});
