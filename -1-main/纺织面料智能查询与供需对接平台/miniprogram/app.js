// app.js - WeChat Mini Program entry point
// Global application logic and state management

var request = require('./utils/request');
var envConfig = require('./config/env');

App({
  /**
   * Lifecycle: called when the mini program initializes
   * Checks login status, loads cached user info, and starts unread badge polling
   */
  onLaunch: function () {
    this._initEnvironment();
    this.checkLoginStatus();
    // Start polling unread message count for tabBar badge
    this._startUnreadBadgePolling();
  },

  onHide: function () {
    // Pause polling when app goes to background
    if (this._unreadPollTimer) {
      clearInterval(this._unreadPollTimer);
      this._unreadPollTimer = null;
    }
  },

  onShow: function () {
    // Resume polling when app comes back to foreground
    if (this.globalData.isLoggedIn && !this._unreadPollTimer) {
      this._startUnreadBadgePolling();
    }
  },

  /**
   * Resolve runtime env and API base URL.
   */
  _initEnvironment: function () {
    var runtimeEnv = envConfig.getRuntimeEnv();
    var baseUrl = envConfig.getBaseUrl();

    this.globalData.runtimeEnv = runtimeEnv;
    this.globalData.baseUrl = baseUrl;

    console.log('[app] env:', runtimeEnv, 'baseUrl:', baseUrl);
  },

  /**
   * Check if user is already logged in by verifying stored token
   * Updates globalData accordingly
   */
  checkLoginStatus: function () {
    var token = wx.getStorageSync('token');
    var userInfo = wx.getStorageSync('userInfo');

    if (token && userInfo) {
      this.globalData.token = token;
      this.globalData.userInfo = userInfo;
      this.globalData.isLoggedIn = true;
    } else {
      this.globalData.token = '';
      this.globalData.userInfo = null;
      this.globalData.isLoggedIn = false;
    }
  },

  /**
   * Save login data to storage and update global state
   * @param {string} token - JWT authentication token
   * @param {Object} userInfo - User profile information
   */
  setLoginState: function (token, userInfo) {
    this.globalData.token = token;
    this.globalData.userInfo = userInfo;
    this.globalData.isLoggedIn = true;

    try {
      wx.setStorageSync('token', token);
      wx.setStorageSync('userInfo', userInfo || null);
    } catch (e) {
      // Storage write failed silently
    }

    // Refresh badge immediately after login
    this.refreshUnreadBadge();
  },

  /**
   * Clear login data from storage and reset global state
   */
  clearLoginState: function () {
    this.globalData.token = '';
    this.globalData.userInfo = null;
    this.globalData.isLoggedIn = false;
    this.globalData.unreadCount = 0;

    wx.removeStorageSync('token');
    wx.removeStorageSync('userInfo');

    // Clear tabBar badge when logging out
    this._clearUnreadBadge();
  },

  /**
   * Get current user role for permission checks
   * @returns {string|null} User role: 'buyer', 'supplier', 'admin', or null
   */
  getUserRole: function () {
    if (this.globalData.userInfo) {
      return this.globalData.userInfo.role;
    }
    return null;
  },

  /**
   * Check if the current user has a specific role
   * @param {string} role - Role to check against
   * @returns {boolean} Whether the user has the specified role
   */
  hasRole: function (role) {
    return this.getUserRole() === role;
  },

  // ============================================================
  // Unread Message Badge Management
  // ============================================================

  /**
   * Start polling unread message count every 60 seconds.
   * The poll runs only when the user is logged in.
   */
  _startUnreadBadgePolling: function () {
    var that = this;

    // Initial fetch
    this.refreshUnreadBadge();

    // Set up periodic polling (every 60 seconds)
    this._unreadPollTimer = setInterval(function () {
      that.refreshUnreadBadge();
    }, 60000);
  },

  /**
   * Refresh the unread message count and update the tabBar badge.
   * This method is exposed globally so any page can call it
   * (e.g., after marking a message as read).
   */
  refreshUnreadBadge: function () {
    var that = this;

    // Only poll when logged in
    if (!this.globalData.isLoggedIn || !this.globalData.token) {
      this._clearUnreadBadge();
      return;
    }

    // Keep the app-level badge consistent with message center:
    // total unread = conversation unread + notification unread.
    Promise.all([
      request.get('/conversations/unread-count', {}, { showError: false }).catch(function () {
        return { count: 0 };
      }),
      request.get('/messages/unread-count', {}, { showError: false }).catch(function () {
        return { count: 0 };
      })
    ]).then(function (results) {
      var convRes = results[0] || {};
      var msgRes = results[1] || {};
      var convCount = convRes.count || convRes.unread_count || 0;
      var msgCount = msgRes.count || msgRes.unread_count || 0;
      var total = convCount + msgCount;

      that.globalData.unreadCount = total;
      that._updateTabBarBadge(total);
    }).catch(function () {
      // Silently fail to avoid disrupting UX.
    });
  },

  /**
   * Update the tabBar badge on the message tab (index 2).
   * @param {number} count - Unread message count
   */
  _updateTabBarBadge: function (count) {
    if (count > 0) {
      wx.setTabBarBadge({
        index: 2,
        text: count > 99 ? '99+' : String(count)
      });
    } else {
      this._clearUnreadBadge();
    }
  },

  /**
   * Remove the tabBar badge from the message tab.
   */
  _clearUnreadBadge: function () {
    wx.removeTabBarBadge({
      index: 2,
      fail: function () {
        // Ignore errors (e.g., badge not set)
      }
    });
  },

  /**
   * Global data shared across all pages
   */
  globalData: {
    // User authentication state
    userInfo: null,
    token: '',
    isLoggedIn: false,

    // Unread message count (kept in sync by polling)
    unreadCount: 0,

    // Runtime environment and API base URL
    runtimeEnv: 'develop',
    baseUrl: 'http://127.0.0.1:5000/api',

    // Platform configuration
    platform: {
      name: '\u7eba\u7ec7\u9762\u6599\u5e73\u53f0',
      version: '1.0.0'
    }
  }
});
