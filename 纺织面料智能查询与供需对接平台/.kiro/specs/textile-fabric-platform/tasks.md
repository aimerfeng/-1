# 实现计划：纺织面料智能查询与供需对接平台

## 概述

基于微信小程序（WXML/WXSS/JavaScript）+ Python Flask + MySQL 的全栈实现。后端使用 Flask + SQLAlchemy + Flask-JWT-Extended，前端使用微信小程序原生框架。任务按模块递增构建，每个模块包含后端模型、路由、服务实现及对应的前端页面，测试任务紧跟实现任务以尽早发现问题。

## 任务

- [x] 1. 项目初始化与基础架构搭建
  - [x] 1.1 创建 Flask 后端项目骨架
    - 创建 `server/` 目录结构：`app.py`、`config.py`、`extensions.py`、`models/`、`routes/`、`services/`、`tests/`
    - 在 `config.py` 中配置 MySQL 连接字符串、JWT 密钥、CORS 设置
    - 在 `extensions.py` 中初始化 `db = SQLAlchemy()` 和 `jwt = JWTManager()`
    - 在 `app.py` 中创建 Flask 应用工厂函数，注册扩展和蓝图
    - 创建 `requirements.txt`：flask, flask-sqlalchemy, flask-jwt-extended, flask-cors, pymysql, requests, hypothesis, pytest, werkzeug
    - 创建 `server/tests/conftest.py`，配置测试用 SQLite 内存数据库和 Flask test client fixture
    - _需求: 全局架构_

  - [x] 1.2 创建微信小程序项目骨架
    - 创建 `miniprogram/` 目录：`app.js`、`app.json`、`app.wxss`、`project.config.json`
    - 在 `app.json` 中配置页面路由和 tabBar（首页、面料、消息、我的）
    - 在 `app.wxss` 中定义全局样式变量（主色调、字体层级、间距系统）
    - 在 `app.js` 中实现全局状态管理（用户信息、登录状态）
    - _需求: 10.1_

  - [x] 1.3 实现前端网络请求封装与认证工具
    - 创建 `utils/request.js`：封装 `wx.request`，统一注入 Authorization Bearer token、处理 401 自动跳转登录、处理 >= 400 错误 Toast 提示、网络失败重试提示
    - 创建 `utils/auth.js`：封装登录态检查、token 存取（wx.getStorageSync/setStorageSync）
    - 创建 `utils/util.js`：通用工具函数（日期格式化等）
    - _需求: 10.5_

  - [x] 1.4 创建公共 UI 组件
    - 创建 `components/loading-skeleton/`（wxml/wxss/js/json）：骨架屏组件，支持不同布局模式
    - 创建 `components/empty-state/`：空状态组件，支持自定义图标和文案
    - 创建 `components/status-tag/`：状态标签组件，支持不同颜色映射
    - 创建 `components/fabric-card/`：面料卡片组件，展示缩略图、名称、关键参数、价格
    - 所有组件实现过渡动效（fadeIn、slideUp）
    - _需求: 10.1, 10.2, 10.4_

