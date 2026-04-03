/**
 * util.js - 通用工具函数模块
 * 提供日期格式化、价格格式化、重量格式化等常用工具函数
 */

/**
 * 日期格式化
 * @param {Date|string|number} date - 日期对象、日期字符串或时间戳
 * @param {string} [format='YYYY-MM-DD HH:mm:ss'] - 格式化模板
 *   支持的占位符：YYYY(年), MM(月), DD(日), HH(时), mm(分), ss(秒)
 * @returns {string} 格式化后的日期字符串
 */
function formatDate(date, format) {
  if (!date) return '';

  format = format || 'YYYY-MM-DD HH:mm:ss';

  // 统一转换为 Date 对象
  if (typeof date === 'string' || typeof date === 'number') {
    date = new Date(date);
  }

  if (!(date instanceof Date) || isNaN(date.getTime())) {
    return '';
  }

  var year = date.getFullYear();
  var month = date.getMonth() + 1;
  var day = date.getDate();
  var hours = date.getHours();
  var minutes = date.getMinutes();
  var seconds = date.getSeconds();

  var result = format
    .replace('YYYY', year)
    .replace('MM', padZero(month))
    .replace('DD', padZero(day))
    .replace('HH', padZero(hours))
    .replace('mm', padZero(minutes))
    .replace('ss', padZero(seconds));

  return result;
}

/**
 * 数字补零
 * @param {number} num - 数字
 * @returns {string} 补零后的字符串
 */
function padZero(num) {
  return num < 10 ? '0' + num : '' + num;
}

/**
 * 格式化价格
 * @param {number|string} price - 价格数值
 * @param {number} [decimals=2] - 小数位数
 * @param {string} [unit='元/米'] - 价格单位
 * @returns {string} 格式化后的价格字符串，如 "¥12.50 元/米"
 */
function formatPrice(price, decimals, unit) {
  if (price === null || price === undefined || price === '') return '';

  decimals = decimals !== undefined ? decimals : 2;
  unit = unit !== undefined ? unit : '元/米';

  var num = parseFloat(price);
  if (isNaN(num)) return '';

  var formatted = '¥' + num.toFixed(decimals);
  if (unit) {
    formatted += ' ' + unit;
  }
  return formatted;
}

/**
 * 格式化重量（克重）
 * @param {number|string} weight - 重量数值
 * @param {string} [unit='g/m²'] - 重量单位
 * @returns {string} 格式化后的重量字符串，如 "150 g/m²"
 */
function formatWeight(weight, unit) {
  if (weight === null || weight === undefined || weight === '') return '';

  unit = unit !== undefined ? unit : 'g/m²';

  var num = parseFloat(weight);
  if (isNaN(num)) return '';

  return num + ' ' + unit;
}

/**
 * 格式化幅宽
 * @param {number|string} width - 幅宽数值
 * @param {string} [unit='cm'] - 幅宽单位
 * @returns {string} 格式化后的幅宽字符串，如 "150 cm"
 */
function formatWidth(width, unit) {
  if (width === null || width === undefined || width === '') return '';

  unit = unit !== undefined ? unit : 'cm';

  var num = parseFloat(width);
  if (isNaN(num)) return '';

  return num + ' ' + unit;
}

/**
 * 格式化数量
 * @param {number|string} quantity - 数量
 * @param {string} [unit='米'] - 数量单位
 * @returns {string} 格式化后的数量字符串
 */
function formatQuantity(quantity, unit) {
  if (quantity === null || quantity === undefined || quantity === '') return '';

  unit = unit !== undefined ? unit : '米';

  var num = parseInt(quantity, 10);
  if (isNaN(num)) return '';

  return num + ' ' + unit;
}

/**
 * 获取相对时间描述
 * @param {Date|string|number} date - 日期
 * @returns {string} 相对时间描述，如 "刚刚"、"5分钟前"、"2小时前"、"昨天"
 */
