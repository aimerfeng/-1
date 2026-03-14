// pages/fabric/publish/publish.js
var request = require('../../../utils/request');

Page({
  data: {
    loading: false,
    isEdit: false,
    fabricId: null,
    form: {
      name: '',
      composition: '',
      weight: '',
      width: '',
      craft: '',
      color: '',
      price: '',
      min_order_qty: '',
      delivery_days: '',
      stock_quantity: ''
    }
  },

  onLoad: function (options) {
    if (options.id) {
      this.setData({ isEdit: true, fabricId: options.id });
      this._loadFabric(options.id);
    }
  },

  _loadFabric: function (id) {
    var that = this;
    this.setData({ loading: true });
    request.get('/fabrics/' + id).then(function (res) {
      that.setData({
        loading: false,
        form: {
          name: res.name || '',
          composition: res.composition || '',
          weight: res.weight ? String(res.weight) : '',
          width: res.width ? String(res.width) : '',
          craft: res.craft || '',
          color: res.color || '',
          price: res.price ? String(res.price) : '',
          min_order_qty: res.min_order_qty ? String(res.min_order_qty) : '',
          delivery_days: res.delivery_days ? String(res.delivery_days) : '',
          stock_quantity: res.stock_quantity ? String(res.stock_quantity) : ''
        }
      });
    }).catch(function () {
      that.setData({ loading: false });
      wx.showToast({ title: '加载失败', icon: 'none' });
    });
  },

  onInput: function (e) {
    var field = e.currentTarget.dataset.field;
    var obj = {};
    obj['form.' + field] = e.detail.value;
    this.setData(obj);
  },

  onSubmit: function () {
    var form = this.data.form;
    if (!form.name.trim()) {
      wx.showToast({ title: '请输入面料名称', icon: 'none' }); return;
    }
    if (!form.composition.trim()) {
      wx.showToast({ title: '请输入成分', icon: 'none' }); return;
    }
    if (!form.weight || parseFloat(form.weight) <= 0) {
      wx.showToast({ title: '请输入有效克重', icon: 'none' }); return;
    }
    if (!form.width || parseFloat(form.width) <= 0) {
      wx.showToast({ title: '请输入有效幅宽', icon: 'none' }); return;
    }
    if (!form.craft.trim()) {
      wx.showToast({ title: '请输入工艺', icon: 'none' }); return;
    }
    if (!form.price || parseFloat(form.price) <= 0) {
      wx.showToast({ title: '请输入有效价格', icon: 'none' }); return;
    }

    var payload = {
      name: form.name.trim(),
      composition: form.composition.trim(),
      weight: parseFloat(form.weight),
      width: parseFloat(form.width),
      craft: form.craft.trim(),
      color: form.color.trim() || null,
      price: parseFloat(form.price),
      min_order_qty: form.min_order_qty ? parseInt(form.min_order_qty) : null,
      delivery_days: form.delivery_days ? parseInt(form.delivery_days) : null,
      stock_quantity: form.stock_quantity ? parseInt(form.stock_quantity) : 0
    };

    var that = this;
    this.setData({ loading: true });

    var promise;
    if (this.data.isEdit) {
      promise = request.put('/fabrics/' + this.data.fabricId, payload);
    } else {
      promise = request.post('/fabrics', payload);
    }

    promise.then(function () {
      that.setData({ loading: false });
      wx.showToast({
        title: that.data.isEdit ? '修改成功' : '发布成功',
        icon: 'success'
      });
      setTimeout(function () {
        wx.navigateBack();
      }, 1500);
    }).catch(function (err) {
      that.setData({ loading: false });
      var msg = (err && err.message) || '操作失败';
      wx.showToast({ title: msg, icon: 'none' });
    });
  }
});