- [x] 2. 用户管理与认证模块
  - [x] 2.1 创建 User 数据模型
    - 在 `server/models/user.py` 中定义 User 模型：id, openid, phone, password_hash, role, company_name, contact_name, address, certification_status, created_at, updated_at
    - role 字段使用 Enum 限制为 buyer/supplier/admin
    - certification_status 使用 Enum 限制为 pending/approved/rejected
    - 实现密码哈希存储（werkzeug.security 的 generate_password_hash / check_password_hash）
    - _需求: 2.1_

  - [x] 2.2 编写用户角色约束属性测试
    - **Property 3: 用户角色约束**
    - 使用 Hypothesis 生成随机字符串，验证只有 buyer/supplier/admin 能通过模型角色校验
    - **验证: 需求 2.1**

  - [x] 2.3 实现认证路由
    - 在 `server/routes/auth.py` 中实现：
    - `POST /api/auth/wx-login`：接收微信 code，调用微信接口换取 openid，查找或创建用户，返回 JWT 令牌和 is_new 标志
    - `POST /api/auth/register`：手机号 + 验证码注册，校验手机号格式，创建用户，返回 JWT
    - `POST /api/auth/login`：手机号 + 密码登录，验证凭证有效性，返回 JWT；无效凭证返回明确错误信息
    - 实现手机号格式验证函数 `validate_phone(phone: str) -> bool`（1开头、第二位3-9、共11位数字）
    - 实现角色权限装饰器 `@role_required(roles)` 和认证状态检查装饰器 `@certification_required`
    - 未认证用户（certification_status != approved）访问受限端点返回 403
    - _需求: 1.1, 1.2, 1.3, 1.4, 2.5_

  - [x] 2.4 编写认证模块属性测试
    - **Property 1: 手机号格式验证** — 使用 Hypothesis 生成随机字符串，验证 validate_phone 函数对合法手机号返回 True，对非法格式返回 False
    - **Property 2: JWT 令牌有效性** — 验证有效凭证登录返回可解码 JWT 且用户 ID 一致，无效凭证返回错误
    - **Property 4: 未认证用户访问控制** — 验证 certification_status 非 approved 的用户访问受限端点返回 403
    - **验证: 需求 1.2, 1.3, 1.4, 2.5**

  - [x] 2.5 实现登录与注册页面
    - 创建 `pages/login/`（wxml/wxss/js/json）
    - 实现微信一键登录按钮（调用 `wx.login` 获取 code，请求 `/api/auth/wx-login`）
    - 实现手机号 + 验证码注册表单，含手机号格式即时校验
    - 实现手机号 + 密码登录表单
    - 首次登录（is_new=true）引导选择角色（buyer/supplier）弹窗并完善基本信息
    - 添加按钮点击动效、表单验证即时反馈（Toast 提示）
    - _需求: 1.1, 1.2, 1.5, 10.4_

  - [x] 2.6 实现个人中心页面
    - 创建 `pages/profile/`（wxml/wxss/js/json）
    - 展示用户头像、昵称、角色、认证状态
    - 实现个人信息编辑功能（公司名称、联系方式、地址），调用后端更新接口
    - 根据角色动态展示功能入口（收藏列表、订单入口、样品入口）
    - _需求: 2.2, 2.3, 2.4, 9.1_

  - [x] 2.7 编写用户资料更新属性测试
    - **Property 20: 用户资料更新往返** — 对于任意有效用户资料更新数据，更新后查询应返回更新后的值
    - **验证: 需求 9.1**

- [x] 3. 检查点 - 用户管理模块验证
  - 确保所有测试通过，如有问题请向用户确认。

