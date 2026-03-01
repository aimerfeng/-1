/**
 * pages/demand/detail/detail.js - 需求详情页
 * 展示需求完整信息，供应商可提交报价
 */
var request = require('../../../utils/request.js');
var auth = require('../../../utils/auth.js');

Page({
  data: {
    demandId: null,
    demand: null,
    loading: true,
    userRole: '',
    // 报价相关
    showQuoteModal: false,
    quotePrice: '',
    quoteDeliveryDays: '',
    quoteMessage: '',
    quoteSubmitting: false,
    myQuote: null,
    quoteCount: 0,
    // 报价列表（采购方可见）
    quoteList: [],
    quotesLoading: false
  },

  onLoad: function (options) {
    var id = options.id;
    if (!id) {
      wx.showToast({ title: '参数错误', icon: 'none' });
      return;
    }
    this.setData({
      demandId: parseInt(id, 10),
      userRole: auth.getUserRole() || ''
    });
    this._loadDetail();
  },

  onPullDownRefresh: function () {
    this._loadDetail(true);
  },

  _loadDetail: function (isRefresh) {
    var that = this;
    if (!isRefresh) this.setData({ loading: true });

    request.get('/demands/' + this.data.demandId).then(function (res) {
      that.setData({
        demand: that._formatDemand(res),
        myQuote: res.my_quote || null,
        quoteCount: res.quote_count || 0,
        loading: false
      });
      if (isRefresh) wx.stopPullDownRefresh();

      // 采购方加载报价列表
      if (that.data.userRole === 'buyer') {
        that._loadQuotes();
      }
    }).catch(function () {
      that.setData({ loading: false });
      if (isRefresh) wx.stopPullDownRefresh();
      wx.showToast({ title: '加载失败', icon: 'none' });
    });
  },

  _formatDemand: function (d) {
    var statusMap = { 'open': '进行中', 'closed': '已关闭', 'matched': '已匹配' };
    d._statusText = statusMap[d.status] || d.status || '';
    // 参数列表
    d._params = [];
    if (d.composition) d._params.push({ label: '成分要求', value: d.composition });
    if (d.weight_min || d.weight_max) {
      var w = '';
      if (d.weight_min && d.weight_max) w = d.weight_min + ' - ' + d.weight_max + ' g/m²';
      else if (d.weight_min) w = '≥' + d.weight_min + ' g/m²';
      else w = '≤' + d.weight_max + ' g/m²';
      d._params.push({ label: '克重范围', value: w });
    }
    if (d.width_min || d.width_max) {
      var wd = '';
      if (d.width_min && d.width_max) wd = d.width_min + ' - ' + d.width_max + ' cm';
      else if (d.width_min) wd = '≥' + d.width_min + ' cm';
      else wd = '≤' + d.width_max + ' cm';
      d._params.push({ label: '幅宽范围', value: wd });
    }
    if (d.craft) d._params.push({ label: '工艺要求', value: d.craft });
    if (d.color) d._params.push({ label: '颜色偏好', value: d.color });
    if (d.price_min || d.price_max) {
      var p = '';
      if (d.price_min && d.price_max) p = '¥' + d.price_min + ' - ¥' + d.price_max + '/米';
      else if (d.price_min) p = '≥¥' + d.price_min + '/米';
      else p = '≤¥' + d.price_max + '/米';
      d._params.push({ label: '价格区间', value: p });
    }
    if (d.quantity) d._params.push({ label: '采购数量', value: d.quantity + ' 米' });
    if (d.created_at) d._timeText = d.created_at.substring(0, 16).replace('T', ' ');
    return d;
  },

  _loadQuotes: function () {
    var that = this;
    this.setData({ quotesLoading: true });
    request.get('/demands/' + this.data.demandId + '/quotes').then(function (res) {
      var items = (res.items || []).map(function (q) {
        if (q.created_at) q._timeText = q.created_at.substring(0, 16).replace('T', ' ');
        q._supplierName = (q.supplier_info && q.supplier_info.company_name) || '供应商';
        return q;
      });
      that.setData({ quoteList: items, quotesLoading: false });
    }).catch(function () {
      that.setData({ quotesLoading: false });
    });
  },

  // 报价弹窗
  showQuote: function () {
    if (this.data.myQuote) {
      wx.showToast({ title: '您已提交过报价', icon: 'none' });
      return;
    }
    this.setData({ showQuoteModal: true });
  },

  hideQuote: function () {
    this.setData({ showQuoteModal: false });
  },

  onQuotePriceInput: function (e) {
    this.setData({ quotePrice: e.detail.value });
  },

  onQuoteDaysInput: function (e) {
    this.setData({ quoteDeliveryDays: e.detail.value });
  },

  onQuoteMessageInput: function (e) {
    this.setData({ quoteMessage: e.detail.value });
  },

  submitQuote: function () {
    var that = this;
    var price = parseFloat(this.data.quotePrice);
    if (!price || price <= 0) {
      wx.showToast({ title: '请输入有效报价', icon: 'none' });
      return;
    }

    var data = { price: price };
    if (this.data.quoteDeliveryDays) {
      data.delivery_days = parseInt(this.data.quoteDeliveryDays, 10);
    }
    if (this.data.quoteMessage) {
      data.message = this.data.quoteMessage;
    }

    this.setData({ quoteSubmitting: true });

    request.post('/demands/' + this.data.demandId + '/quotes', data).then(function (res) {
      that.setData({
        quoteSubmitting: false,
        showQuoteModal: false,
        myQuote: res,
        quotePrice: '',
        quoteDeliveryDays: '',
        quoteMessage: ''
      });
      wx.showToast({ title: '报价提交成功', icon: 'success' });
    }).catch(function () {
      that.setData({ quoteSubmitting: false });
    });
  },

  preventTouchMove: function () {},

  /**
   * 接受报价 - 采购方接受供应商报价，自动创建订单
   */
  acceptQuote: function (e) {
    var that = this;
    var quoteId = e.currentTarget.dataset.id;
    if (!quoteId) return;

    wx.showModal({
      title: '确认接受报价',
      content: '确认接受此报价？接受后将自动创建订单',
      confirmText: '确认',
      cancelText: '取消',
      success: function (res) {
        if (!res.confirm) return;

        wx.showLoading({ title: '处理中...', mask: true });

        request.put('/demands/' + that.data.demandId + '/quotes/' + quoteId + '/accept').then(function (res) {
          wx.hideLoading();
          wx.showToast({ title: '订单创建成功', icon: 'success' });

          // 刷新需求详情和报价列表
          that._loadDetail();

          // 延迟跳转到订单详情页
          var orderId = res.order && res.order.id;
          if (orderId) {
            setTimeout(function () {
              wx.navigateTo({
                url: '/pages/order/detail/detail?id=' + orderId
              });
            }, 1500);
          }
        }).catch(function (err) {
          wx.hideLoading();
          wx.showToast({
            title: (err && err.message) || '操作失败',
            icon: 'none'
          });
        });
      }
    });
  }
});
