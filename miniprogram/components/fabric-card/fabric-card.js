/**
 * fabric-card 面料卡片组件
 * 展示缩略图、名称、关键参数（成分、克重）、价格
 * 需求 4.2: 以列表形式展示面料信息
 * 需求 10.1: 统一视觉设计规范
 * 需求 10.4: 提供即时的视觉反馈
 */
var util = require('../../utils/util.js');

Component({
  properties: {
    /** 面料数据对象 */
    fabric: {
      type: Object,
      value: {}
    },
    /** 卡片布局模式: card（卡片）| list（列表行） */
    mode: {
      type: String,
      value: 'card'
    },
    /** 是否显示收藏按钮 */
    showFavorite: {
      type: Boolean,
      value: false
    },
    /** 是否已收藏 */
    isFavorited: {
      type: Boolean,
      value: false
    }
  },

  data: {
    /** 格式化后的价格 */
    formattedPrice: '',
    /** 格式化后的克重 */
    formattedWeight: '',
    /** 缩略图 URL */
    thumbUrl: '',
    /** 默认占位图（待替换为真实图片） */
    defaultImage: '/assets/images/fabric-placeholder.png'
  },

  lifetimes: {
    attached: function () {
      this._formatData();
    }
  },

  observers: {
    'fabric': function () {
      this._formatData();
    }
  },

  methods: {
    /**
     * 格式化面料数据用于展示
     */
    _formatData: function () {
      var fabric = this.data.fabric;
      if (!fabric) return;

      var formattedPrice = util.formatPrice(fabric.price);
      var formattedWeight = util.formatWeight(fabric.weight);

      // 取第一张图片作为缩略图
      var thumbUrl = '';
      if (fabric.images && fabric.images.length > 0) {
        thumbUrl = util.normalizeImageUrl(fabric.images[0]);
      }

      this.setData({
        formattedPrice: formattedPrice,
        formattedWeight: formattedWeight,
        thumbUrl: thumbUrl
      });
    },

    /**
     * 卡片点击事件
     */
    onCardTap: function () {
      this.triggerEvent('tap', { fabric: this.data.fabric });
    },

    /**
     * 收藏按钮点击事件
     */
    onFavoriteTap: function (e) {
      // 阻止冒泡到卡片点击
      this.triggerEvent('favorite', {
        fabric: this.data.fabric,
        isFavorited: !this.data.isFavorited
      });
    },

    /**
     * 图片加载失败时使用占位图
     */
    onImageError: function () {
      this.setData({
        thumbUrl: ''
      });
    }
  }
});
