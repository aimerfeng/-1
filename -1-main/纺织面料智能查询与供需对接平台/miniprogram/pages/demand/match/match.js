/**
 * pages/demand/match/match.js - 匹配结果页面
 * 展示采购需求的供需匹配结果列表：匹配度评分（进度条可视化）、面料信息摘要、供应商基本信息
 * 点击跳转面料详情页，支持下拉刷新
 * 需求: 5.5
 */
var request = require('../../../utils/request.js');

Page({
  data: {
    /** 需求ID（通过页面参数传入） */
    demandId: null,
    /** 需求标题（用于顶部展示上下文） */
    demandTitle: '',
    /** 匹配结果列表 */
    matchList: [],
    /** 匹配结果总数 */
    total: 0,
    /** 是否正在加载（首次加载，展示骨架屏） */
    loading: true,
    /** 加载失败 */
    loadError: false,
    /** 页面是否已就绪（用于入场动效） */
    pageReady: false,

    /** 维度标签映射 */
    dimensionLabels: {
      composition: '成分',
      weight: '克重',
      craft: '工艺',
      price: '价格',
      width: '幅宽'
    }
  },

  onLoad: function (options) {
    var demandId = options.demand_id || options.id;
    if (!demandId) {
      wx.showToast({
        title: '参数错误',
        icon: 'none'
      });
      return;
    }

    this.setData({
      demandId: parseInt(demandId, 10)
    });

    this._loadDemandInfo();
    this._loadMatches();
  },

  /**
   * 下拉刷新
   */
  onPullDownRefresh: function () {
    this._loadMatches(true);
  },

  /**
   * 加载需求信息（用于顶部展示标题）
   */
  _loadDemandInfo: function () {
    var that = this;
    request.get('/demands/' + this.data.demandId).then(function (res) {
      that.setData({
        demandTitle: res.title || '采购需求'
      });
    }).catch(function () {
      // 需求信息加载失败不影响匹配结果展示
    });
  },

  /**
   * 加载匹配结果列表
   * @param {boolean} isRefresh - 是否为下拉刷新
   */
  _loadMatches: function (isRefresh) {
    var that = this;

    if (!isRefresh) {
      this.setData({
        loading: true,
        loadError: false
      });
    }

    request.get('/demands/' + this.data.demandId + '/matches').then(function (res) {
      var items = res.items || [];
      var total = res.total || 0;

      // 处理匹配结果数据，为每个结果添加展示所需的字段
      var matchList = items.map(function (item) {
        return that._formatMatchItem(item);
      });

      that.setData({
        matchList: matchList,
        total: total,
        loading: false,
        loadError: false,
        pageReady: true
      });

      if (isRefresh) {
        wx.stopPullDownRefresh();
        wx.showToast({
          title: '已刷新',
          icon: 'success',
          duration: 1000
        });
      }
    }).catch(function () {
      that.setData({
        loading: false,
        loadError: true
      });
      if (isRefresh) {
        wx.stopPullDownRefresh();
      }
    });
  },

  /**
   * 格式化单个匹配结果项
   * @param {Object} item - 原始匹配结果数据
   * @returns {Object} 格式化后的匹配结果
   */
  _formatMatchItem: function (item) {
    var score = item.score || 0;
    var scoreDetail = item.score_detail || {};
    var fabric = item.fabric || {};

    // 计算评分等级和颜色
    var scoreLevel = '';
    var scoreColorClass = '';
    if (score >= 80) {
      scoreLevel = '优秀';
      scoreColorClass = 'score--excellent';
    } else if (score >= 60) {
      scoreLevel = '良好';
      scoreColorClass = 'score--good';
    } else if (score >= 40) {
      scoreLevel = '一般';
      scoreColorClass = 'score--fair';
    } else {
      scoreLevel = '较低';
      scoreColorClass = 'score--low';
    }

    // 格式化维度得分列表
    var dimensions = [];
    var dimensionLabels = this.data.dimensionLabels;
    var dimensionKeys = ['composition', 'weight', 'craft', 'price', 'width'];
    for (var i = 0; i < dimensionKeys.length; i++) {
      var key = dimensionKeys[i];
      if (scoreDetail[key] !== undefined && scoreDetail[key] !== null) {
        dimensions.push({
          key: key,
          label: dimensionLabels[key] || key,
          score: Math.round(scoreDetail[key])
        });
      }
    }

    // 面料图片（取第一张或使用占位）
    var fabricImage = '';
    if (fabric.images && fabric.images.length > 0) {
      fabricImage = fabric.images[0];
    }

    // 供应商信息
    var supplierName = fabric.supplier_name || fabric.company_name || '供应商';

    return {
      id: item.id,
      fabricId: fabric.id,
      score: Math.round(score),
      scoreLevel: scoreLevel,
      scoreColorClass: scoreColorClass,
      dimensions: dimensions,
      fabricName: fabric.name || '未知面料',
      fabricImage: fabricImage,
      composition: fabric.composition || '-',
      weight: fabric.weight ? fabric.weight + ' g/m²' : '-',
      width: fabric.width ? fabric.width + ' cm' : '-',
      craft: fabric.craft || '-',
      price: fabric.price ? '¥' + fabric.price + '/米' : '-',
      color: fabric.color || '-',
      minOrderQty: fabric.min_order_qty ? fabric.min_order_qty + '米起订' : '',
      deliveryDays: fabric.delivery_days ? fabric.delivery_days + '天交货' : '',
      supplierName: supplierName
    };
  },

  /**
   * 点击匹配结果 - 跳转面料详情页
   */
  onMatchItemTap: function (e) {
    var fabricId = e.currentTarget.dataset.fabricId;
    if (fabricId) {
      wx.navigateTo({
        url: '/pages/fabric/detail/detail?id=' + fabricId
      });
    }
  },

  /**
   * 重试加载
   */
  onRetry: function () {
    this._loadMatches();
  }
});
