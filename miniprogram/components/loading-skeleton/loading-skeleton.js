/**
 * loading-skeleton 骨架屏组件
 * 支持不同布局模式：list（列表）、card（卡片）、detail（详情）
 * 需求 10.2: 页面加载数据时展示骨架屏，避免空白等待
 */
Component({
  properties: {
    /** 布局模式: list | card | detail */
    mode: {
      type: String,
      value: 'list'
    },
    /** 骨架行数（list 模式下生效） */
    rows: {
      type: Number,
      value: 3
    },
    /** 是否显示头像占位（list 模式下生效） */
    avatar: {
      type: Boolean,
      value: false
    },
    /** 是否启用动画 */
    animate: {
      type: Boolean,
      value: true
    },
    /** 卡片列数（card 模式下生效） */
    cardCount: {
      type: Number,
      value: 4
    }
  },

  data: {
    rowArray: [],
    cardArray: []
  },

  lifetimes: {
    attached: function () {
      this._buildArrays();
    }
  },

  observers: {
    'rows': function () {
      this._buildArrays();
    },
    'cardCount': function () {
      this._buildArrays();
    }
  },

  methods: {
    _buildArrays: function () {
      var rowArr = [];
      for (var i = 0; i < this.data.rows; i++) {
        rowArr.push(i);
      }
      var cardArr = [];
      for (var j = 0; j < this.data.cardCount; j++) {
        cardArr.push(j);
      }
      this.setData({
        rowArray: rowArr,
        cardArray: cardArr
      });
    }
  }
});