function getRelativeTime(date) {
  if (!date) return '';

  if (typeof date === 'string' || typeof date === 'number') {
    date = new Date(date);
  }

  if (!(date instanceof Date) || isNaN(date.getTime())) {
    return '';
  }

  var now = new Date();
  var diff = now.getTime() - date.getTime();
  var seconds = Math.floor(diff / 1000);
  var minutes = Math.floor(seconds / 60);
  var hours = Math.floor(minutes / 60);
  var days = Math.floor(hours / 24);

  if (seconds < 60) {
    return '刚刚';
  } else if (minutes < 60) {
    return minutes + '分钟前';
  } else if (hours < 24) {
    return hours + '小时前';
  } else if (days < 7) {
    return days + '天前';
  } else {
    return formatDate(date, 'YYYY-MM-DD');
  }
}

/**
 * 截断文本并添加省略号
 * @param {string} text - 原始文本
 * @param {number} [maxLength=50] - 最大长度
 * @returns {string} 截断后的文本
 */
function truncateText(text, maxLength) {
  if (!text) return '';
  maxLength = maxLength || 50;

  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength) + '...';
}

/**
 * 订单状态映射（中文）
 */
var ORDER_STATUS_MAP = {
  'pending': '待确认',
  'confirmed': '已确认',
  'producing': '生产中',
  'shipped': '已发货',
  'received': '已签收',
  'completed': '已完成'
};

/**
 * 样品状态映射（中文）
 */
var SAMPLE_STATUS_MAP = {
  'pending': '待审核',
  'approved': '已通过',
  'rejected': '已拒绝',
  'shipping': '运输中',
  'received': '已签收'
};

/**
 * 获取订单状态中文名称
 * @param {string} status - 订单状态英文标识
 * @returns {string} 中文状态名称
 */
function getOrderStatusText(status) {
  return ORDER_STATUS_MAP[status] || status || '';
}

/**
 * 获取样品状态中文名称
 * @param {string} status - 样品状态英文标识
 * @returns {string} 中文状态名称
 */
function getSampleStatusText(status) {
  return SAMPLE_STATUS_MAP[status] || status || '';
}

/**
 * 标准化图片 URL，避免小程序环境下的非法地址问题
 * 1) localhost 替换为 127.0.0.1
 * 2) 相对路径 /static/... 自动补全服务端根地址
 * 3) 明确拦截 http 远程图，返回空字符串交给调用方走占位图
 * @param {string} url
 * @returns {string}
 */
function normalizeImageUrl(url) {
  if (!url || typeof url !== 'string') return '';
  var result = url.trim();
  if (!result) return '';

  // 相对路径转绝对路径
  if (result.indexOf('/static/') === 0) {
    var app = typeof getApp === 'function' ? getApp() : null;
    var baseUrl = (app && app.globalData && app.globalData.baseUrl) || 'http://127.0.0.1:5000/api';
    var serverRoot = baseUrl.replace(/\/api\/?$/, '');
    result = serverRoot + result;
  }

  // localhost 统一替换，避免部分环境解析问题
  result = result.replace(/^http:\/\/localhost/i, 'http://127.0.0.1');
  result = result.replace(/^https:\/\/localhost/i, 'https://127.0.0.1');

  // 微信环境对 HTTP 图片限制严格，直接降级占位图，避免渲染报错
  if (/^http:\/\//i.test(result)) {
    return '';
  }

  return result;
}

module.exports = {
  formatDate: formatDate,
  padZero: padZero,
  formatPrice: formatPrice,
  formatWeight: formatWeight,
  formatWidth: formatWidth,
  formatQuantity: formatQuantity,
  getRelativeTime: getRelativeTime,
  truncateText: truncateText,
  getOrderStatusText: getOrderStatusText,
  getSampleStatusText: getSampleStatusText,
  normalizeImageUrl: normalizeImageUrl,
  ORDER_STATUS_MAP: ORDER_STATUS_MAP,
  SAMPLE_STATUS_MAP: SAMPLE_STATUS_MAP
};