- [x] 4. 面料管理模块
  - [x] 4.1 创建 Fabric 数据模型
    - 在 `server/models/fabric.py` 中定义 Fabric 模型：id, supplier_id, name, composition, weight, width, craft, color, price, min_order_qty, delivery_days, images(JSON), status, created_at, updated_at
    - status 使用 Enum：active/inactive
    - 实现面料参数校验函数 `validate_fabric(data: dict) -> tuple[bool, dict]`：校验必填字段（composition, weight, width, craft, price）存在性和数据格式，返回校验结果和具体错误字段信息
    - _需求: 3.1, 3.2, 3.5_

  - [x] 4.2 编写面料校验属性测试
    - **Property 6: 面料参数标准化校验** — 使用 Hypothesis 生成随机面料数据，验证缺少任一必填字段时校验失败并返回缺失字段名，所有必填字段存在且格式正确时校验通过
    - **Property 8: 面料字段完整性** — 验证所有面料记录包含完整字段集合（成分、克重、幅宽、工艺、颜色、价格、最小起订量、交货周期）
    - **验证: 需求 3.1, 3.2, 3.5**

  - [x] 4.3 实现面料管理路由
    - 在 `server/routes/fabric.py` 中实现：
    - `POST /api/fabrics`：创建面料（仅供应商角色），调用 validate_fabric 校验，通过后存入数据库
    - `GET /api/fabrics`：多条件筛选查询（composition, craft, price_min, price_max, weight_min, weight_max, color），分页返回（page, per_page 参数）
    - `GET /api/fabrics/<id>`：获取面料完整详情
    - `PUT /api/fabrics/<id>`：更新面料信息（仅所属供应商），保留修改历史
    - `GET /api/fabrics/compare?ids=1,2,3`：多面料参数对比，返回所有面料的完整参数
    - `POST /api/fabrics/<id>/images`：上传面料图片，存储并生成可访问 URL
    - _需求: 3.1, 3.3, 3.4, 3.6, 4.5, 4.6_

  - [x] 4.4 编写面料数据持久化与查询属性测试
    - **Property 7: 面料数据持久化往返** — 创建面料后通过 ID 查询应返回一致数据；更新后查询应返回更新后数据
    - **Property 9: 面料多条件筛选正确性** — 对于任意查询条件组合，返回的每条面料记录都满足所有指定筛选条件
    - **Property 10: 面料对比数据完整性** — 对于任意面料 ID 集合，对比结果包含每个面料的所有参数字段，且数量与请求 ID 数量一致
    - **Property 11: 分页查询正确性** — 返回结果数量不超过 per_page，total 字段正确反映满足条件的总记录数
    - **验证: 需求 3.3, 3.6, 4.1, 4.5, 4.6**

  - [x] 4.5 实现面料列表页面
    - 创建 `pages/fabric/list/`（wxml/wxss/js/json）
    - 实现筛选面板：成分下拉、工艺下拉、价格区间输入、克重范围输入、颜色选择器
    - 使用 fabric-card 组件展示面料列表（缩略图、名称、关键参数、价格）
    - 实现下拉刷新（onPullDownRefresh）和上拉加载更多（onReachBottom）
    - 数据加载时展示骨架屏，空结果展示空状态组件
    - _需求: 4.1, 4.2, 10.2, 10.3_

  - [x] 4.6 实现面料详情页面
    - 创建 `pages/fabric/detail/`（wxml/wxss/js/json）
    - 展示面料完整参数：成分、克重、幅宽、工艺、颜色、价格、最小起订量、交货周期
    - 实现图片轮播（swiper 组件）和点击放大预览（wx.previewImage，支持手势缩放）
    - 底部操作栏：收藏按钮、申请样品按钮、立即下单按钮
    - 添加页面进入动效
    - _需求: 4.3, 4.4, 10.4_

  - [x] 4.7 实现面料对比页面
    - 创建 `pages/fabric/compare/`（wxml/wxss/js/json）
    - 实现横向滚动表格，并排展示多个面料的参数差异
    - 高亮参数差异项
    - 支持从面料列表页选择面料加入对比
    - _需求: 4.5_

- [x] 5. 检查点 - 面料管理模块验证
  - 确保所有测试通过，如有问题请向用户确认。

- [x] 6. 供需对接模块
  - [x] 6.1 创建 Demand 和 MatchResult 数据模型
    - 在 `server/models/demand.py` 中定义 Demand 模型：id, buyer_id, title, composition, weight_min, weight_max, width_min, width_max, craft, color, price_min, price_max, quantity, status(open/matched/closed), created_at
    - 定义 MatchResult 模型：id, demand_id, fabric_id, score(0-100), score_detail(JSON), created_at
    - _需求: 5.1_

  - [x] 6.2 实现供需匹配引擎
    - 在 `server/services/matching.py` 中实现 MatchingEngine 类：
    - `__init__(ahp_weights: dict)`：接收 AHP 权重配置（如 composition:0.3, weight:0.2, craft:0.25, price:0.15, width:0.1）
    - `calculate_score(demand, fabric) -> float`：计算单个面料与需求的匹配度评分（0-100），包含关键词匹配（成分、工艺文本相似度）、数值匹配（克重、幅宽、价格归一化比较）、AHP 加权汇总
    - `match(demand, fabrics) -> list[MatchResult]`：对所有面料计算匹配度并按评分降序排列
    - _需求: 5.2, 5.3_

  - [x] 6.3 编写匹配引擎属性测试
    - **Property 12: 供需匹配评分范围与排序** — 对于任意需求和面料集合，每个匹配度评分在 0-100 范围内，且结果按评分降序排列
    - **Property 13: 需求发布触发匹配** — 对于任意新需求，如果存在 active 面料，匹配过程应被执行；对于任意新面料，应与所有 open 需求匹配
    - **验证: 需求 5.1, 5.2, 5.3, 5.6**

  - [x] 6.4 实现供需对接路由
    - 在 `server/routes/demand.py` 中实现：
    - `POST /api/demands`：创建采购需求（仅采购方），创建后调用 MatchingEngine 触发匹配，生成 MatchResult 记录
    - `GET /api/demands`：查询需求列表（采购方看自己的，供应商看所有 open 状态的）
    - `GET /api/demands/<id>`：获取需求详情
    - `GET /api/demands/<id>/matches`：获取匹配结果列表，按匹配度降序
    - 在 `server/routes/fabric.py` 的面料创建路由中添加：新面料发布后触发与所有 open 需求的匹配
    - 匹配结果生成后调用通知服务向相关供应商推送匹配通知
    - _需求: 5.1, 5.4, 5.6_

  - [x] 6.5 实现需求发布页面
    - 创建 `pages/demand/publish/`（wxml/wxss/js/json）
    - 实现需求表单：标题、成分要求、克重范围（min/max）、幅宽范围（min/max）、工艺要求、颜色偏好、价格区间（min/max）、数量
    - 表单验证和提交成功反馈
    - _需求: 5.1_

  - [x] 6.6 实现匹配结果页面
    - 创建 `pages/demand/match/`（wxml/wxss/js/json）
    - 展示匹配结果列表：匹配度评分（进度条可视化）、面料信息摘要、供应商基本信息
    - 点击跳转面料详情页
    - 实现下拉刷新
    - _需求: 5.5_

