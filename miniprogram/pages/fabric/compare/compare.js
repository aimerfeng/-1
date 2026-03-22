/**
 * pages/fabric/compare/compare.js - 面料对比页面
 * 实现横向滚动表格，并排展示多个面料的参数差异，高亮差异项
 * 需求: 4.5 - 以表格形式并排展示各面料的参数差异
 */
var request = require('../../../utils/request.js');

Page({
  data: {
    /** 面料 ID 列表 */
    ids: [],
    /** 面料数据列表 */
    fabrics: [],
    /** 是否正在加载 */
    loading: true,
    /** 是否加载失败 */
    loadError: false,
    /** 页面是否就绪（用于入场动效） */
    pageReady: false,

    /**
     * 参数行定义
     * 每行包含: label(中文标签), key(数据字段名), unit(单位), format(格式化类型)
     */
    paramRows: [
      { label: '成分', key: 'composition', unit: '', format: 'text' },
      { label: '克重', key: 'weight', unit: 'g/m²', format: 'number' },
      { label: '幅宽', key: 'width', unit: 'cm', format: 'number' },
      { label: '工艺', key: 'craft', unit: '', format: 'text' },
      { label: '颜色', key: 'color', unit: '', format: 'text' },
      { label: '价格', key: 'price', unit: '元/米', format: 'price' },
      { label: '最小起订量', key: 'min_order_qty', unit: '米', format: 'number' },
      { label: '交货周期', key: 'delivery_days', unit: '天', format: 'number' }
    ],

    /**
     * 差异标记映射: { paramKey: true/false }
     * true 表示该参数在各面料间存在差异
     */
    diffMap: {},

    /** 横向滚动位置同步 */
    scrollLeft: 0
  },

  onLoad: function (options) {
    if (options.ids) {
      var ids = options.ids.split(',').map(function (id) {
        return parseInt(id, 10);
      }).filter(function (id) {
        return !isNaN(id) && id > 0;
      });

      if (ids.length < 2) {
        wx.showToast({
          title: '请至少选择2个面料进行对比',
          icon: 'none'
        });
        setTimeout(function () {
          wx.navigateBack();
        }, 1500);
        return;
      }

      this.setData({ ids: ids });
      this._loadCompareData();
    } else {
      this.setData({ loading: false, loadError: true });
    }
  },

  /**
   * 加载面料对比数据
   */
  _loadCompareData: function () {
    var that = this;
    var idsStr = this.data.ids.join(',');

    this.setData({ loading: true, loadError: false });

    request.get('/fabrics/compare', { ids: idsStr }).then(function (res) {
      var items = res.items || [];

      if (items.length === 0) {
        that.setData({
          loading: false,
          loadError: true
        });
        wx.showToast({
          title: '未找到面料数据',
          icon: 'none'
        });
        return;
      }

      // 计算参数差异
      var diffMap = that._calculateDiffs(items);

      that.setData({
        fabrics: items,
        diffMap: diffMap,
        loading: false,
        loadError: false
      });

      // 延迟触发入场动效
      setTimeout(function () {
        that.setData({ pageReady: true });
      }, 50);
    }).catch(function () {
      that.setData({
        loading: false,
        loadError: true
      });
    });
  },

  /**
   * 计算各参数在面料间的差异
   * @param {Array} fabrics - 面料数据列表
   * @returns {Object} 差异映射 { paramKey: boolean }
   */
  _calculateDiffs: function (fabrics) {
    var paramRows = this.data.paramRows;
    var diffMap = {};

    if (fabrics.length < 2) {
      return diffMap;
    }

    for (var i = 0; i < paramRows.length; i++) {
      var key = paramRows[i].key;
      var firstValue = this._getParamValue(fabrics[0], key);
      var hasDiff = false;

      for (var j = 1; j < fabrics.length; j++) {
        var currentValue = this._getParamValue(fabrics[j], key);
        if (firstValue !== currentValue) {
          hasDiff = true;
          break;
        }
      }

      diffMap[key] = hasDiff;
    }

    return diffMap;
  },

  /**
   * 获取面料参数值（统一转为字符串用于比较）
   * @param {Object} fabric - 面料数据
   * @param {string} key - 参数字段名
   * @returns {string} 参数值字符串
   */
  _getParamValue: function (fabric, key) {
    var value = fabric[key];
    if (value === null || value === undefined || value === '') {
      return '--';
    }
    return String(value);
  },

  /**
   * 格式化参数显示值
   * @param {*} value - 原始值
   * @param {string} format - 格式化类型
   * @param {string} unit - 单位
   * @returns {string} 格式化后的显示值
   */
  _formatValue: function (value, format, unit) {
    if (value === null || value === undefined || value === '') {
      return '--';
    }

    switch (format) {
      case 'price':
        return '¥' + parseFloat(value).toFixed(2) + (unit ? ' ' + unit : '');
      case 'number':
        return value + (unit ? ' ' + unit : '');
      default:
        return String(value);
    }
  },

  /**
   * 重新加载数据
   */
  onRetry: function () {
    this._loadCompareData();
  },

  /**
   * 点击面料图片/名称 - 跳转详情页
   */
  onFabricTap: function (e) {
    var id = e.currentTarget.dataset.id;
    if (id) {
      wx.navigateTo({
        url: '/pages/fabric/detail/detail?id=' + id
      });
    }
  },

  /**
   * 移除对比面料
   */
  onRemoveFabric: function (e) {
    var id = e.currentTarget.dataset.id;
    var fabrics = this.data.fabrics.filter(function (f) {
      return f.id !== id;
    });
    var ids = this.data.ids.filter(function (fid) {
      return fid !== id;
    });

    if (fabrics.length < 2) {
      wx.showToast({
        title: '至少保留2个面料进行对比',
        icon: 'none'
      });
      return;
    }

    var diffMap = this._calculateDiffs(fabrics);

    this.setData({
      fabrics: fabrics,
      ids: ids,
      diffMap: diffMap
    });
  },

  /**
   * 同步头部和内容区域的横向滚动
   */
  onHeaderScroll: function (e) {
    this.setData({
      scrollLeft: e.detail.scrollLeft
    });
  },

  onContentScroll: function (e) {
    this.setData({
      scrollLeft: e.detail.scrollLeft
    });
  }
});
