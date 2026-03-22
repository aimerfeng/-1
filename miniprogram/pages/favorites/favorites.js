/**
 * pages/favorites/favorites.js - 收藏列表页面
 *
 * 功能：
 * - 使用 fabric-card 组件展示已收藏面料
 * - 下拉刷新
 * - 上拉加载更多（分页）
 * - 滑动删除取消收藏
 * - 骨架屏加载态
 * - 空状态展示
 * - 点击面料卡片跳转面料详情页
 *
 * 需求: 9.4
 */
var request = require('../../utils/request');

Page({
  data: {
    /** 收藏列表数据（每项包含 fabric 对象） */
    favoriteList: [],
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
    /** 当前滑动打开的项索引（-1 表示无） */
    swipeOpenIndex: -1,
    /** 触摸起始 X 坐标 */
    startX: 0,
    /** 触摸起始 Y 坐标 */
    startY: 0,
    /** 正在删除中的面料 ID */
    removingId: 0
  },

  onLoad: function () {
    this._loadFavorites(true);
  },

  onShow: function () {
    // 从详情页返回时刷新列表（可能取消了收藏）
    if (this._hasLoaded) {
      this._loadFavorites(true);
    }
  },

  /**
   * 下拉刷新
   */
  onPullDownRefresh: function () {
    this._loadFavorites(true);
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
   * 加载收藏列表
   * @param {boolean} isRefresh - 是否为刷新（重置页码）
   */
  _loadFavorites: function (isRefresh) {
    var that = this;

    if (isRefresh) {
      this.setData({
        page: 1,
        loading: true,
        hasMore: true,
        favoriteList: [],
        swipeOpenIndex: -1
      });
    }

    var params = {
      page: this.data.page,
      per_page: this.data.perPage
    };

    request.get('/fabrics/favorites', params).then(function (res) {
      var items = res.items || [];
      var total = res.total || 0;
      var currentPage = res.page || 1;
      var perPage = res.per_page || that.data.perPage;

      // 处理收藏数据，提取面料信息
      var processedItems = items.map(function (item) {
        return that._processFavoriteItem(item);
      }).filter(function (item) {
        // 过滤掉面料已被删除的收藏
        return item.fabric !== null;
      });

      that.setData({
        favoriteList: processedItems,
        total: total,
        page: currentPage,
        loading: false,
        hasMore: currentPage * perPage < total
      });

      that._hasLoaded = true;

      if (isRefresh) {
        wx.stopPullDownRefresh();
      }
    }).catch(function () {
      that.setData({ loading: false });
      that._hasLoaded = true;
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

    request.get('/fabrics/favorites', params).then(function (res) {
      var items = res.items || [];
      var total = res.total || 0;
      var currentPage = res.page || nextPage;
      var perPage = res.per_page || that.data.perPage;

      var processedItems = items.map(function (item) {
        return that._processFavoriteItem(item);
      }).filter(function (item) {
        return item.fabric !== null;
      });

      that.setData({
        favoriteList: that.data.favoriteList.concat(processedItems),
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
   * 处理单条收藏数据
   * @param {Object} item - 收藏原始数据（含 fabric 子对象）
   * @returns {Object} 处理后的收藏数据
   */
  _processFavoriteItem: function (item) {
    return {
      id: item.id,
      fabric_id: item.fabric_id,
      created_at: item.created_at,
      fabric: item.fabric || null
    };
  },

  /**
   * 点击面料卡片，跳转到面料详情页
   */
  onFabricTap: function (e) {
    // 如果有滑动打开的项，先关闭
    if (this.data.swipeOpenIndex !== -1) {
      this.setData({ swipeOpenIndex: -1 });
      return;
    }

    var fabricId = e.currentTarget.dataset.fabricId;
    if (fabricId) {
      wx.navigateTo({
        url: '/pages/fabric/detail/detail?id=' + fabricId
      });
    }
  },

  /**
   * 触摸开始 - 记录起始位置
   */
  onTouchStart: function (e) {
    if (e.touches.length !== 1) return;
    this.setData({
      startX: e.touches[0].clientX,
      startY: e.touches[0].clientY
    });
  },

  /**
   * 触摸移动 - 判断滑动方向并打开/关闭删除按钮
   */
  onTouchMove: function (e) {
    if (e.touches.length !== 1) return;

    var moveX = e.touches[0].clientX;
    var moveY = e.touches[0].clientY;
    var deltaX = moveX - this.data.startX;
    var deltaY = moveY - this.data.startY;

    // 水平滑动距离大于垂直滑动距离才处理
    if (Math.abs(deltaX) < Math.abs(deltaY)) return;

    var index = parseInt(e.currentTarget.dataset.index);

    if (deltaX < -50) {
      // 左滑：打开删除按钮
      this.setData({ swipeOpenIndex: index });
    } else if (deltaX > 50) {
      // 右滑：关闭删除按钮
      this.setData({ swipeOpenIndex: -1 });
    }
  },

  /**
   * 点击删除按钮 - 取消收藏
   */
  onRemoveFavorite: function (e) {
    var that = this;
    var fabricId = e.currentTarget.dataset.fabricId;
    var index = e.currentTarget.dataset.index;

    if (!fabricId || this.data.removingId) return;

    wx.showModal({
      title: '提示',
      content: '确定要取消收藏该面料吗？',
      confirmText: '取消收藏',
      confirmColor: '#E74C3C',
      success: function (res) {
        if (res.confirm) {
          that._doRemoveFavorite(fabricId, index);
        }
      }
    });
  },

  /**
   * 执行取消收藏操作
   * @param {number} fabricId - 面料 ID
   * @param {number} index - 列表索引
   */
  _doRemoveFavorite: function (fabricId, index) {
    var that = this;

    this.setData({ removingId: fabricId });

    request.del('/fabrics/' + fabricId + '/favorite').then(function () {
      // 从列表中移除该项（带动画效果）
      var favoriteList = that.data.favoriteList.slice();
      favoriteList.splice(index, 1);

      that.setData({
        favoriteList: favoriteList,
        total: that.data.total > 0 ? that.data.total - 1 : 0,
        swipeOpenIndex: -1,
        removingId: 0
      });

      wx.showToast({
        title: '已取消收藏',
        icon: 'success',
        duration: 1500
      });
    }).catch(function () {
      that.setData({ removingId: 0 });
    });
  },

  /**
   * 空状态操作按钮 - 跳转面料列表
   */
  onGoExplore: function () {
    wx.switchTab({
      url: '/pages/fabric/list/list'
    });
  }
});
