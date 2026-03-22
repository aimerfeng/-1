/**
 * pages/demand/publish/publish.js - 需求发布页面
 * 实现采购需求表单：标题、成分要求、克重范围、幅宽范围、工艺要求、颜色偏好、价格区间、数量
 * 表单验证和提交成功反馈
 * 需求: 5.1
 */
var request = require('../../../utils/request.js');
var auth = require('../../../utils/auth.js');

Page({
  data: {
    /** 表单数据 */
    form: {
      title: '',
      composition: '',
      weightMin: '',
      weightMax: '',
      widthMin: '',
      widthMax: '',
      craft: '',
      color: '',
      priceMin: '',
      priceMax: '',
      quantity: ''
    },

    /** 表单错误信息 */
    errors: {
      title: '',
      weightRange: '',
      widthRange: '',
      priceRange: '',
      quantity: ''
    },

    /** 成分选项列表 */
    compositionOptions: ['全棉', '涤纶', '涤棉', '锦纶', '真丝', '亚麻', '羊毛', '莫代尔', '其他'],
    compositionIndex: -1,

    /** 工艺选项列表 */
    craftOptions: ['平纹', '斜纹', '缎纹', '针织', '梭织', '提花', '印花', '染色', '其他'],
    craftIndex: -1,

    /** 预设颜色列表 */
    colorOptions: [
      { name: '白色', value: '白色', hex: '#FFFFFF' },
      { name: '黑色', value: '黑色', hex: '#000000' },
      { name: '红色', value: '红色', hex: '#E74C3C' },
      { name: '蓝色', value: '蓝色', hex: '#3498DB' },
      { name: '绿色', value: '绿色', hex: '#27AE60' },
      { name: '黄色', value: '黄色', hex: '#F1C40F' },
      { name: '灰色', value: '灰色', hex: '#95A5A6' },
      { name: '米色', value: '米色', hex: '#F5E6CC' },
      { name: '粉色', value: '粉色', hex: '#FADBD8' },
      { name: '紫色', value: '紫色', hex: '#8E44AD' }
    ],
    selectedColor: '',

    /** 提交状态 */
    submitting: false,

    /** 提交成功弹窗 */
    showSuccess: false,
    matchCount: 0
  },

  onLoad: function () {
    // 检查登录状态
    if (!auth.requireAuth('/pages/demand/publish/publish')) {
      return;
    }
  },

  onShow: function () {
    // 每次显示时重新检查登录状态
    if (!auth.isLoggedIn()) {
      auth.requireAuth('/pages/demand/publish/publish');
    }
  },

  // ============================================================
  // 表单输入事件
  // ============================================================

  onTitleInput: function (e) {
    this.setData({
      'form.title': e.detail.value,
      'errors.title': ''
    });
  },

  onCompositionChange: function (e) {
    var index = parseInt(e.detail.value, 10);
    var value = this.data.compositionOptions[index] || '';
    this.setData({
      compositionIndex: index,
      'form.composition': value
    });
  },

  onWeightMinInput: function (e) {
    this.setData({
      'form.weightMin': e.detail.value,
      'errors.weightRange': ''
    });
  },

  onWeightMaxInput: function (e) {
    this.setData({
      'form.weightMax': e.detail.value,
      'errors.weightRange': ''
    });
  },

  onWidthMinInput: function (e) {
    this.setData({
      'form.widthMin': e.detail.value,
      'errors.widthRange': ''
    });
  },

  onWidthMaxInput: function (e) {
    this.setData({
      'form.widthMax': e.detail.value,
      'errors.widthRange': ''
    });
  },

  onCraftChange: function (e) {
    var index = parseInt(e.detail.value, 10);
    var value = this.data.craftOptions[index] || '';
    this.setData({
      craftIndex: index,
      'form.craft': value
    });
  },

  onColorSelect: function (e) {
    var color = e.currentTarget.dataset.color;
    var selectedColor = this.data.selectedColor === color ? '' : color;
    this.setData({
      selectedColor: selectedColor,
      'form.color': selectedColor
    });
  },

  onPriceMinInput: function (e) {
    this.setData({
      'form.priceMin': e.detail.value,
      'errors.priceRange': ''
    });
  },

  onPriceMaxInput: function (e) {
    this.setData({
      'form.priceMax': e.detail.value,
      'errors.priceRange': ''
    });
  },

  onQuantityInput: function (e) {
    this.setData({
      'form.quantity': e.detail.value,
      'errors.quantity': ''
    });
  },

  // ============================================================
  // 表单验证
  // ============================================================

  _validateForm: function () {
    var form = this.data.form;
    var errors = {
      title: '',
      weightRange: '',
      widthRange: '',
      priceRange: '',
      quantity: ''
    };
    var isValid = true;

    // 标题必填
    if (!form.title.trim()) {
      errors.title = '请输入需求标题';
      isValid = false;
    } else if (form.title.trim().length < 2) {
      errors.title = '标题至少2个字符';
      isValid = false;
    }

    // 克重范围验证
    if (form.weightMin && form.weightMax) {
      var wMin = parseFloat(form.weightMin);
      var wMax = parseFloat(form.weightMax);
      if (wMin < 0 || wMax < 0) {
        errors.weightRange = '克重不能为负数';
        isValid = false;
      } else if (wMin > wMax) {
        errors.weightRange = '最小克重不能大于最大克重';
        isValid = false;
      }
    } else if (form.weightMin && parseFloat(form.weightMin) < 0) {
      errors.weightRange = '克重不能为负数';
      isValid = false;
    } else if (form.weightMax && parseFloat(form.weightMax) < 0) {
      errors.weightRange = '克重不能为负数';
      isValid = false;
    }

    // 幅宽范围验证
    if (form.widthMin && form.widthMax) {
      var dMin = parseFloat(form.widthMin);
      var dMax = parseFloat(form.widthMax);
      if (dMin < 0 || dMax < 0) {
        errors.widthRange = '幅宽不能为负数';
        isValid = false;
      } else if (dMin > dMax) {
        errors.widthRange = '最小幅宽不能大于最大幅宽';
        isValid = false;
      }
    } else if (form.widthMin && parseFloat(form.widthMin) < 0) {
      errors.widthRange = '幅宽不能为负数';
      isValid = false;
    } else if (form.widthMax && parseFloat(form.widthMax) < 0) {
      errors.widthRange = '幅宽不能为负数';
      isValid = false;
    }

    // 价格区间验证
    if (form.priceMin && form.priceMax) {
      var pMin = parseFloat(form.priceMin);
      var pMax = parseFloat(form.priceMax);
      if (pMin < 0 || pMax < 0) {
        errors.priceRange = '价格不能为负数';
        isValid = false;
      } else if (pMin > pMax) {
        errors.priceRange = '最低价不能大于最高价';
        isValid = false;
      }
    } else if (form.priceMin && parseFloat(form.priceMin) < 0) {
      errors.priceRange = '价格不能为负数';
      isValid = false;
    } else if (form.priceMax && parseFloat(form.priceMax) < 0) {
      errors.priceRange = '价格不能为负数';
      isValid = false;
    }

    // 数量验证
    if (form.quantity) {
      var qty = parseInt(form.quantity, 10);
      if (isNaN(qty) || qty <= 0) {
        errors.quantity = '数量必须为正整数';
        isValid = false;
      }
    }

    this.setData({ errors: errors });
    return isValid;
  },

  // ============================================================
  // 提交表单
  // ============================================================

  handleSubmit: function () {
    if (this.data.submitting) {
      return;
    }

    // 提交前再次检查登录状态
    if (!auth.isLoggedIn()) {
      wx.showToast({ title: '请先登录', icon: 'none' });
      setTimeout(function () {
        wx.navigateTo({ url: '/pages/login/login' });
      }, 1000);
      return;
    }

    if (!this._validateForm()) {
      wx.showToast({
        title: '请检查表单信息',
        icon: 'none'
      });
      return;
    }

    var that = this;
    var form = this.data.form;

    // 构建请求数据
    var data = {
      title: form.title.trim()
    };

    if (form.composition) {
      data.composition = form.composition;
    }
    if (form.weightMin) {
      data.weight_min = parseFloat(form.weightMin);
    }
    if (form.weightMax) {
      data.weight_max = parseFloat(form.weightMax);
    }
    if (form.widthMin) {
      data.width_min = parseFloat(form.widthMin);
    }
    if (form.widthMax) {
      data.width_max = parseFloat(form.widthMax);
    }
    if (form.craft) {
      data.craft = form.craft;
    }
    if (form.color) {
      data.color = form.color;
    }
    if (form.priceMin) {
      data.price_min = parseFloat(form.priceMin);
    }
    if (form.priceMax) {
      data.price_max = parseFloat(form.priceMax);
    }
    if (form.quantity) {
      data.quantity = parseInt(form.quantity, 10);
    }

    this.setData({ submitting: true });

    request.post('/demands', data, {
      showLoading: true,
      loadingText: '正在发布...'
    }).then(function (res) {
      that.setData({
        submitting: false,
        showSuccess: true,
        matchCount: res.match_count || 0
      });
    }).catch(function (err) {
      that.setData({ submitting: false });
      // 处理后端返回的字段级错误
      if (err && err.errors) {
        var errors = that.data.errors;
        if (err.errors.title) {
          errors.title = err.errors.title;
        }
        that.setData({ errors: errors });
      }
    });
  },

  // ============================================================
  // 成功弹窗操作
  // ============================================================

  /** 查看匹配结果 */
  goToMatches: function () {
    this.setData({ showSuccess: false });
    // 返回上一页或跳转到需求列表
    wx.navigateBack({
      fail: function () {
        wx.switchTab({ url: '/pages/home/home' });
      }
    });
  },

  /** 继续发布 */
  continuePublish: function () {
    this.setData({
      showSuccess: false,
      matchCount: 0,
      form: {
        title: '',
        composition: '',
        weightMin: '',
        weightMax: '',
        widthMin: '',
        widthMax: '',
        craft: '',
        color: '',
        priceMin: '',
        priceMax: '',
        quantity: ''
      },
      errors: {
        title: '',
        weightRange: '',
        widthRange: '',
        priceRange: '',
        quantity: ''
      },
      compositionIndex: -1,
      craftIndex: -1,
      selectedColor: ''
    });
  },

  /** 阻止弹窗下层滚动 */
  preventTouchMove: function () {
    // 空函数，仅用于阻止冒泡
  }
});
