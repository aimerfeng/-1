/**
 * pages/sample/sample.js - 样品管理页面
 * 采购方视角：样品申请列表、各状态展示、物流跟踪详情
 * 供应商视角：待审核列表、审核操作（通过/拒绝 + 拒绝原因输入）
 * 需求: 6.5, 10.3
 */
var request = require('../../utils/request');
var auth = require('../../utils/auth');

Page({
  data: {
    /** 用户角色: buyer / supplier */
    role: '',
    /** 样品列表数据 */
    sampleList: [],
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

    /** 状态中文映射 */
    statusTextMap: {
      'pending': '待审核',
      'approved': '已通过',
      'rejected': '已拒绝',
      'shipping': '运输中',
      'received': '已签收'
    },

    /** 供应商审核弹窗是否显示 */
    reviewModalVisible: false,
    /** 当前审核的样品 */
    reviewingSample: null,
    /** 拒绝原因输入 */
    rejectReason: '',
    /** 审核操作加载中 */
    reviewLoading: false,

    /** 物流详情弹窗是否显示 */
    logisticsModalVisible: false,
    /** 物流详情数据 */
    logisticsData: null,
    /** 物流加载中 */
    logisticsLoading: false,
    /** 当前查看物流的样品 */
    logisticsSample: null
  },

  onLoad: function () {
    var role = auth.getUserRole();
    this.setData({ role: role || 'buyer' });
    this._loadSamples(true);
  },

  onShow: function () {
    // 页面显示时可刷新数据
  },

  /**
   * 下拉刷新
   */
  onPullDownRefresh: function () {
    this._loadSamples(true);
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
   * 加载样品列表
   * @param {boolean} isRefresh - 是否为刷新（重置页码）
   */
  _loadSamples: function (isRefresh) {
    var that = this;

    if (isRefresh) {
      this.setData({
        page: 1,
        loading: true,
        hasMore: true,
        sampleList: []
      });
    }

    var params = {
      page: this.data.page,
      per_page: this.data.perPage
    };

    request.get('/samples', params).then(function (res) {
      var items = res.items || [];
      var total = res.total || 0;
      var currentPage = res.page || 1;
      var perPage = res.per_page || that.data.perPage;

      that.setData({
        sampleList: items,
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

    request.get('/samples', params).then(function (res) {
      var items = res.items || [];
      var total = res.total || 0;
      var currentPage = res.page || nextPage;
      var perPage = res.per_page || that.data.perPage;

      that.setData({
        sampleList: that.data.sampleList.concat(items),
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
   * 获取状态对应的自定义 type（覆盖 status-tag 默认映射）
   */
  _getStatusType: function (status) {
    var map = {
      'pending': 'warning',
      'approved': 'info',
      'rejected': 'danger',
      'shipping': 'primary',
      'received': 'success'
    };
    return map[status] || 'info';
  },

  /**
   * 获取状态对应的中文文本
   */
  _getStatusText: function (status) {
    return this.data.statusTextMap[status] || status;
  },

  // ============================================================
  // 供应商审核操作
  // ============================================================

  /**
   * 打开审核弹窗
   */
  onReviewTap: function (e) {
    var sample = e.currentTarget.dataset.sample;
    this.setData({
      reviewModalVisible: true,
      reviewingSample: sample,
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
      reviewingSample: null,
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
    var sample = this.data.reviewingSample;
    if (!sample) return;

    this.setData({ reviewLoading: true });

    request.put('/samples/' + sample.id + '/review', {
      status: 'approved'
    }).then(function () {
      wx.showToast({ title: '已通过审核', icon: 'success' });
      that.setData({
        reviewModalVisible: false,
        reviewingSample: null,
        reviewLoading: false
      });
      that._loadSamples(true);
    }).catch(function () {
      that.setData({ reviewLoading: false });
    });
  },

  /**
   * 审核拒绝
   */
  onReject: function () {
    var that = this;
    var sample = this.data.reviewingSample;
    if (!sample) return;

    var reason = this.data.rejectReason.trim();
    if (!reason) {
      wx.showToast({ title: '请输入拒绝原因', icon: 'none' });
      return;
    }

    this.setData({ reviewLoading: true });

    request.put('/samples/' + sample.id + '/review', {
      status: 'rejected',
      reject_reason: reason
    }).then(function () {
      wx.showToast({ title: '已拒绝申请', icon: 'success' });
      that.setData({
        reviewModalVisible: false,
        reviewingSample: null,
        rejectReason: '',
        reviewLoading: false
      });
      that._loadSamples(true);
    }).catch(function () {
      that.setData({ reviewLoading: false });
    });
  },

  // ============================================================
  // 物流跟踪（采购方）
  // ============================================================

  /**
   * 查看物流详情
   */
  onLogisticsTap: function (e) {
    var that = this;
    var sample = e.currentTarget.dataset.sample;
    if (!sample) return;

    this.setData({
      logisticsModalVisible: true,
      logisticsLoading: true,
      logisticsSample: sample,
      logisticsData: null
    });

    request.get('/samples/' + sample.id + '/logistics').then(function (res) {
      that.setData({
        logisticsData: res,
        logisticsLoading: false
      });
    }).catch(function () {
      that.setData({ logisticsLoading: false });
    });
  },

  /**
   * 关闭物流弹窗
   */
  closeLogisticsModal: function () {
    this.setData({
      logisticsModalVisible: false,
      logisticsSample: null,
      logisticsData: null
    });
  }
});