- [x] 7. 检查点 - 供需对接模块验证
  - 确保所有测试通过，如有问题请向用户确认。

- [x] 8. 样品管理模块
  - [x] 8.1 创建 Sample 数据模型
    - 在 `server/models/sample.py` 中定义 Sample 模型：id, fabric_id, buyer_id, supplier_id, quantity, address, status, logistics_no, logistics_info(JSON), reject_reason, created_at, updated_at
    - status 使用 Enum：pending/approved/rejected/shipping/received
    - _需求: 6.1, 6.5_

  - [x] 8.2 实现物流服务
    - 在 `server/services/logistics.py` 中实现：
    - `create_logistics(sample_id, address) -> str`：调用第三方物流 API（通过 requests 库）创建物流单，返回物流单号
    - `query_logistics(logistics_no) -> dict`：查询物流状态详情
    - `sync_logistics_status(sample_id)`：同步物流状态，状态变更时调用通知服务推送通知
    - 物流 API 调用失败时记录错误日志并标记待重试，下次同步时重试
    - _需求: 6.3, 6.4, 6.6_

  - [x] 8.3 实现样品管理路由
    - 在 `server/routes/sample.py` 中实现：
    - `POST /api/samples`：创建样品申请（仅采购方），创建后通知对应供应商
    - `GET /api/samples`：查询样品列表（采购方看自己的申请，供应商看收到的申请）
    - `PUT /api/samples/<id>/review`：审核样品申请（仅供应商），通过后触发物流创建，拒绝时记录原因；更新状态后通知采购方
    - `GET /api/samples/<id>/logistics`：查询样品物流状态
    - _需求: 6.1, 6.2, 6.3_

  - [x]* 8.4 编写样品管理属性测试
    - **Property 15: 样品申请创建与状态转换** — 对于任意样品申请，创建后状态为 pending；供应商审核通过后状态变为 approved，拒绝后变为 rejected
    - **验证: 需求 6.1, 6.2**

  - [x] 8.5 实现样品管理页面
    - 创建 `pages/sample/`（wxml/wxss/js/json）
    - 采购方视角：样品申请列表、各状态展示（待审核/已通过/已拒绝/运输中/已签收）、物流跟踪详情
    - 供应商视角：待审核列表、审核操作（通过/拒绝 + 拒绝原因输入）
    - 使用 status-tag 组件展示状态
    - 实现下拉刷新和分页加载
    - _需求: 6.5, 10.3_

