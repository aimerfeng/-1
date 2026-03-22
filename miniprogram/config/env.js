/**
 * Runtime environment resolution for mini program API base URL.
 *
 * Env source priority:
 * 1) local storage debug_base_url (http/https only)
 * 2) envVersion mapping from wx.getAccountInfoSync().miniProgram.envVersion
 * 3) develop fallback
 */

var ENV_BASE_URLS = {
  develop: 'http://127.0.0.1:5000/api',
  // TODO: replace with your internal trial domain.
  trial: 'https://trial-api.example.com/api',
  // TODO: replace with your production domain.
  release: 'https://api.example.com/api'
};

function _isValidHttpUrl(value) {
  if (!value || typeof value !== 'string') return false;
  return /^https?:\/\/.+/.test(value.trim());
}

function getRuntimeEnv() {
  try {
    var info = wx.getAccountInfoSync && wx.getAccountInfoSync();
    var envVersion = info && info.miniProgram && info.miniProgram.envVersion;
    if (envVersion && ENV_BASE_URLS[envVersion]) {
      return envVersion;
    }
  } catch (e) {
    // Ignore and fallback to develop.
  }
  return 'develop';
}

function getBaseUrl() {
  try {
    var debugBaseUrl = wx.getStorageSync('debug_base_url');
    if (_isValidHttpUrl(debugBaseUrl)) {
      return debugBaseUrl.trim();
    }
  } catch (e) {
    // Ignore storage read errors and continue.
  }

  var env = getRuntimeEnv();
  return ENV_BASE_URLS[env] || ENV_BASE_URLS.develop;
}

module.exports = {
  ENV_BASE_URLS: ENV_BASE_URLS,
  getRuntimeEnv: getRuntimeEnv,
  getBaseUrl: getBaseUrl
};
