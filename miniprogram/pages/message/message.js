/**
 * pages/message/message.js - 消息中心页面
 * 双Tab布局：会话列表 + 通知列表
 * 会话Tab：展示与对方的聊天会话，点击进入聊天详情
 * 通知Tab：展示系统通知消息（保留原有逻辑）
 * 需求: 8.1, 8.2, 8.3, 8.4, 8.5, 10.3
 */
var request = require('../../utils/request');
var util = require('../../utils/util');
var auth = require('../../utils/auth');

Page({
  data: {
    /** 当前激活的Tab: 'conversations' 或 'notifications' */
    activeTab: 'conversations',

    /* ============================================================
       会话Tab数据
       ============================================================ */
    /** 会话列表数据 */
    conversationList: [],
    /** 会话列表是否正在加载 */
    convLoading: true,
    /** 会话列表是否正在加载更多 */
    convLoadingMore: false,
    /** 会话列表是否还有更多 */
    convHasMore: true,
    /** 会话列表当前页码 */
    convPage: 1,
    /** 会话列表每页条数 */
    convPerPage: 20,
    /** 会话列表总数 */
    convTotal: 0,
    /** 未读会话消息数量 */
    unreadConvCount: 0,

    /* ============================================================
       通知Tab数据（保留原有逻辑）
       ============================================================ */
    /** 消息列表数据 */
    messageList: [],
    /** 是否正在加载（首次加载，展示骨架屏） */
    loading: true,
    /** 是否正在加载更多 */
    loadingMore: false,
    /** 是否还有更多数据 */
    hasMore: true,
    /** 当前页码 */
    page: 1,
    /** 每页条数 */
    perPage: 15,
    /** 总记录数 */
    total: 0,
    /** 未读消息数量 */
    unreadCount: 0,

    /** 消息类型图标映射 */
    typeIconMap: {
      'match': '🔗',
      'logistics': '🚚',
      'review': '✅',
      'order': '📦',
      'quote': '💰',
      'system': '📢'
    },

    /** 消息类型中文映射 */
    typeTextMap: {
      'match': '供需匹配',
      'logistics': '物流更新',
      'review': '审核结果',
      'order': '订单状态',
      'quote': '供应商报价',
      'system': '系统通知'
    }
  },

  onLoad: function () {
    // 默认加载会话Tab
    this._loadConversations(true);
    this._loadUnreadConvCount();
  },

  onShow: function () {
    // 刷新未读数量
    this._loadUnreadConvCount();
    this._loadUnreadCount();

    // 只在会话Tab且列表已加载时做轻量刷新（不重置列表）
    if (this.data.activeTab === 'conversations' && !this.data.convLoading) {
      this._loadConversations(true);
    }

    // 刷新全局角标
    var app = getApp();
    if (app && app.refreshUnreadBadge) {
      app.refreshUnreadBadge();
    }
  },

  /**
   * 下拉刷新
   */
  onPullDownRefresh: function () {
    if (this.data.activeTab === 'conversations') {
      this._loadConversations(true);
      this._loadUnreadConvCount();
    } else {
      this._loadMessages(true);
      this._loadUnreadCount();
    }
  },

  /**
   * 上拉加载更多
   */
  onReachBottom: function () {
    if (this.data.activeTab === 'conversations') {
      if (this.data.convHasMore && !this.data.convLoadingMore) {
        this._loadMoreConversations();
      }
    } else {
      if (this.data.hasMore && !this.data.loadingMore) {
        this._loadMore();
      }
    }
  },

  /* ============================================================
     Tab切换
     ============================================================ */

  /**
   * 切换Tab
   */
  onTabChange: function (e) {
    var tab = e.currentTarget.dataset.tab;
    if (tab === this.data.activeTab) return;

    this.setData({ activeTab: tab });

    if (tab === 'conversations') {
      if (this.data.conversationList.length === 0) {
        this._loadConversations(true);
      }
    } else {
      if (this.data.messageList.length === 0) {
        this._loadMessages(true);
        this._loadUnreadCount();
      }
    }
  },

  /* ============================================================
     会话Tab方法
     ============================================================ */

  /**
   * 加载会话列表
   * @param {boolean} isRefresh - 是否为刷新（重置页码）
   */
  _loadConversations: function (isRefresh) {
    var that = this;

    if (isRefresh) {
      this.setData({
        convPage: 1,
        convLoading: true,
        convHasMore: true,
        conversationList: []
      });
    }

    var params = {
      page: this.data.convPage,
      per_page: this.data.convPerPage
    };

    request.get('/conversations', params).then(function (res) {
      var items = res.items || [];
      var total = res.total || 0;
      var currentPage = res.page || 1;
      var perPage = res.per_page || that.data.convPerPage;

      // 处理会话数据
      var processedItems = items.map(function (item) {
        return that._processConversationItem(item);
      });

      that.setData({
        conversationList: processedItems,
        convTotal: total,
        convPage: currentPage,
        convLoading: false,
        convHasMore: currentPage * perPage < total
      });

      if (isRefresh) {
        wx.stopPullDownRefresh();
      }
    }).catch(function () {
      that.setData({ convLoading: false });
      if (isRefresh) {
        wx.stopPullDownRefresh();
      }
    });
  },

  /**
   * 加载更多会话
   */
  _loadMoreConversations: function () {
    var that = this;
    var nextPage = this.data.convPage + 1;

    this.setData({ convLoadingMore: true });

    var params = {
      page: nextPage,
      per_page: this.data.convPerPage
    };

    request.get('/conversations', params).then(function (res) {
      var items = res.items || [];
      var total = res.total || 0;
      var currentPage = res.page || nextPage;
      var perPage = res.per_page || that.data.convPerPage;

      var processedItems = items.map(function (item) {
        return that._processConversationItem(item);
      });

      that.setData({
        conversationList: that.data.conversationList.concat(processedItems),
        convTotal: total,
        convPage: currentPage,
        convLoadingMore: false,
        convHasMore: currentPage * perPage < total
      });
    }).catch(function () {
      that.setData({ convLoadingMore: false });
    });
  },

  /**
   * 处理单条会话数据
   * @param {Object} item - 会话原始数据
   * @returns {Object} 处理后的会话数据
   */
  _processConversationItem: function (item) {
    // 相对时间
    item.relativeTime = util.getRelativeTime(item.last_message_at);
    // 消息预览截断
    item.previewText = util.truncateText(item.last_message_preview || '', 30);
    // 对方名称（后端 buyer/supplier 返回字符串，admin 返回对象）
    if (typeof item.counterparty === 'string') {
      item.counterpartyName = item.counterparty;
    } else if (item.counterparty && typeof item.counterparty === 'object') {
      var buyerName = item.counterparty.buyer_company_name || '';
      var supplierName = item.counterparty.supplier_company_name || '';
      item.counterpartyName = (buyerName && supplierName)
        ? (buyerName + ' -> ' + supplierName)
        : (buyerName || supplierName || '未知用户');
    } else {
      item.counterpartyName = item.counterparty_company_name || item.counterparty_name || '未知用户';
    }
    // 需求标题
    item.demandTitle = item.demand_title || '未知需求';
    // 未读数量
    item.unreadCount = item.unread_count || item.unreadCount || 0;

    return item;
  },

  /**
   * 加载未读会话消息数量
   */
  _loadUnreadConvCount: function () {
    var that = this;

    request.get('/conversations/unread-count', {}, { showError: false }).then(function (res) {
      var count = res.count || 0;
      that.setData({ unreadConvCount: count });

      // 更新 tabBar 角标（合并通知未读和会话未读）
      that._updateTabBarBadge();
    }).catch(function () {
      // 静默失败
    });
  },

  /**
   * 更新tabBar角标（合并会话未读和通知未读）
   */
  _updateTabBarBadge: function () {
    var totalUnread = (this.data.unreadConvCount || 0) + (this.data.unreadCount || 0);
    if (totalUnread > 0) {
      wx.setTabBarBadge({
        index: 2,
        text: totalUnread > 99 ? '99+' : String(totalUnread)
      });
    } else {
      wx.removeTabBarBadge({ index: 2 });
    }
  },

  /**
   * 点击会话：跳转到聊天详情页
   */
  onConversationTap: function (e) {
    var conv = e.currentTarget.dataset.conversation;
    if (!conv) return;

    var url = '/pages/message/chat/chat?id=' + conv.id +
      '&counterparty=' + encodeURIComponent(conv.counterpartyName) +
      '&demandTitle=' + encodeURIComponent(conv.demandTitle);

    wx.navigateTo({ url: url });
  },

  /* ============================================================
     通知Tab方法（保留原有逻辑）
     ============================================================ */

  /**
   * 加载消息列表
   * @param {boolean} isRefresh - 是否为刷新（重置页码）
   */
  _loadMessages: function (isRefresh) {
    var that = this;

    if (isRefresh) {
      this.setData({
        page: 1,
        loading: true,
        hasMore: true,
        messageList: []
      });
    }

    var params = {
      page: this.data.page,
      per_page: this.data.perPage
    };

    request.get('/messages', params).then(function (res) {
      var items = res.items || [];
      var total = res.total || 0;
      var currentPage = res.page || 1;
      var perPage = res.per_page || that.data.perPage;

      var processedItems = items.map(function (item) {
        return that._processMessageItem(item);
      });

      that.setData({
        messageList: processedItems,
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

    request.get('/messages', params).then(function (res) {
      var items = res.items || [];
      var total = res.total || 0;
      var currentPage = res.page || nextPage;
      var perPage = res.per_page || that.data.perPage;

      var processedItems = items.map(function (item) {
        return that._processMessageItem(item);
      });

      that.setData({
        messageList: that.data.messageList.concat(processedItems),
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
   * 加载未读消息数量
   */
  _loadUnreadCount: function () {
    var that = this;

    request.get('/messages/unread-count', {}, { showError: false }).then(function (res) {
      var count = res.count || res.unread_count || 0;
      that.setData({ unreadCount: count });

      // 更新 tabBar 角标
      that._updateTabBarBadge();
    }).catch(function () {
      // 静默失败
    });
  },

  /**
   * 处理单条消息数据，添加显示用字段
   * @param {Object} item - 消息原始数据
   * @returns {Object} 处理后的消息数据
   */
  _processMessageItem: function (item) {
    item.typeIcon = this.data.typeIconMap[item.type] || '📢';
    item.typeText = this.data.typeTextMap[item.type] || '系统通知';
    item.relativeTime = util.getRelativeTime(item.created_at);
    item.contentSummary = util.truncateText(item.content, 40);
    return item;
  },

  /**
   * 点击消息：标记已读并跳转对应详情页
   */
  onMessageTap: function (e) {
    var message = e.currentTarget.dataset.message;
    if (!message) return;

    if (!message.is_read) {
      this._markAsRead(message.id);
    }

    var url = this._getNavigateUrl(message);
    if (url) {
      wx.navigateTo({ url: url });
    }
  },

  /**
   * 标记消息为已读
   * @param {number} messageId - 消息 ID
   */
  _markAsRead: function (messageId) {
    var that = this;

    request.put('/messages/' + messageId + '/read', {}, { showError: false }).then(function () {
      var messageList = that.data.messageList.map(function (item) {
        if (item.id === messageId) {
          item.is_read = true;
        }
        return item;
      });

      var unreadCount = that.data.unreadCount > 0 ? that.data.unreadCount - 1 : 0;
      that.setData({
        messageList: messageList,
        unreadCount: unreadCount
      });

      // 更新 tabBar 角标
      that._updateTabBarBadge();

      var app = getApp();
      if (app && app.refreshUnreadBadge) {
        app.refreshUnreadBadge();
      }
    }).catch(function () {
      // 静默失败
    });
  },

  /**
   * 根据消息的 ref_type 获取跳转 URL
   * @param {Object} message - 消息数据
   * @returns {string|null} 跳转 URL
   */
  _getNavigateUrl: function (message) {
    if (!message.ref_type || !message.ref_id) {
      return null;
    }

    var refType = message.ref_type;
    var refId = message.ref_id;

    if (refType === 'demand') {
      return '/pages/demand/detail/detail?id=' + refId;
    } else if (refType === 'fabric') {
      return '/pages/fabric/detail/detail?id=' + refId;
    } else if (refType === 'order') {
      return '/pages/order/detail/detail?id=' + refId;
    } else if (refType === 'sample') {
      return '/pages/sample/sample';
    }

    return null;
  }
});
