/**
 * empty-state 空状态组件
 * 支持自定义图标和文案
 * 需求 10.4: 提供即时的视觉反馈
 */
Component({
  properties: {
    /** 图标类型（使用内置图标名称或自定义图片路径） */
    icon: {
      type: String,
      value: 'default'
    },
    /** 标题文案 */
    title: {
      type: String,
      value: '暂无数据'
    },
    /** 描述文案 */
    description: {
      type: String,
      value: ''
    },
    /** 操作按钮文案（为空则不显示按钮） */
    actionText: {
      type: String,
      value: ''
    }
  },

  data: {
    /** 是否使用自定义图片路径 */
    isCustomIcon: false,
    /** 最终使用的图标路径 */
    iconSrc: '',
    /** emoji 图标 */
    iconEmoji: '📭'
  },

  lifetimes: {
    attached: function () {
      this._resolveIcon();
    }
  },

  observers: {
    'icon': function () {
      this._resolveIcon();
    }
  },

  methods: {
    /**
     * 解析图标：内置名称使用 emoji 占位，其他视为自定义路径
     */
    _resolveIcon: function () {
      var icon = this.data.icon;
      var emojiMap = {
        'default': '📭',
        'search': '🔍',
        'network': '🌐',
        'order': '📋',
        'favorite': '❤️',
        'message': '💬',
        'empty': '📭',
        'error': '⚠️'
      };
      var emoji = emojiMap[icon];
      if (emoji) {
        // 内置图标：使用 emoji 占位，不加载图片
        this.setData({
          isCustomIcon: false,
          iconSrc: '',
          iconEmoji: emoji
        });
      } else {
        // 自定义路径
        this.setData({
          isCustomIcon: true,
          iconSrc: icon,
          iconEmoji: ''
        });
      }
    },

    /**
     * 操作按钮点击事件
     */
    onActionTap: function () {
      this.triggerEvent('action');
    },

    /**
     * 图片加载失败时回退到 CSS 占位图标
     */
    onIconError: function () {
      this.setData({
        isCustomIcon: false,
        iconSrc: ''
      });
    }
  }
});
