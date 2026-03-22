/**
 * pages/order/detail/detail.js - 订单详情页面
 * 展示订单完整信息：订单号、面料明细、总金额、收货地址
 * 展示订单状态时间线（纵向步骤条，标注各状态时间）
 * 供应商可操作更新状态按钮（根据当前状态展示下一步操作）
 * 需求: 7.5, 7.6
 */
var request = require('../../../utils/request');
var auth = require('../../../utils/auth');

Page({
  data: {
    /** 订单ID（从页面参数获取） */
    orderId: null,
    /** 订单详情数据 */
    order: null,
    /** 是否正在加载 */
    loading: true,
    /** 加载失败 */
    loadError: false,

    /** 当前用户角色: buyer / supplier */
    role: '',
    /** 当前用户ID */
    userId: null,

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
    },

    /** 状态图标映射 */
    statusIconMap: {
      'pending': '📋',
      'confirmed': '✅',
      'producing': '🏭',
      'shipped': '🚚',
      'received': '📦',
      'completed': '🎉'
    },

    /** 状态时间线数据 */
    timeline: [],

    /** 下一步操作按钮信息（null 表示无可操作按钮） */
    nextAction: null,

    /** 是否正在更新状态 */
    updatingStatus: false,

    /** 是否显示状态更新确认弹窗 */
    showConfirm: false,
    /** 确认弹窗中的目标状态 */
    confirmTargetStatus: '',
    /** 确认弹窗中的目标状态文本 */
    confirmTargetText: '',

    /** 需求信息（来自 API 的 demand_info） */
    demandInfo: null,
    /** 报价信息（来自 API 的 quote_info） */
    quoteInfo: null,
    /** 物流单号输入值 */
    trackingNoInput: ''
  },

  onLoad: function (options) {
    var orderId = options.id;
    if (!orderId) {
      wx.showToast({ title: '参数错误', icon: 'none' });
      setTimeout(function () {
        wx.navigateBack();
      }, 1500);
      return;
    }

    var userInfo = auth.getUserInfo();
    var role = auth.getUserRole() || 'buyer';
    var userId = userInfo ? userInfo.id : null;

    this.setData({
      orderId: orderId,
      role: role,
      userId: userId
    });

    this._loadOrderDetail();
  },

  onShow: function () {
    // 页面再次显示时可刷新数据
  },

  /**
   * 下拉刷新
   */
  onPullDownRefresh: function () {
    this._loadOrderDetail();
  },

  // ============================================================
  // 数据加载
  // ============================================================

  /**
   * 加载订单详情
   */
  _loadOrderDetail: function () {
    var that = this;
    this.setData({ loading: true, loadError: false });

    request.get('/orders/' + this.data.orderId).then(function (res) {
      var order = res;

      // 处理状态文本
      order.statusText = that.data.statusTextMap[order.status] || order.status;
      order.statusType = that.data.statusTypeMap[order.status] || 'info';

      // 处理时间线数据
      var timeline = that._buildTimeline(order);

      // 计算下一步操作
      var nextAction = that._getNextAction(order);

      // 提取需求信息和报价信息
      var demandInfo = order.demand_info || null;
      var quoteInfo = order.quote_info || null;

      that.setData({
        order: order,
        timeline: timeline,
        nextAction: nextAction,
        demandInfo: demandInfo,
        quoteInfo: quoteInfo,
        loading: false
      });

      wx.stopPullDownRefresh();
    }).catch(function () {
      that.setData({
        loading: false,
        loadError: true
      });
      wx.stopPullDownRefresh();
    });
  },

  /**
   * 重试加载
   */
  onRetry: function () {
    this._loadOrderDetail();
  },

  // ============================================================
  // 时间线构建
  // ============================================================

  /**
   * 构建状态时间线数据
   * @param {Object} order - 订单数据
   * @returns {Array} 时间线数据
   */
  _buildTimeline: function (order) {
    var statuses = ['pending', 'confirmed', 'producing', 'shipped', 'received', 'completed'];
    var statusTextMap = this.data.statusTextMap;
    var statusIconMap = this.data.statusIconMap;

    var currentIndex = -1;
    if (order.status) {
      currentIndex = statuses.indexOf(order.status);
    }

    var timeline = [];
    for (var i = 0; i < statuses.length; i++) {
      var status = statuses[i];

      var item = {
        status: status,
        text: statusTextMap[status] || status,
        icon: statusIconMap[status] || '○',
        completed: i <= currentIndex,
        current: i === currentIndex,
        future: i > currentIndex
      };

      // 为已完成的步骤添加时间标注
      if (item.completed && i === 0 && order.created_at) {
        item.time = this._formatTime(order.created_at);
      } else if (item.current && order.updated_at) {
        item.time = this._formatTime(order.updated_at);
      } else if (item.completed && !item.current) {
        // 已完成但非当前步骤，无精确时间
        item.time = '';
      } else {
        item.time = '';
      }

      timeline.push(item);
    }

    // 为第一步（待确认）设置创建时间
    if (timeline.length > 0 && order.created_at) {
      timeline[0].time = this._formatTime(order.created_at);
    }
    // 为当前步骤设置更新时间
    if (currentIndex > 0 && order.updated_at) {
      timeline[currentIndex].time = this._formatTime(order.updated_at);
    }

    return timeline;
  },

  /**
   * 格式化时间字符串
   * @param {string} timeStr - ISO 时间字符串
   * @returns {string} 格式化后的时间
   */
  _formatTime: function (timeStr) {
    if (!timeStr) return '';
    try {
      var date = new Date(timeStr);
      if (isNaN(date.getTime())) return timeStr;

      var year = date.getFullYear();
      var month = ('0' + (date.getMonth() + 1)).slice(-2);
      var day = ('0' + date.getDate()).slice(-2);
      var hours = ('0' + date.getHours()).slice(-2);
      var minutes = ('0' + date.getMinutes()).slice(-2);

      return year + '-' + month + '-' + day + ' ' + hours + ':' + minutes;
    } catch (e) {
      return timeStr;
    }
  },

  // ============================================================
  // 操作按钮逻辑
  // ============================================================

  /**
   * 根据当前订单状态和用户角色，计算下一步可操作按钮
   * @param {Object} order - 订单数据
   * @returns {Object|null} 操作按钮信息
   */
  _getNextAction: function (order) {
    var role = this.data.role;
    var status = order.status;

    // Admin 只读，无操作按钮
    if (role === 'admin') {
      return null;
    }

    // 供应商可操作的状态转换
    var supplierActions = {
      'pending': { nextStatus: 'confirmed', text: '确认订单', icon: '✅' },
      'confirmed': { nextStatus: 'producing', text: '开始生产', icon: '🏭' },
      'producing': { nextStatus: 'shipped', text: '确认发货', icon: '🚚' }
    };

    // 采购方可操作的状态转换（buyer 可以确认收货和完成订单）
    var buyerActions = {
      'shipped': { nextStatus: 'received', text: '确认收货', icon: '📦' },
      'received': { nextStatus: 'completed', text: '完成订单', icon: '🎉' }
    };

    if (role === 'supplier' && supplierActions[status]) {
      return supplierActions[status];
    }

    if (role === 'buyer' && buyerActions[status]) {
      return buyerActions[status];
    }

    return null;
  },

  /**
   * 点击操作按钮 - 弹出确认弹窗
   */
  onActionTap: function () {
    var nextAction = this.data.nextAction;
    if (!nextAction || this.data.updatingStatus) return;

    this.setData({
      showConfirm: true,
      confirmTargetStatus: nextAction.nextStatus,
      confirmTargetText: nextAction.text
    });
  },

  /**
   * 确认更新状态
   */
  onConfirmUpdate: function () {
    var that = this;
    var targetStatus = this.data.confirmTargetStatus;

    // 发货时需要物流单号
    if (targetStatus === 'shipped' && !this.data.trackingNoInput) {
      wx.showToast({ title: '请输入物流单号', icon: 'none' });
      return;
    }

    this.setData({
      showConfirm: false,
      updatingStatus: true
    });

    var body = {
      status: targetStatus
    };

    // 发货时附带物流单号
    if (targetStatus === 'shipped' && this.data.trackingNoInput) {
      body.tracking_no = this.data.trackingNoInput;
    }

    request.put('/orders/' + this.data.orderId + '/status', body, {
      showLoading: true,
      loadingText: '正在更新...'
    }).then(function () {
      wx.showToast({
        title: '状态更新成功',
        icon: 'success'
      });
      // 重新加载订单详情
      that.setData({ updatingStatus: false, trackingNoInput: '' });
      that._loadOrderDetail();
    }).catch(function () {
      that.setData({ updatingStatus: false });
    });
  },

  /**
   * 取消确认弹窗
   */
  onCancelConfirm: function () {
    this.setData({
      showConfirm: false,
      confirmTargetStatus: '',
      confirmTargetText: '',
      trackingNoInput: ''
    });
  },

  /**
   * 物流单号输入事件
   */
  onTrackingNoInput: function (e) {
    this.setData({
      trackingNoInput: e.detail.value
    });
  },

  /**
   * 阻止弹窗下层滚动
   */
  preventTouchMove: function () {
    // 空函数，仅用于阻止冒泡
  },

  // ============================================================
  // 导航
  // ============================================================

  /**
   * 返回订单列表
   */
  goToOrderList: function () {
    wx.navigateBack({
      fail: function () {
        wx.redirectTo({
          url: '/pages/order/list/list'
        });
      }
    });
  }
});
