/**
 * pages/message/chat/chat.js - 聊天详情页
 * 展示会话消息列表，支持发送消息
 * 下拉加载历史消息，新消息自动滚动到底部
 * 系统消息居中显示
 * 需求: 7.1, 7.2, 7.3, 7.4
 */
var request = require('../../../utils/request');
var auth = require('../../../utils/auth');
var util = require('../../../utils/util');

Page({
  data: {
    /** 会话ID */
    conversationId: null,
    /** 对方名称 */
    counterparty: '',
    /** 需求标题 */
    demandTitle: '',
    /** 当前用户ID */
    currentUserId: null,

    /** 消息列表 */
    messageList: [],
    /** 是否正在加载 */
    loading: true,
    /** 是否正在加载更多（历史消息） */
    loadingMore: false,
    /** 是否还有更多历史消息 */
    hasMore: true,
    /** 当前页码 */
    page: 1,
    /** 每页条数 */
    perPage: 30,
    /** 总消息数 */
    total: 0,

    /** 输入框内容 */
    inputValue: '',
    /** 是否正在发送 */
    sending: false,
    /** 滚动到的元素ID */
    scrollToView: '',
    /** 滚动区域高度（用于计算） */
    scrollHeight: 0
  },

  onLoad: function (options) {
    var conversationId = options.id;
    var counterparty = decodeURIComponent(options.counterparty || '');
    var demandTitle = decodeURIComponent(options.demandTitle || '');

    // 获取当前用户ID
    var userInfo = auth.getUserInfo();
    var currentUserId = userInfo ? userInfo.id : null;

    // 设置导航栏标题
    wx.setNavigationBarTitle({
      title: counterparty || '聊天'
    });

    this.setData({
      conversationId: conversationId,
      counterparty: counterparty,
      demandTitle: demandTitle,
      currentUserId: currentUserId
    });

    // 加载消息
    this._loadMessages(true);
  },

  onShow: function () {
    // 开始轮询新消息
    this._startPolling();
  },

  onHide: function () {
    this._stopPolling();
  },

  onUnload: function () {
    this._stopPolling();
  },

  /**
   * 下拉刷新 - 加载更早的消息
   */
  onPullDownRefresh: function () {
    if (this.data.hasMore && !this.data.loadingMore) {
      this._loadOlderMessages();
    } else {
      wx.stopPullDownRefresh();
    }
  },

  /* ============================================================
     消息加载
     ============================================================ */

  /**
   * 加载消息列表（首次加载，获取最新消息）
   * @param {boolean} isInitial - 是否为初始加载
   */
  _loadMessages: function (isInitial) {
    var that = this;

    if (isInitial) {
      this.setData({
        loading: true,
        messageList: [],
        page: 1,
        hasMore: true
      });
    }

    var params = {
      page: 1,
      per_page: this.data.perPage
    };

    request.get('/conversations/' + this.data.conversationId + '/messages', params).then(function (res) {
      var items = res.items || [];
      var total = res.total || 0;
      var perPage = res.per_page || that.data.perPage;

      // 处理消息数据
      var processedItems = items.map(function (item) {
        return that._processMessageItem(item);
      });

      // 计算总页数，判断是否有更多历史消息
      var totalPages = Math.ceil(total / perPage);

      that.setData({
        messageList: processedItems,
        total: total,
        page: 1,
        loading: false,
        hasMore: totalPages > 1
      });

      // 滚动到底部
      that._scrollToBottom();
    }).catch(function () {
      that.setData({ loading: false });
    });
  },

  /**
   * 加载更早的消息（下拉加载）
   */
  _loadOlderMessages: function () {
    var that = this;
    var nextPage = this.data.page + 1;

    this.setData({ loadingMore: true });

    var params = {
      page: nextPage,
      per_page: this.data.perPage
    };

    request.get('/conversations/' + this.data.conversationId + '/messages', params).then(function (res) {
      var items = res.items || [];
      var total = res.total || 0;
      var currentPage = res.page || nextPage;
      var perPage = res.per_page || that.data.perPage;

      var processedItems = items.map(function (item) {
        return that._processMessageItem(item);
      });

      // 将历史消息添加到列表前面
      var totalPages = Math.ceil(total / perPage);

      that.setData({
        messageList: processedItems.concat(that.data.messageList),
        total: total,
        page: currentPage,
        loadingMore: false,
        hasMore: currentPage < totalPages
      });

      wx.stopPullDownRefresh();
    }).catch(function () {
      that.setData({ loadingMore: false });
      wx.stopPullDownRefresh();
    });
  },

  /**
   * 处理单条消息数据
   * @param {Object} item - 消息原始数据
   * @returns {Object} 处理后的消息数据
   */
  _processMessageItem: function (item) {
    // 判断是否为自己发送的消息
    item.isMine = item.sender_id === this.data.currentUserId;
    // 判断是否为系统消息
    item.isSystem = item.msg_type === 'system';
    // 格式化时间
    item.timeText = util.getRelativeTime(item.created_at);
    // 唯一标识（用于滚动定位）
    item.viewId = 'msg-' + item.id;

    return item;
  },

  /* ============================================================
     发送消息
     ============================================================ */

  /**
   * 输入框内容变化
   */
  onInputChange: function (e) {
    this.setData({
      inputValue: e.detail.value
    });
  },

  /**
   * 发送消息
   */
  onSendMessage: function () {
    var that = this;
    var content = this.data.inputValue.trim();

    if (!content) {
      wx.showToast({
        title: '请输入消息内容',
        icon: 'none'
      });
      return;
    }

    if (this.data.sending) return;

    this.setData({ sending: true });

    request.post('/conversations/' + this.data.conversationId + '/messages', {
      content: content
    }).then(function (res) {
      // 处理返回的消息
      var newMessage = that._processMessageItem(res);

      // 添加到消息列表末尾
      var messageList = that.data.messageList.concat([newMessage]);

      that.setData({
        messageList: messageList,
        inputValue: '',
        sending: false
      });

      // 滚动到底部
      that._scrollToBottom();
    }).catch(function () {
      that.setData({ sending: false });
      wx.showToast({
        title: '发送失败，请重试',
        icon: 'none'
      });
    });
  },

  /* ============================================================
     辅助方法
     ============================================================ */

  /**
   * 滚动到底部
   */
  _scrollToBottom: function () {
    var that = this;
    setTimeout(function () {
      var list = that.data.messageList;
      if (list.length > 0) {
        that.setData({
          scrollToView: list[list.length - 1].viewId
        });
      }
    }, 100);
  },

  /**
   * 开始轮询新消息（每5秒）
   */
  _startPolling: function () {
    this._stopPolling();
    var that = this;
    this._pollTimer = setInterval(function () {
      that._pollNewMessages();
    }, 5000);
  },

  /**
   * 停止轮询
   */
  _stopPolling: function () {
    if (this._pollTimer) {
      clearInterval(this._pollTimer);
      this._pollTimer = null;
    }
  },

  /**
   * 拉取新消息（只获取第一页，对比最新ID）
   */
  _pollNewMessages: function () {
    var that = this;
    if (this.data.loading || this.data.sending) return;

    var list = this.data.messageList;
    var latestId = list.length > 0 ? list[list.length - 1].id : 0;

    request.get('/conversations/' + this.data.conversationId + '/messages', {
      page: 1,
      per_page: this.data.perPage
    }, { showError: false }).then(function (res) {
      var items = res.items || [];
      // 找出比当前最新ID更新的消息
      var newItems = [];
      for (var i = 0; i < items.length; i++) {
        if (items[i].id > latestId) {
          newItems.push(that._processMessageItem(items[i]));
        }
      }
      if (newItems.length > 0) {
        that.setData({
          messageList: that.data.messageList.concat(newItems)
        });
        that._scrollToBottom();
      }
    }).catch(function () {
      // 静默失败
    });
  }
});
