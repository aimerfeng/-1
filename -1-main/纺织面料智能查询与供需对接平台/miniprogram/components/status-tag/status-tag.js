/**
 * status-tag 状态标签组件
 * 支持不同状态到颜色的映射
 * 需求 10.1: 统一视觉设计规范
 * 需求 10.4: 提供即时的视觉反馈
 */
Component({
  properties: {
    /** 状态值（英文标识） */
    status: {
      type: String,
      value: ''
    },
    /** 显示文本（如不传则自动从 statusTextMap 映射） */
    text: {
      type: String,
      value: ''
    },
    /** 标签尺寸: small | default | large */
    size: {
      type: String,
      value: 'default'
    },
    /** 是否使用圆角胶囊样式 */
    round: {
      type: Boolean,
      value: true
    },
    /** 自定义颜色类型（覆盖自动映射）: primary | success | warning | danger | info */
    type: {
      type: String,
      value: ''
    }
  },

  data: {
    /** 状态 → 颜色类型映射 */
    statusColorMap: {
      // 通用状态
      'pending': 'warning',
      'approved': 'success',
      'rejected': 'danger',
      'active': 'success',
      'inactive': 'info',
      // 订单状态
      'confirmed': 'primary',
      'producing': 'info',
      'shipped': 'primary',
      'received': 'success',
      'completed': 'success',
      // 样品状态
      'shipping': 'primary',
      // 需求状态
      'open': 'success',
      'matched': 'primary',
      'closed': 'info'
    },
    /** 状态 → 中文文本映射 */
    statusTextMap: {
      // 通用状态
      'pending': '待处理',
      'approved': '已通过',
      'rejected': '已拒绝',
      'active': '有效',
      'inactive': '无效',
      // 订单状态
      'confirmed': '已确认',
      'producing': '生产中',
      'shipped': '已发货',
      'received': '已签收',
      'completed': '已完成',
      // 样品状态
      'shipping': '运输中',
      // 需求状态
      'open': '进行中',
      'matched': '已匹配',
      'closed': '已关闭'
    },
    /** 计算后的颜色类型 */
    colorType: 'info',
    /** 计算后的显示文本 */
    displayText: ''
  },

  lifetimes: {
    attached: function () {
      this._computeDisplay();
    }
  },

  observers: {
    'status, text, type': function () {
      this._computeDisplay();
    }
  },

  methods: {
    _computeDisplay: function () {
      var status = this.data.status;
      var text = this.data.text;
      var type = this.data.type;

      // 颜色类型：优先使用自定义 type，否则从映射表查找
      var colorType = type || this.data.statusColorMap[status] || 'info';

      // 显示文本：优先使用自定义 text，否则从映射表查找
      var displayText = text || this.data.statusTextMap[status] || status || '';

      this.setData({
        colorType: colorType,
        displayText: displayText
      });
    }
  }
});
