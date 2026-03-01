/**
 * pages/fabric/detail/detail.js - 面料详情页面
 * 展示面料完整参数、图片轮播、收藏、申请样品、立即下单
 * 需求: 4.3, 4.4, 10.4
 */
var request = require('../../../utils/request.js');
var auth = require('../../../utils/auth.js');

Page({
  data: {
    /** 面料ID */
    fabricId: null,
    /** 面料详情数据 */
    fabric: null,
    /** 是否正在加载 */
    loading: true,
    /** 加载失败 */
    loadError: false,
    /** 当前轮播索引 */
    swiperCurrent: 0,
    /** 是否已收藏 */
    isFavorited: false,
    /** 收藏操作中 */
    favLoading: false,
    /** 页面是否已就绪（用于入场动效） */
    pageReady: false,

    /** 面料参数列表（用于展示） */
    paramList: []
  },

  onLoad: function (options) {
    var id = options.id;
    if (!id) {
      wx.showToast({ title: '参数错误', icon: 'none' });
      setTimeout(function () {
        wx.navigateBack();
      }, 1500);
      return;
    }
    this.setData({ fabricId: id });
    this._loadFabricDetail(id);
  },

  onShow: function () {
    // 每次显示时刷新收藏状态（从其他页面返回时可能已变化）
    if (this.data.fabricId && !this.data.loading) {
      this._checkFavoriteStatus(this.data.fabricId);
    }
  },

  /**
   * 加载面料详情
   * @param {string|number} id - 面料ID
   */
  _loadFabricDetail: function (id) {
    var that = this;
    this.setData({ loading: true, loadError: false });

    request.get('/fabrics/' + id).then(function (res) {
      var fabric = res;
      // 确保 images 是数组
      if (!fabric.images || !Array.isArray(fabric.images)) {
        fabric.images = [];
      }

      var paramList = that._buildParamList(fabric);

      that.setData({
        fabric: fabric,
        paramList: paramList,
        loading: false
      });

      // 延迟触发入场动效
      setTimeout(function () {
        that.setData({ pageReady: true });
      }, 50);

      // 检查收藏状态
      that._checkFavoriteStatus(id);
    }).catch(function (err) {
      that.setData({
        loading: false,
        loadError: true
      });
      wx.showToast({
        title: (err && err.message) || '加载失败',
        icon: 'none'
      });
    });
  },

  /**
   * 构建参数展示列表
   * @param {Object} fabric - 面料数据
   * @returns {Array} 参数列表
   */
  _buildParamList: function (fabric) {
    var params = [];

    params.push({ label: '成分', value: fabric.composition || '-', icon: '🧵' });
    params.push({ label: '克重', value: fabric.weight ? fabric.weight + ' g/m²' : '-', icon: '⚖' });
    params.push({ label: '幅宽', value: fabric.width ? fabric.width + ' cm' : '-', icon: '📏' });
    params.push({ label: '工艺', value: fabric.craft || '-', icon: '🔧' });
    params.push({ label: '颜色', value: fabric.color || '-', icon: '🎨' });
    params.push({ label: '价格', value: fabric.price ? '¥' + fabric.price + '/米' : '-', icon: '💰' });
    params.push({ label: '最小起订量', value: fabric.min_order_qty ? fabric.min_order_qty + ' 米' : '-', icon: '📦' });
    params.push({ label: '库存量', value: fabric.stock_quantity ? fabric.stock_quantity + ' 米' : '-', icon: '🏭' });
    params.push({ label: '交货周期', value: fabric.delivery_days ? fabric.delivery_days + ' 天' : '-', icon: '🚚' });

    return params;
  },

  /**
   * 检查收藏状态
   * @param {string|number} id - 面料ID
   */
  _checkFavoriteStatus: function (id) {
    var that = this;
    if (!auth.isLoggedIn()) {
      return;
    }

    request.get('/fabrics/favorites', { page: 1, per_page: 100 }, { showError: false }).then(function (res) {
      var favorites = res.items || res || [];
      var isFavorited = false;
      for (var i = 0; i < favorites.length; i++) {
        if (String(favorites[i].fabric_id) === String(id)) {
          isFavorited = true;
          break;
        }
      }
      that.setData({ isFavorited: isFavorited });
    }).catch(function () {
      // 静默失败，不影响页面展示
    });
  },

  /**
   * 轮播图切换
   */
  onSwiperChange: function (e) {
    this.setData({
      swiperCurrent: e.detail.current
    });
  },

  /**
   * 点击图片放大预览
   */
  onImagePreview: function (e) {
    var current = e.currentTarget.dataset.src;
    var urls = this.data.fabric.images || [];
    if (urls.length === 0) return;

    wx.previewImage({
      current: current,
      urls: urls
    });
  },

  /**
   * 切换收藏状态
   */
  onToggleFavorite: function () {
    if (!auth.isLoggedIn()) {
      wx.showToast({ title: '请先登录', icon: 'none' });
      return;
    }

    if (this.data.favLoading) return;

    var that = this;
    var fabricId = this.data.fabricId;
    var isFavorited = this.data.isFavorited;

    this.setData({ favLoading: true });

    if (isFavorited) {
      // 取消收藏
      request.del('/fabrics/' + fabricId + '/favorite').then(function () {
        that.setData({
          isFavorited: false,
          favLoading: false
        });
        wx.showToast({ title: '已取消收藏', icon: 'none' });
      }).catch(function () {
        that.setData({ favLoading: false });
      });
    } else {
      // 添加收藏
      request.post('/fabrics/' + fabricId + '/favorite').then(function () {
        that.setData({
          isFavorited: true,
          favLoading: false
        });
        wx.showToast({ title: '收藏成功', icon: 'success' });
      }).catch(function () {
        that.setData({ favLoading: false });
      });
    }
  },

  /**
   * 申请样品
   */
  onRequestSample: function () {
    if (!auth.isLoggedIn()) {
      wx.showToast({ title: '请先登录', icon: 'none' });
      return;
    }
    var fabricId = this.data.fabricId;
    var fabricName = (this.data.fabric && this.data.fabric.name) || '';
    wx.navigateTo({
      url: '/pages/sample/sample?fabric_id=' + fabricId +
        (fabricName ? '&fabric_name=' + encodeURIComponent(fabricName) : '')
    });
  },

  /**
   * 立即下单
   */
  onPlaceOrder: function () {
    if (!auth.isLoggedIn()) {
      wx.showToast({ title: '请先登录', icon: 'none' });
      return;
    }
    var fabricId = this.data.fabricId;
    wx.navigateTo({
      url: '/pages/order/create/create?fabric_id=' + fabricId
    });
  },

  /**
   * 重试加载
   */
  onRetry: function () {
    if (this.data.fabricId) {
      this._loadFabricDetail(this.data.fabricId);
    }
  },

  /**
   * 分享
   */
  onShareAppMessage: function () {
    var fabric = this.data.fabric;
    return {
      title: fabric ? fabric.name : '面料详情',
      path: '/pages/fabric/detail/detail?id=' + this.data.fabricId
    };
  }
});