- [x] 9. 订单管理模块
  - [x] 9.1 创建 Order 和 OrderItem 数据模型
    - 在 `server/models/order.py` 中定义 Order 模型：id, buyer_id, supplier_id, order_no(唯一), total_amount, address, status, created_at, updated_at
    - 定义 OrderItem 模型：id, order_id, fabric_id, quantity, unit_price, subtotal
    - status 使用 Enum：pending/confirmed/producing/shipped/received/completed
    - 实现订单号生成函数（时间戳 + 随机数）
    - 实现状态机校验函数 `validate_status_transition(current: str, next: str) -> bool`，只允许 pending→confirmed→producing→shipped→received→completed 顺序转换
    - _需求: 7.1, 7.6_

  - [x] 9.2 编写订单状态机属性测试
    - **Property 17: 订单状态机合法性** — 使用 Hypothesis 生成随机状态转换序列，验证只有合法顺序转换被允许，跳跃或逆向转换被拒绝
    - **验证: 需求 7.3, 7.6**

  - [x] 9.3 实现订单管理路由
    - 在 `server/routes/order.py` 中实现：
    - `POST /api/orders`：创建订单（仅采购方），校验面料存在性、数量、价格、收货地址必填；校验失败返回具体错误信息
    - `GET /api/orders`：查询订单列表，按创建时间降序，分页返回
    - `GET /api/orders/<id>`：获取订单详情（含 OrderItem 列表、面料信息、状态时间线）
    - `PUT /api/orders/<id>/status`：更新订单状态，调用 validate_status_transition 校验合法性，状态变更后推送通知
    - _需求: 7.1, 7.2, 7.3, 7.4, 7.5_

  - [x]* 9.4 编写订单创建属性测试
    - **Property 16: 订单创建往返** — 对于任意有效订单数据，创建后通过 ID 查询应返回一致信息；缺少必填字段的数据创建应失败
    - **验证: 需求 7.1, 7.2**

  - [x] 9.5 实现订单列表页面
    - 创建 `pages/order/list/`（wxml/wxss/js/json）
    - 展示订单列表：订单号、面料摘要、金额、状态标签
    - 实现状态筛选 tab（全部/待确认/生产中/已发货/已完成）
    - 实现下拉刷新和分页加载
    - _需求: 7.4, 10.3_

  - [x] 9.6 实现订单创建页面
    - 创建 `pages/order/create/`（wxml/wxss/js/json）
    - 实现订单表单：面料选择、数量输入、价格确认、收货地址填写
    - 实现金额自动计算（数量 × 单价）
    - 表单验证和提交确认弹窗
    - _需求: 7.1_

  - [x] 9.7 实现订单详情页面
    - 创建 `pages/order/detail/`（wxml/wxss/js/json）
    - 展示订单完整信息：订单号、面料明细（名称、数量、单价、小计）、总金额、收货地址
    - 展示订单状态时间线（纵向步骤条，标注各状态时间）
    - 供应商可操作更新状态按钮（根据当前状态展示下一步操作）
    - _需求: 7.5, 7.6_

- [x] 10. 检查点 - 样品与订单模块验证
  - 确保所有测试通过，如有问题请向用户确认。

- [x] 11. 消息通知模块
  - [x] 11.1 创建 Message 数据模型
    - 在 `server/models/message.py` 中定义 Message 模型：id, user_id, type, title, content, ref_id, ref_type, is_read, created_at
    - type 使用 Enum：match/logistics/review/order/system
    - 确保每条消息包含完整字段：消息类型、标题、内容、关联业务ID、创建时间、已读状态
    - _需求: 8.6_

  - [x] 11.2 实现通知服务
    - 在 `server/services/notification.py` 中实现：
    - `create_notification(user_id, type, title, content, ref_id, ref_type) -> Message`：创建通知消息记录
    - 在以下业务事件中调用：匹配结果生成（type=match）、物流状态更新（type=logistics）、审核结果产生（type=review）、订单状态变更（type=order）
    - _需求: 8.1, 8.2, 8.3_

  - [x] 11.3 编写消息通知属性测试
    - **Property 14: 事件触发通知创建** — 对于任意业务事件（匹配/物流/审核），系统应为相关用户创建包含正确类型和关联业务 ID 的通知消息
    - **Property 18: 消息已读标记** — 对于任意未读消息，标记已读后 is_read 为 true；对已读消息重复标记保持幂等
    - **Property 19: 消息字段完整性** — 对于任意消息记录，应包含消息类型、标题、内容、关联业务ID、创建时间、已读状态
    - **验证: 需求 5.4, 8.1, 8.2, 8.3, 8.5, 8.6**

  - [x] 11.4 实现消息路由
    - 在 `server/routes/message.py` 中实现：
    - `GET /api/messages`：查询当前用户消息列表，按时间降序，分页返回，区分已读/未读
    - `PUT /api/messages/<id>/read`：标记消息为已读
    - `GET /api/messages/unread-count`：获取未读消息数量（用于 tabBar 角标显示）
    - _需求: 8.4, 8.5_

  - [x] 11.5 实现消息中心页面
    - 创建 `pages/message/`（wxml/wxss/js/json）
    - 展示消息列表：类型图标、标题、内容摘要、时间、已读/未读状态
    - 未读消息高亮显示
    - 点击消息：标记已读并跳转对应详情页（匹配结果页/订单详情页/样品详情页）
    - 实现下拉刷新
    - _需求: 8.4, 8.5, 10.3_

