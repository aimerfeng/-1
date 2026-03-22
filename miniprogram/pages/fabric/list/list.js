/**
 * pages/fabric/list/list.js - 面料列表页面
 * 实现多条件筛选、分页加载、下拉刷新、骨架屏、空状态
 * 需求: 4.1, 4.2, 10.2, 10.3
 */
var request = require('../../../utils/request.js');
var util = require('../../../utils/util.js');

Page({
  data: {
    /** 搜索关键词 */
    searchKeyword: '',
    /** 面料列表数据 */
    fabricList: [],
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

    /** 筛选面板是否展开 */
    filterVisible: false,

    /** 筛选条件 */
    filters: {
      composition: '',
      craft: '',
      priceMin: '',
      priceMax: '',
      weightMin: '',
      weightMax: '',
      color: ''
    },

    /** 成分选项列表 */
    compositionOptions: ['全棉', '涤纶', '涤棉', '锦纶', '真丝', '亚麻', '羊毛', '莫代尔'],
    /** 成分选择索引 */
    compositionIndex: -1,

    /** 工艺选项列表 */
    craftOptions: ['平纹', '斜纹', '缎纹', '针织', '梭织', '提花', '印花', '染色'],
    /** 工艺选择索引 */
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
    /** 当前选中的颜色值 */
    selectedColor: '',

    /** 对比选中的面料ID列表 */
    compareList: [],
    /** 最大对比数量 */
    maxCompare: 5,

    /** 是否有活跃的筛选条件 */
    hasActiveFilters: false
  },

  onLoad: function () {
    this._loadFabrics(true);
  },

  onShow: function () {
    // 从对比页返回时可能需要刷新对比列表
  },

  /**
   * 下拉刷新
   */
  onPullDownRefresh: function () {
    this._loadFabrics(true);
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
   * 加载面料列表
   * @param {boolean} isRefresh - 是否为刷新（重置页码）
   */
  _loadFabrics: function (isRefresh) {
    var that = this;

    if (isRefresh) {
      this.setData({
        page: 1,
        loading: true,
        hasMore: true,
        fabricList: []
      });
    }

    var params = this._buildQueryParams();

    request.get('/fabrics', params).then(function (res) {
      var items = res.items || [];
      var total = res.total || 0;
      var currentPage = res.page || 1;
      var perPage = res.per_page || that.data.perPage;

      that.setData({
        fabricList: items,
        total: total,
        page: currentPage,
        loading: false,
        hasMore: currentPage * perPage < total
      });

      if (isRefresh) {
        wx.stopPullDownRefresh();
      }
    }).catch(function () {
      that.setData({
        loading: false
      });
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

    this.setData({
      loadingMore: true
    });

    var params = this._buildQueryParams();
    params.page = nextPage;

    request.get('/fabrics', params).then(function (res) {
      var items = res.items || [];
      var total = res.total || 0;
      var currentPage = res.page || nextPage;
      var perPage = res.per_page || that.data.perPage;

      that.setData({
        fabricList: that.data.fabricList.concat(items),
        total: total,
        page: currentPage,
        loadingMore: false,
        hasMore: currentPage * perPage < total
      });
    }).catch(function () {
      that.setData({
        loadingMore: false
      });
    });
  },

  /**
   * 构建查询参数
   */
  _buildQueryParams: function () {
    var filters = this.data.filters;
    var params = {
      page: this.data.page,
      per_page: this.data.perPage
    };

    if (this.data.searchKeyword) {
      params.keyword = this.data.searchKeyword;
    }
    if (filters.composition) {
      params.composition = filters.composition;
    }
    if (filters.craft) {
      params.craft = filters.craft;
    }
    if (filters.priceMin) {
      params.price_min = parseFloat(filters.priceMin);
    }
    if (filters.priceMax) {
      params.price_max = parseFloat(filters.priceMax);
    }
    if (filters.weightMin) {
      params.weight_min = parseFloat(filters.weightMin);
    }
    if (filters.weightMax) {
      params.weight_max = parseFloat(filters.weightMax);
    }
    if (filters.color) {
      params.color = filters.color;
    }

    return params;
  },

  /**
   * 搜索输入（防抖 500ms）
   */
  onSearchInput: function (e) {
    var keyword = e.detail.value;
    this.setData({ searchKeyword: keyword });
    if (this._searchTimer) clearTimeout(this._searchTimer);
    var that = this;
    this._searchTimer = setTimeout(function () {
      that._loadFabrics(true);
    }, 300);
  },

  /**
   * 键盘确认搜索
   */
  onSearchConfirm: function () {
    if (this._searchTimer) clearTimeout(this._searchTimer);
    this._loadFabrics(true);
  },

  /**
   * 清空搜索词
   */
  onSearchClear: function () {
    this.setData({ searchKeyword: '' });
    this._loadFabrics(true);
  },

  /**
   * 切换筛选面板显示/隐藏
   */
  toggleFilter: function () {
    this.setData({
      filterVisible: !this.data.filterVisible
    });
  },

  /**
   * 关闭筛选面板（点击遮罩层）
   */
  closeFilter: function () {
    this.setData({
      filterVisible: false
    });
  },

  /**
   * 阻止事件冒泡（筛选面板内部点击）
   */
  preventBubble: function () {
    // 空函数，仅用于阻止冒泡
  },

  /**
   * 成分下拉选择变化
   */
  onCompositionChange: function (e) {
    var index = parseInt(e.detail.value, 10);
    var value = this.data.compositionOptions[index] || '';
    this.setData({
      compositionIndex: index,
      'filters.composition': value
    });
  },

  /**
   * 工艺下拉选择变化
   */
  onCraftChange: function (e) {
    var index = parseInt(e.detail.value, 10);
    var value = this.data.craftOptions[index] || '';
    this.setData({
      craftIndex: index,
      'filters.craft': value
    });
  },

  /**
   * 价格最小值输入
   */
  onPriceMinInput: function (e) {
    this.setData({
      'filters.priceMin': e.detail.value
    });
  },

  /**
   * 价格最大值输入
   */
  onPriceMaxInput: function (e) {
    this.setData({
      'filters.priceMax': e.detail.value
    });
  },

  /**
   * 克重最小值输入
   */
  onWeightMinInput: function (e) {
    this.setData({
      'filters.weightMin': e.detail.value
    });
  },

  /**
   * 克重最大值输入
   */
  onWeightMaxInput: function (e) {
    this.setData({
      'filters.weightMax': e.detail.value
    });
  },

  /**
   * 颜色选择
   */
  onColorSelect: function (e) {
    var color = e.currentTarget.dataset.color;
    var selectedColor = this.data.selectedColor === color ? '' : color;
    this.setData({
      selectedColor: selectedColor,
      'filters.color': selectedColor
    });
  },

  /**
   * 应用筛选条件
   */
  applyFilter: function () {
    this.setData({
      filterVisible: false,
      hasActiveFilters: this._checkActiveFilters()
    });
    this._loadFabrics(true);
  },

  /**
   * 重置筛选条件
   */
  resetFilter: function () {
    this.setData({
      filters: {
        composition: '',
        craft: '',
        priceMin: '',
        priceMax: '',
        weightMin: '',
        weightMax: '',
        color: ''
      },
      compositionIndex: -1,
      craftIndex: -1,
      selectedColor: '',
      hasActiveFilters: false,
      filterVisible: false
    });
    this._loadFabrics(true);
  },

  /**
   * 检查是否有活跃的筛选条件
   */
  _checkActiveFilters: function () {
    var f = this.data.filters;
    return !!(f.composition || f.craft || f.priceMin || f.priceMax ||
              f.weightMin || f.weightMax || f.color);
  },

  /**
   * 面料卡片点击 - 跳转详情页
   */
  onFabricTap: function (e) {
    var fabric = e.detail.fabric;
    if (fabric && fabric.id) {
      wx.navigateTo({
        url: '/pages/fabric/detail/detail?id=' + fabric.id
      });
    }
  },

  /**
   * 切换面料对比选中状态
   */
  onCompareToggle: function (e) {
    var fabricId = e.currentTarget.dataset.id;
    var compareList = this.data.compareList.slice();
    var index = compareList.indexOf(fabricId);

    if (index > -1) {
      compareList.splice(index, 1);
    } else {
      if (compareList.length >= this.data.maxCompare) {
        wx.showToast({
          title: '最多选择' + this.data.maxCompare + '个面料对比',
          icon: 'none'
        });
        return;
      }
      compareList.push(fabricId);
    }

    this.setData({
      compareList: compareList
    });
  },

  /**
   * 跳转到面料对比页面
   */
  goCompare: function () {
    if (this.data.compareList.length < 2) {
      wx.showToast({
        title: '请至少选择2个面料进行对比',
        icon: 'none'
      });
      return;
    }
    var ids = this.data.compareList.join(',');
    wx.navigateTo({
      url: '/pages/fabric/compare/compare?ids=' + ids
    });
  },

  /**
   * 检查面料是否在对比列表中
   */
  isInCompare: function (fabricId) {
    return this.data.compareList.indexOf(fabricId) > -1;
  }
});
