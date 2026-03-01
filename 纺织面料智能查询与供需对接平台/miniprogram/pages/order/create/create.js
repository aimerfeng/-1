/**
 * pages/order/create/create.js - 订单创建页面
 * 实现订单表单：面料选择、数量输入、价格确认、收货地址填写
 * 实现金额自动计算（数量 × 单价）
 * 表单验证和提交确认弹窗
 * 需求: 7.1
 */
var request = require('../../../utils/request');
var auth = require('../../../utils/auth');

Page({
  data: {
    /** 面料ID（从页面参数获取） */
    fabricId: null,
    /** 面料详情数据 */
    fabric: null,
    /** 是否正在加载面料信息 */
    loading: true,
    /** 加载失败 */
    loadError: false,

    /** 表单数据 */
    form: {
      quantity: '',
      address: ''
    },

    /** 表单错误信息 */
    errors: {
      quantity: '',
      address: ''
    },

    /** 自动计算的总金额 */
    totalAmount: '0.00',

    /** 是否显示确认弹窗 */
    showConfirm: false,

    /** 提交状态 */
    submitting: false,

    /** 提交成功弹窗 */
    showSuccess: false,
    /** 创建成功后的订单ID */
    createdOrderId: null,
    /** 创建成功后的订单号 */
    createdOrderNo: ''
  },

  onLoad: function (options) {
    // 检查登录状态
    if (!auth.requireAuth('/pages/order/create/create?fabric_id=' + (options.fabric_id || ''))) {
      return;
    }

    var fabricId = options.fabric_id;
    if (!fabricId) {
      wx.showToast({ title: '参数错误', icon: 'none' });
      setTimeout(function () {
        wx.navigateBack();
      }, 1500);
      return;
    }

    this.setData({ fabricId: fabricId });
    this._loadFabricDetail(fabricId);
  },

  // ============================================================
  // 数据加载
  // ============================================================

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

      that.setData({
        fabric: fabric,
        loading: false
      });
    }).catch(function () {
      that.setData({
        loading: false,
        loadError: true
      });
    });
  },

  /**
   * 重试加载面料信息
   */
  onRetry: function () {
    if (this.data.fabricId) {
      this._loadFabricDetail(this.data.fabricId);
    }
  },

  // ============================================================
  // 表单输入事件
  // ============================================================

  /**
   * 数量输入
   */
  onQuantityInput: function (e) {
    var value = e.detail.value;
    this.setData({
      'form.quantity': value,
      'errors.quantity': ''
    });
    this._calculateTotal(value);
  },

  /**
   * 数量减少
   */
  onQuantityMinus: function () {
    var qty = parseInt(this.data.form.quantity, 10) || 0;
    var minQty = (this.data.fabric && this.data.fabric.min_order_qty) || 1;
    if (qty > minQty) {
      var newQty = String(qty - 1);
      this.setData({
        'form.quantity': newQty,
        'errors.quantity': ''
      });
      this._calculateTotal(newQty);
    }
  },

  /**
   * 数量增加
   */
  onQuantityPlus: function () {
    var qty = parseInt(this.data.form.quantity, 10) || 0;
    var newQty = String(qty + 1);
    this.setData({
      'form.quantity': newQty,
      'errors.quantity': ''
    });
    this._calculateTotal(newQty);
  },

  /**
   * 收货地址输入
   */
  onAddressInput: function (e) {
    this.setData({
      'form.address': e.detail.value,
      'errors.address': ''
    });
  },

  // ============================================================
  // 金额自动计算
  // ============================================================

  /**
   * 计算总金额 = 数量 × 单价
   * @param {string} quantityStr - 数量字符串
   */
  _calculateTotal: function (quantityStr) {
    var quantity = parseInt(quantityStr, 10);
    var price = this.data.fabric ? this.data.fabric.price : 0;

    if (!isNaN(quantity) && quantity > 0 && price > 0) {
      var total = (quantity * price).toFixed(2);
      this.setData({ totalAmount: total });
    } else {
      this.setData({ totalAmount: '0.00' });
    }
  },

  // ============================================================
  // 表单验证
  // ============================================================

  /**
   * 验证表单
   * @returns {boolean} 是否通过验证
   */
  _validateForm: function () {
    var form = this.data.form;
    var fabric = this.data.fabric;
    var errors = {
      quantity: '',
      address: ''
    };
    var isValid = true;

    // 数量验证
    if (!form.quantity || !form.quantity.trim()) {
      errors.quantity = '请输入采购数量';
      isValid = false;
    } else {
      var qty = parseInt(form.quantity, 10);
      if (isNaN(qty) || qty <= 0) {
        errors.quantity = '数量必须为正整数';
        isValid = false;
      } else if (fabric && fabric.min_order_qty && qty < fabric.min_order_qty) {
        errors.quantity = '最小起订量为 ' + fabric.min_order_qty + ' 米';
        isValid = false;
      }
    }

    // 收货地址验证
    if (!form.address || !form.address.trim()) {
      errors.address = '请填写收货地址';
      isValid = false;
    } else if (form.address.trim().length < 5) {
      errors.address = '请填写完整的收货地址';
      isValid = false;
    }

    this.setData({ errors: errors });
    return isValid;
  },

  // ============================================================
  // 提交流程
  // ============================================================

  /**
   * 点击提交按钮 - 先验证，再弹出确认弹窗
   */
  handleSubmit: function () {
    if (this.data.submitting) return;

    if (!this._validateForm()) {
      wx.showToast({
        title: '请检查表单信息',
        icon: 'none'
      });
      return;
    }

    // 显示确认弹窗
    this.setData({ showConfirm: true });
  },

  /**
   * 确认提交订单
   */
  onConfirmSubmit: function () {
    var that = this;
    var form = this.data.form;
    var fabric = this.data.fabric;

    this.setData({
      showConfirm: false,
      submitting: true
    });

    var data = {
      items: [
        {
          fabric_id: parseInt(that.data.fabricId, 10),
          quantity: parseInt(form.quantity, 10)
        }
      ],
      address: form.address.trim()
    };

    request.post('/orders', data, {
      showLoading: true,
      loadingText: '正在创建订单...'
    }).then(function (res) {
      that.setData({
        submitting: false,
        showSuccess: true,
        createdOrderId: res.id || null,
        createdOrderNo: res.order_no || ''
      });
    }).catch(function (err) {
      that.setData({ submitting: false });
      // 处理后端返回的字段级错误
      if (err && err.errors) {
        var errors = that.data.errors;
        if (err.errors.quantity) {
          errors.quantity = err.errors.quantity;
        }
        if (err.errors.address) {
          errors.address = err.errors.address;
        }
        that.setData({ errors: errors });
      }
    });
  },

  /**
   * 取消确认弹窗
   */
  onCancelConfirm: function () {
    this.setData({ showConfirm: false });
  },

  // ============================================================
  // 成功弹窗操作
  // ============================================================

  /**
   * 查看订单详情
   */
  goToOrderDetail: function () {
    var orderId = this.data.createdOrderId;
    this.setData({ showSuccess: false });
    if (orderId) {
      wx.redirectTo({
        url: '/pages/order/detail/detail?id=' + orderId
      });
    } else {
      wx.navigateBack();
    }
  },

  /**
   * 返回订单列表
   */
  goToOrderList: function () {
    this.setData({ showSuccess: false });
    wx.redirectTo({
      url: '/pages/order/list/list'
    });
  },

  /**
   * 阻止弹窗下层滚动
   */
  preventTouchMove: function () {
    // 空函数，仅用于阻止冒泡
  }
});