- [x] 12. 收藏功能模块
  - [x] 12.1 创建 Favorite 数据模型和收藏路由
    - 在 `server/models/fabric.py` 中定义 Favorite 模型：id, user_id, fabric_id, created_at
    - 在 `server/routes/fabric.py` 中添加：
    - `POST /api/fabrics/<id>/favorite`：收藏面料（防止重复收藏）
    - `DELETE /api/fabrics/<id>/favorite`：取消收藏
    - `GET /api/favorites`：查询当前用户收藏列表，展示面料缩略信息和当前状态
    - _需求: 9.2, 9.3, 9.4_

  - [x] 12.2 编写收藏功能属性测试
    - **Property 21: 收藏往返** — 对于任意用户和面料，收藏后查询收藏列表应包含该面料；取消收藏后查询应不包含该面料
    - **验证: 需求 9.2, 9.3**

  - [x] 12.3 实现收藏列表页面
    - 在个人中心页面添加收藏列表入口
    - 创建收藏列表页面，使用 fabric-card 组件展示已收藏面料
    - 支持滑动删除取消收藏
    - _需求: 9.4_

- [x] 13. 首页与导航整合
  - [x] 13.1 实现首页
    - 创建 `pages/home/`（wxml/wxss/js/json）
    - 顶部搜索栏（跳转面料查询页）
    - 功能入口网格（面料查询、需求发布、样品管理、订单管理），根据角色动态展示
    - 最新匹配推荐列表（调用匹配结果接口）
    - 数据加载时展示骨架屏
    - _需求: 2.2, 2.3, 2.4, 10.2_

  - [x] 13.2 整合 tabBar 导航和全局页面跳转
    - 配置 tabBar 四个入口：首页、面料、消息、我的
    - 消息 tab 展示未读消息角标（轮询 unread-count 接口）
    - 确保所有页面间跳转逻辑正确（wx.navigateTo / wx.switchTab）
    - 添加页面切换过渡动效
    - 确保所有页面在不同尺寸手机屏幕上正确适配
    - _需求: 9.5, 10.1, 10.4, 10.6_

- [x] 14. 管理员功能
  - [x] 14.1 实现管理员审核路由
    - 在 `server/routes/auth.py` 中添加：
    - `GET /api/admin/users`：查询待审核用户列表（仅管理员）
    - `PUT /api/admin/users/<id>/certify`：审核用户资质（通过/拒绝），更新 certification_status，触发审核通知
    - _需求: 2.6_

  - [x] 14.2 编写资质审核属性测试
    - **Property 5: 用户资质审核状态转换** — 对于任意 pending 状态用户，管理员审核通过后 certification_status 变为 approved 且生成审核通知消息
    - **验证: 需求 2.6**

  - [x] 14.3 实现管理员审核页面
    - 创建管理员专属页面，展示待审核用户列表（公司名称、联系方式、申请时间）
    - 实现审核操作（通过/拒绝 + 拒绝原因输入）
    - 展示数据统计概览（用户数、面料数、订单数）
    - _需求: 2.4, 2.6_

- [x] 15. 最终检查点 - 全模块集成验证
  - 确保所有测试通过，如有问题请向用户确认。
  - 验证所有页面间跳转逻辑正确
  - 验证所有 API 接口与前端对接正常
  - 确认小程序可在微信开发者工具中正常运行

## 备注

- 标记 `*` 的子任务为可选任务，可跳过以加快 MVP 进度
- 每个任务引用了具体的需求编号以确保可追溯性
- 检查点确保增量验证
- 属性测试使用 Hypothesis 库，每个属性测试最少运行 100 次迭代
- 属性测试标签格式：**Feature: textile-fabric-platform, Property {编号}: {属性描述}**
- 单元测试验证具体示例和边界情况，属性测试验证通用正确性属性
