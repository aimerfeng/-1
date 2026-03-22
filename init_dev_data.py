"""
初始化开发数据脚本
填充纺织面料平台的示例数据，包括：
- 用户（管理员、采购方、供应商）
- 面料数据（棉、毛、麻、丝、化纤等品类，参考 GB/T 5705-2018 等国标）
- 采购需求
- 报价

运行方式：
  python init_dev_data.py
"""

import sys
import os

# 确保项目根目录在 path 中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 在导入 server 模块之前设置 SQLite 数据库路径
# DevelopmentConfig 在类定义时读取 DATABASE_URL 环境变量
_basedir = os.path.abspath(os.path.dirname(__file__))
_instance_dir = os.path.join(_basedir, 'instance')
os.makedirs(_instance_dir, exist_ok=True)
os.environ['DATABASE_URL'] = 'sqlite:///' + os.path.join(_instance_dir, 'dev.db')

from server.app import create_app
from server.extensions import db
from server.models.user import User
from server.models.fabric import Fabric
from server.models.demand import Demand, Quote


def create_users():
    """创建示例用户"""
    users = []

    # 管理员
    admin = User(
        phone='13800000001',
        role='admin',
        company_name='平台管理中心',
        contact_name='系统管理员',
        address='浙江省杭州市西湖区',
        certification_status='approved',
    )
    admin.set_password('admin123')
    users.append(admin)

    # 采购方
    buyers = [
        {
            'phone': '13800000010',
            'company_name': '杭州锦绣服饰有限公司',
            'contact_name': '张明',
            'address': '浙江省杭州市萧山区市心北路',
        },
        {
            'phone': '13800000011',
            'company_name': '上海华裳时装集团',
            'contact_name': '李婷',
            'address': '上海市长宁区延安西路',
        },
        {
            'phone': '13800000012',
            'company_name': '广州粤织家纺有限公司',
            'contact_name': '陈伟',
            'address': '广东省广州市海珠区新港东路',
        },
    ]
    for b in buyers:
        user = User(role='buyer', certification_status='approved', **b)
        user.set_password('buyer123')
        users.append(user)

    # 供应商
    suppliers = [
        {
            'phone': '13800000020',
            'company_name': '绍兴柯桥恒丰纺织有限公司',
            'contact_name': '王建国',
            'address': '浙江省绍兴市柯桥区中国轻纺城',
        },
        {
            'phone': '13800000021',
            'company_name': '江苏盛泽丝绸科技股份有限公司',
            'contact_name': '刘芳',
            'address': '江苏省苏州市吴江区盛泽镇',
        },
        {
            'phone': '13800000022',
            'company_name': '山东鲁棉纺织集团有限公司',
            'contact_name': '赵强',
            'address': '山东省滨州市滨城区黄河五路',
        },
        {
            'phone': '13800000023',
            'company_name': '河北宁纺集团有限责任公司',
            'contact_name': '孙丽',
            'address': '河北省宁晋县凤凰路',
        },
        {
            'phone': '13800000024',
            'company_name': '福建长乐力恒锦纶科技有限公司',
            'contact_name': '周磊',
            'address': '福建省福州市长乐区滨海工业区',
        },
    ]
    for s in suppliers:
        user = User(role='supplier', certification_status='approved', **s)
        user.set_password('supplier123')
        users.append(user)

    for u in users:
        db.session.add(u)
    db.session.flush()
    return users


def create_fabrics(suppliers):
    """
    创建示例面料数据
    参考国标分类：棉纺织品(GB/T 5705)、毛纺织品(GB/T 5706)、
    麻纺织品(GB/T 5707)、纺织纤维编码(GB/T 36612)
    """
    # suppliers[0] = 绍兴恒丰, [1] = 盛泽丝绸, [2] = 鲁棉, [3] = 宁纺, [4] = 力恒锦纶
    s0, s1, s2, s3, s4 = [s.id for s in suppliers]

    # 9张布料图片，循环分配
    BASE_IMG = 'http://localhost:5000/static/uploads/fabrics/'
    IMGS = [BASE_IMG + f'fabric_0{i}.jpg' for i in range(1, 10)]

    def imgs(*indices):
        """按指定索引取图片（0-based），最多3张"""
        return [IMGS[i % 9] for i in indices]

    fabrics_data = [
        # ========== 棉纺织品 (GB/T 5705-2018) ==========
        {
            'supplier_id': s2, 'name': '精梳纯棉府绸',
            'composition': '100%精梳棉', 'weight': 120, 'width': 150,
            'craft': '平纹', 'color': '漂白', 'price': 18.5,
            'min_order_qty': 500, 'delivery_days': 7,
            'images': imgs(0, 1),
        },
        {
            'supplier_id': s2, 'name': '全棉斜纹布',
            'composition': '100%棉', 'weight': 180, 'width': 150,
            'craft': '斜纹', 'color': '藏青', 'price': 22.0,
            'min_order_qty': 300, 'delivery_days': 10,
            'images': imgs(1, 2),
        },
        {
            'supplier_id': s2, 'name': '纯棉牛仔布 10oz',
            'composition': '100%棉', 'weight': 340, 'width': 150,
            'craft': '斜纹/靛蓝染色', 'color': '靛蓝', 'price': 32.0,
            'min_order_qty': 500, 'delivery_days': 15,
            'images': imgs(2, 3),
        },
        {
            'supplier_id': s3, 'name': '棉涤混纺衬衫面料',
            'composition': '60%棉/40%涤纶', 'weight': 110, 'width': 145,
            'craft': '平纹', 'color': '浅蓝条纹', 'price': 15.0,
            'min_order_qty': 1000, 'delivery_days': 7,
            'images': imgs(3, 4),
        },
        {
            'supplier_id': s3, 'name': '全棉灯芯绒 14条',
            'composition': '100%棉', 'weight': 280, 'width': 150,
            'craft': '灯芯绒', 'color': '驼色', 'price': 28.5,
            'min_order_qty': 300, 'delivery_days': 12,
            'images': imgs(4, 5),
        },
        {
            'supplier_id': s2, 'name': '有机棉针织汗布',
            'composition': '100%有机棉(GOTS认证)', 'weight': 160, 'width': 180,
            'craft': '针织/单面', 'color': '本白', 'price': 35.0,
            'min_order_qty': 200, 'delivery_days': 10,
            'images': imgs(5, 6),
        },
        {
            'supplier_id': s3, 'name': '棉氨弹力卡其布',
            'composition': '97%棉/3%氨纶', 'weight': 220, 'width': 150,
            'craft': '斜纹/弹力', 'color': '卡其', 'price': 26.0,
            'min_order_qty': 500, 'delivery_days': 10,
            'images': imgs(6, 7),
        },

        # ========== 毛纺织品 (GB/T 5706-2018) ==========
        {
            'supplier_id': s0, 'name': '精纺羊毛西装面料',
            'composition': '100%澳洲美利奴羊毛', 'weight': 260, 'width': 150,
            'craft': '精纺/斜纹', 'color': '深灰', 'price': 120.0,
            'min_order_qty': 100, 'delivery_days': 20,
            'images': imgs(7, 8),
        },
        {
            'supplier_id': s0, 'name': '毛涤混纺花呢',
            'composition': '70%羊毛/30%涤纶', 'weight': 320, 'width': 150,
            'craft': '粗纺/花呢', 'color': '灰蓝格纹', 'price': 85.0,
            'min_order_qty': 100, 'delivery_days': 15,
            'images': imgs(8, 0),
        },
        {
            'supplier_id': s0, 'name': '羊绒混纺大衣呢',
            'composition': '50%羊绒/50%羊毛', 'weight': 450, 'width': 150,
            'craft': '粗纺/双面呢', 'color': '驼色', 'price': 280.0,
            'min_order_qty': 50, 'delivery_days': 25,
            'images': imgs(0, 1, 2),
        },

        # ========== 麻纺织品 (GB/T 5707-2018) ==========
        {
            'supplier_id': s3, 'name': '纯亚麻平纹布',
            'composition': '100%亚麻', 'weight': 180, 'width': 145,
            'craft': '平纹', 'color': '原色', 'price': 45.0,
            'min_order_qty': 200, 'delivery_days': 12,
            'images': imgs(1, 2),
        },
        {
            'supplier_id': s3, 'name': '棉麻混纺休闲面料',
            'composition': '55%棉/45%亚麻', 'weight': 200, 'width': 150,
            'craft': '平纹', 'color': '浅灰', 'price': 38.0,
            'min_order_qty': 300, 'delivery_days': 10,
            'images': imgs(2, 3),
        },
        {
            'supplier_id': s3, 'name': '苎麻夏季衬衫面料',
            'composition': '100%苎麻', 'weight': 140, 'width': 140,
            'craft': '平纹', 'color': '白色', 'price': 52.0,
            'min_order_qty': 200, 'delivery_days': 14,
            'images': imgs(3, 4),
        },

        # ========== 丝绸面料 ==========
        {
            'supplier_id': s1, 'name': '真丝素绉缎',
            'composition': '100%桑蚕丝(19姆米)', 'weight': 80, 'width': 140,
            'craft': '缎纹', 'color': '香槟色', 'price': 98.0,
            'min_order_qty': 100, 'delivery_days': 15,
            'images': imgs(4, 5),
        },
        {
            'supplier_id': s1, 'name': '真丝乔其纱',
            'composition': '100%桑蚕丝(8姆米)', 'weight': 35, 'width': 140,
            'craft': '平纹/乔其', 'color': '粉色', 'price': 68.0,
            'min_order_qty': 100, 'delivery_days': 12,
            'images': imgs(5, 6),
        },
        {
            'supplier_id': s1, 'name': '真丝双绉',
            'composition': '100%桑蚕丝(16姆米)', 'weight': 65, 'width': 140,
            'craft': '绉纹', 'color': '墨绿', 'price': 88.0,
            'min_order_qty': 100, 'delivery_days': 14,
            'images': imgs(6, 7),
        },

        # ========== 化纤面料 (GB/T 36612-2018 纺织纤维编码) ==========
        {
            'supplier_id': s4, 'name': '涤纶塔夫绸',
            'composition': '100%涤纶', 'weight': 70, 'width': 150,
            'craft': '平纹/塔夫', 'color': '黑色', 'price': 8.5,
            'min_order_qty': 2000, 'delivery_days': 5,
            'images': imgs(7, 8),
        },
        {
            'supplier_id': s4, 'name': '锦纶四面弹力面料',
            'composition': '85%锦纶/15%氨纶', 'weight': 160, 'width': 150,
            'craft': '针织/四面弹', 'color': '黑色', 'price': 25.0,
            'min_order_qty': 500, 'delivery_days': 7,
            'images': imgs(8, 0),
        },
        {
            'supplier_id': s4, 'name': '涤纶仿真丝雪纺',
            'composition': '100%涤纶', 'weight': 55, 'width': 150,
            'craft': '平纹/雪纺', 'color': '碎花印花', 'price': 12.0,
            'min_order_qty': 1000, 'delivery_days': 7,
            'images': imgs(0, 1),
        },
        {
            'supplier_id': s4, 'name': '涤纶春亚纺',
            'composition': '100%涤纶', 'weight': 75, 'width': 150,
            'craft': '平纹/春亚纺', 'color': '军绿', 'price': 7.5,
            'min_order_qty': 3000, 'delivery_days': 5,
            'images': imgs(1, 2),
        },
        {
            'supplier_id': s1, 'name': '醋酸缎面礼服面料',
            'composition': '100%醋酸纤维', 'weight': 120, 'width': 140,
            'craft': '缎纹', 'color': '酒红', 'price': 55.0,
            'min_order_qty': 200, 'delivery_days': 12,
            'images': imgs(2, 3),
        },

        # ========== 功能性面料 ==========
        {
            'supplier_id': s0, 'name': 'COOLMAX速干运动面料',
            'composition': '100%涤纶(COOLMAX)', 'weight': 140, 'width': 160,
            'craft': '针织/网眼', 'color': '宝蓝', 'price': 30.0,
            'min_order_qty': 500, 'delivery_days': 10,
            'images': imgs(3, 4),
        },
        {
            'supplier_id': s0, 'name': 'GORE-TEX三层复合面料',
            'composition': '涤纶/PTFE膜/涤纶', 'weight': 200, 'width': 150,
            'craft': '复合/防水透湿', 'color': '黑色', 'price': 150.0,
            'min_order_qty': 200, 'delivery_days': 20,
            'images': imgs(4, 5),
        },
        {
            'supplier_id': s4, 'name': '阻燃涤棉工装面料',
            'composition': '65%涤纶/35%棉(阻燃处理)', 'weight': 240, 'width': 150,
            'craft': '斜纹/阻燃', 'color': '藏蓝', 'price': 35.0,
            'min_order_qty': 1000, 'delivery_days': 15,
            'images': imgs(5, 6),
        },
        {
            'supplier_id': s4, 'name': '抗菌防臭银离子面料',
            'composition': '90%涤纶/10%银离子纤维', 'weight': 130, 'width': 160,
            'craft': '针织/抗菌', 'color': '灰色', 'price': 42.0,
            'min_order_qty': 300, 'delivery_days': 12,
            'images': imgs(6, 7),
        },

        # ========== 家纺面料 ==========
        {
            'supplier_id': s2, 'name': '60支长绒棉贡缎',
            'composition': '100%长绒棉', 'weight': 150, 'width': 280,
            'craft': '缎纹/贡缎', 'color': '象牙白', 'price': 48.0,
            'min_order_qty': 500, 'delivery_days': 10,
            'images': imgs(7, 8),
        },
        {
            'supplier_id': s1, 'name': '天丝莱赛尔床品面料',
            'composition': '100%莱赛尔(天丝)', 'weight': 130, 'width': 280,
            'craft': '缎纹', 'color': '浅蓝', 'price': 58.0,
            'min_order_qty': 300, 'delivery_days': 12,
            'images': imgs(8, 0),
        },
        {
            'supplier_id': s0, 'name': '法兰绒毛毯面料',
            'composition': '100%涤纶', 'weight': 300, 'width': 200,
            'craft': '针织/法兰绒', 'color': '米白', 'price': 18.0,
            'min_order_qty': 500, 'delivery_days': 7,
            'images': imgs(0, 1),
        },
    ]

    fabrics = []
    # 默认库存量映射（按面料索引）
    stock_quantities = [
        8000, 5000, 3000, 15000, 4000, 3000, 6000,   # 棉 7条
        2000, 2000, 800,                                # 毛 3条
        3000, 5000, 2500,                               # 麻 3条
        1500, 2000, 1800,                               # 丝 3条
        20000, 8000, 12000, 25000, 3000,                # 化纤 5条
        5000, 1000, 10000, 4000,                        # 功能性 4条
        8000, 5000, 6000,                               # 家纺 3条
    ]
    for i, fd in enumerate(fabrics_data):
        fd['stock_quantity'] = stock_quantities[i] if i < len(stock_quantities) else 5000
        f = Fabric(status='active', **fd)
        db.session.add(f)
        fabrics.append(f)

    db.session.flush()
    return fabrics


def create_demands(buyers):
    """创建示例采购需求"""
    # buyers[0] = 杭州锦绣(张明), [1] = 上海华裳(李婷), [2] = 广州粤织(陈伟)
    demands_data = [
        {
            'buyer_id': buyers[0].id,
            'title': '春夏女装纯棉面料采购',
            'composition': '100%棉',
            'weight_min': 100, 'weight_max': 160,
            'width_min': 140, 'width_max': 160,
            'craft': '平纹',
            'color': '白色',
            'price_min': 15.0, 'price_max': 25.0,
            'quantity': 2000,
            'status': 'open',
        },
        {
            'buyer_id': buyers[0].id,
            'title': '秋冬男装西装毛料采购',
            'composition': '羊毛',
            'weight_min': 240, 'weight_max': 300,
            'width_min': 145, 'width_max': 155,
            'craft': '精纺',
            'color': '深灰',
            'price_min': 80.0, 'price_max': 150.0,
            'quantity': 500,
            'status': 'open',
        },
        {
            'buyer_id': buyers[1].id,
            'title': '高端真丝连衣裙面料',
            'composition': '桑蚕丝',
            'weight_min': 50, 'weight_max': 90,
            'width_min': 135, 'width_max': 145,
            'craft': '缎纹',
            'color': None,
            'price_min': 60.0, 'price_max': 120.0,
            'quantity': 300,
            'status': 'open',
        },
        {
            'buyer_id': buyers[1].id,
            'title': '运动服弹力面料批量采购',
            'composition': '锦纶/氨纶',
            'weight_min': 140, 'weight_max': 180,
            'width_min': 145, 'width_max': 165,
            'craft': '针织',
            'color': '黑色',
            'price_min': 18.0, 'price_max': 30.0,
            'quantity': 3000,
            'status': 'open',
        },
        {
            'buyer_id': buyers[2].id,
            'title': '酒店床品长绒棉面料',
            'composition': '长绒棉',
            'weight_min': 130, 'weight_max': 170,
            'width_min': 250, 'width_max': 300,
            'craft': '缎纹',
            'color': '白色',
            'price_min': 35.0, 'price_max': 60.0,
            'quantity': 5000,
            'status': 'open',
        },
        {
            'buyer_id': buyers[2].id,
            'title': '工装阻燃面料采购',
            'composition': '涤棉',
            'weight_min': 200, 'weight_max': 260,
            'width_min': 145, 'width_max': 155,
            'craft': '斜纹',
            'color': '藏蓝',
            'price_min': 25.0, 'price_max': 40.0,
            'quantity': 2000,
            'status': 'open',
        },
    ]

    demands = []
    for dd in demands_data:
        d = Demand(**dd)
        db.session.add(d)
        demands.append(d)

    db.session.flush()
    return demands


def create_quotes(suppliers, demands):
    """创建示例报价"""
    # suppliers[0]=恒丰, [1]=盛泽丝绸, [2]=鲁棉, [3]=宁纺, [4]=力恒锦纶
    quotes_data = [
        # 春夏女装纯棉 ← 鲁棉、宁纺报价
        {
            'demand_id': demands[0].id,
            'supplier_id': suppliers[2].id,
            'price': 19.0,
            'delivery_days': 7,
            'message': '我司精梳纯棉府绸，120g/m²，手感柔软透气，适合春夏女装。现货充足，可随时发货。',
        },
        {
            'demand_id': demands[0].id,
            'supplier_id': suppliers[3].id,
            'price': 16.5,
            'delivery_days': 10,
            'message': '棉涤混纺衬衫面料，110g/m²，性价比高，大批量可再优惠。',
        },
        # 秋冬西装毛料 ← 恒丰报价
        {
            'demand_id': demands[1].id,
            'supplier_id': suppliers[0].id,
            'price': 115.0,
            'delivery_days': 18,
            'message': '精纺100%澳洲美利奴羊毛，260g/m²，手感细腻，适合高端西装。可提供色卡和样布。',
        },
        # 高端真丝 ← 盛泽丝绸报价
        {
            'demand_id': demands[2].id,
            'supplier_id': suppliers[1].id,
            'price': 95.0,
            'delivery_days': 14,
            'message': '19姆米真丝素绉缎，光泽度好，垂感佳。多色可选，支持定制染色。',
        },
        {
            'demand_id': demands[2].id,
            'supplier_id': suppliers[1].id,
            'price': 85.0,
            'delivery_days': 12,
            'message': '16姆米真丝双绉，质地轻盈，适合连衣裙。现有墨绿、藏蓝、酒红等色。',
        },
        # 运动弹力面料 ← 力恒锦纶报价
        {
            'demand_id': demands[3].id,
            'supplier_id': suppliers[4].id,
            'price': 24.0,
            'delivery_days': 7,
            'message': '85%锦纶/15%氨纶四面弹力面料，160g/m²，回弹性好，适合运动服。大量现货。',
        },
        # 酒店床品 ← 鲁棉报价
        {
            'demand_id': demands[4].id,
            'supplier_id': suppliers[2].id,
            'price': 46.0,
            'delivery_days': 10,
            'message': '60支长绒棉贡缎，150g/m²，幅宽280cm，适合酒店床品。5000米以上可享批量价。',
        },
        # 工装阻燃 ← 力恒锦纶报价
        {
            'demand_id': demands[5].id,
            'supplier_id': suppliers[4].id,
            'price': 34.0,
            'delivery_days': 14,
            'message': '阻燃涤棉工装面料，240g/m²，通过GB 8965阻燃标准检测，适合工业工装。',
        },
    ]

    quotes = []
    for qd in quotes_data:
        q = Quote(status='pending', **qd)
        db.session.add(q)
        quotes.append(q)

    db.session.flush()
    return quotes


def create_messages(buyers, suppliers, demands, fabrics):
    """创建示例系统消息和会话数据"""
    from server.models.message import Message
    from server.models.conversation import Conversation, ChatMessage
    from datetime import datetime, timedelta

    now = datetime.utcnow()

    # ========== 系统通知消息 ==========
    messages_data = [
        # 采购方消息
        {'user_id': buyers[0].id, 'type': 'match', 'title': '发现匹配面料',
         'content': '您的需求「春夏女装纯棉面料采购」已匹配到3个供应商面料，点击查看详情。',
         'ref_id': demands[0].id, 'ref_type': 'demand', 'is_read': False},
        {'user_id': buyers[0].id, 'type': 'quote', 'title': '收到新报价',
         'content': '绍兴柯桥恒丰纺织对您的需求「秋冬男装西装毛料采购」提交了报价 ¥115.0/米。',
         'ref_id': demands[1].id, 'ref_type': 'demand', 'is_read': False},
        {'user_id': buyers[0].id, 'type': 'system', 'title': '平台公告',
         'content': '欢迎使用纺织面料智能查询与供需对接平台！如有问题请联系客服。',
         'ref_id': None, 'ref_type': None, 'is_read': True},
        {'user_id': buyers[1].id, 'type': 'match', 'title': '发现匹配面料',
         'content': '您的需求「高端真丝连衣裙面料」已匹配到2个供应商面料，点击查看详情。',
         'ref_id': demands[2].id, 'ref_type': 'demand', 'is_read': False},
        {'user_id': buyers[1].id, 'type': 'quote', 'title': '收到新报价',
         'content': '江苏盛泽丝绸科技对您的需求「运动服弹力面料批量采购」提交了报价 ¥24.0/米。',
         'ref_id': demands[3].id, 'ref_type': 'demand', 'is_read': True},
        {'user_id': buyers[2].id, 'type': 'match', 'title': '发现匹配面料',
         'content': '您的需求「酒店床品长绒棉面料」已匹配到1个供应商面料，点击查看详情。',
         'ref_id': demands[4].id, 'ref_type': 'demand', 'is_read': False},
        # 供应商消息
        {'user_id': suppliers[0].id, 'type': 'match', 'title': '新的供需匹配',
         'content': '您的面料「精纺羊毛西装面料」与采购需求「秋冬男装西装毛料采购」匹配成功。',
         'ref_id': fabrics[7].id, 'ref_type': 'fabric', 'is_read': False},
        {'user_id': suppliers[1].id, 'type': 'match', 'title': '新的供需匹配',
         'content': '您的面料「真丝素绉缎」与采购需求「高端真丝连衣裙面料」匹配成功。',
         'ref_id': fabrics[13].id, 'ref_type': 'fabric', 'is_read': False},
        {'user_id': suppliers[2].id, 'type': 'review', 'title': '认证审核通过',
         'content': '您的企业认证已审核通过，现在可以发布面料和接收采购需求。',
         'ref_id': None, 'ref_type': None, 'is_read': True},
        {'user_id': suppliers[4].id, 'type': 'match', 'title': '新的供需匹配',
         'content': '您的面料「锦纶四面弹力面料」与采购需求「运动服弹力面料批量采购」匹配成功。',
         'ref_id': fabrics[18].id, 'ref_type': 'fabric', 'is_read': False},
    ]

    msgs = []
    for i, md in enumerate(messages_data):
        m = Message(created_at=now - timedelta(hours=i*2), **md)
        db.session.add(m)
        msgs.append(m)

    db.session.flush()

    # ========== 会话和聊天消息 ==========
    convs_data = [
        # 采购方0 与 供应商0 关于需求1（西装毛料）
        {
            'demand_id': demands[1].id,
            'buyer_id': buyers[0].id,
            'supplier_id': suppliers[0].id,
            'chats': [
                {'sender_id': buyers[0].id, 'content': '您好，我们需要采购精纺羊毛西装面料，请问贵司有现货吗？'},
                {'sender_id': suppliers[0].id, 'content': '您好！我司有100%澳洲美利奴羊毛西装面料现货，260g/m²，幅宽150cm，可提供样布。'},
                {'sender_id': buyers[0].id, 'content': '请问最小起订量是多少？能否提供色卡？'},
                {'sender_id': suppliers[0].id, 'content': '最小起订量100米，有深灰、藏蓝、黑色等多色色卡，可免费寄送样布。'},
                {'sender_id': buyers[0].id, 'content': '好的，请寄送样布到我司，地址稍后发您。'},
            ]
        },
        # 采购方1 与 供应商1 关于需求2（真丝）
        {
            'demand_id': demands[2].id,
            'buyer_id': buyers[1].id,
            'supplier_id': suppliers[1].id,
            'chats': [
                {'sender_id': buyers[1].id, 'content': '您好，看到贵司有真丝素绉缎，请问19姆米的有哪些颜色？'},
                {'sender_id': suppliers[1].id, 'content': '您好！19姆米真丝素绉缎目前有香槟色、米白、藏蓝、酒红、墨绿等10余种颜色，支持定制染色。'},
                {'sender_id': buyers[1].id, 'content': '定制染色最小量是多少？交期多久？'},
                {'sender_id': suppliers[1].id, 'content': '定制染色最小量200米，交期约20天。现货颜色100米起订，7天内发货。'},
            ]
        },
        # 采购方2 与 供应商4 关于需求5（工装阻燃）
        {
            'demand_id': demands[5].id,
            'buyer_id': buyers[2].id,
            'supplier_id': suppliers[4].id,
            'chats': [
                {'sender_id': buyers[2].id, 'content': '您好，我们需要采购阻燃工装面料，请问贵司产品通过哪些认证？'},
                {'sender_id': suppliers[4].id, 'content': '您好！我司阻燃涤棉工装面料通过GB 8965.1-2009阻燃防护服标准，可提供检测报告。'},
                {'sender_id': buyers[2].id, 'content': '需要2000米，藏蓝色，请报含税价。'},
                {'sender_id': suppliers[4].id, 'content': '2000米含税价34元/米，可开增值税专用发票，交期15天。'},
                {'sender_id': buyers[2].id, 'content': '价格合适，请发合同模板给我们确认。'},
                {'sender_id': suppliers[4].id, 'content': '好的，合同模板已通过邮件发送，请查收。期待合作！'},
            ]
        },
    ]

    convs = []
    for cd in convs_data:
        chats = cd.pop('chats')
        conv = Conversation(**cd)
        db.session.add(conv)
        db.session.flush()

        for j, chat in enumerate(chats):
            cm = ChatMessage(
                conversation_id=conv.id,
                content=chat['content'],
                sender_id=chat['sender_id'],
                msg_type='text',
                is_read=True,
                created_at=now - timedelta(hours=len(chats)-j)
            )
            db.session.add(cm)

        # 更新会话最后消息
        conv.last_message_at = now - timedelta(minutes=len(chats))
        conv.last_message_preview = chats[-1]['content'][:50]
        convs.append(conv)

    db.session.flush()
    return msgs, convs


def create_samples(buyers, suppliers, fabrics):
    """创建样品申请测试数据."""
    from server.models.sample import Sample

    data = [
        # buyer[0] 向 supplier[0] 申请面料1的样品，已批准发货
        dict(fabric_id=fabrics[0].id, buyer_id=buyers[0].id, supplier_id=suppliers[0].id,
             quantity=2, address='广东省广州市天河区某某路1号', status='shipping',
             logistics_no='SF1234567890'),
        # buyer[0] 向 supplier[1] 申请面料6的样品，待审核
        dict(fabric_id=fabrics[5].id, buyer_id=buyers[0].id, supplier_id=suppliers[1].id,
             quantity=1, address='广东省广州市天河区某某路1号', status='pending'),
        # buyer[1] 向 supplier[0] 申请面料2的样品，已收到
        dict(fabric_id=fabrics[1].id, buyer_id=buyers[1].id, supplier_id=suppliers[0].id,
             quantity=3, address='上海市浦东新区某某路88号', status='received'),
        # buyer[1] 向 supplier[2] 申请面料10的样品，已拒绝
        dict(fabric_id=fabrics[9].id, buyer_id=buyers[1].id, supplier_id=suppliers[2].id,
             quantity=2, address='上海市浦东新区某某路88号', status='rejected',
             reject_reason='该面料暂无库存，无法提供样品'),
        # buyer[2] 向 supplier[3] 申请面料15的样品，已批准
        dict(fabric_id=fabrics[14].id, buyer_id=buyers[2].id, supplier_id=suppliers[3].id,
             quantity=5, address='浙江省杭州市西湖区某某路99号', status='approved'),
    ]

    samples = []
    for d in data:
        s = Sample(**d)
        db.session.add(s)
        samples.append(s)

    db.session.flush()
    return samples


def create_orders(buyers, suppliers, fabrics):
    """创建订单测试数据."""
    from server.models.order import Order, OrderItem, generate_order_no

    order_data = [
        # buyer[0] 向 supplier[0] 下单，已确认生产中
        dict(buyer_id=buyers[0].id, supplier_id=suppliers[0].id,
             total_amount=15800.0, address='广东省广州市天河区某某路1号',
             status='producing',
             items=[(fabrics[0].id, 500, 18.8), (fabrics[1].id, 300, 25.6)]),
        # buyer[0] 向 supplier[1] 下单，已发货
        dict(buyer_id=buyers[0].id, supplier_id=suppliers[1].id,
             total_amount=8400.0, address='广东省广州市天河区某某路1号',
             status='shipped', tracking_no='YTO9876543210',
             items=[(fabrics[5].id, 200, 42.0)]),
        # buyer[1] 向 supplier[0] 下单，已完成
        dict(buyer_id=buyers[1].id, supplier_id=suppliers[0].id,
             total_amount=6600.0, address='上海市浦东新区某某路88号',
             status='completed',
             items=[(fabrics[2].id, 400, 16.5)]),
        # buyer[1] 向 supplier[2] 下单，待确认
        dict(buyer_id=buyers[1].id, supplier_id=suppliers[2].id,
             total_amount=12000.0, address='上海市浦东新区某某路88号',
             status='pending',
             items=[(fabrics[9].id, 600, 20.0)]),
        # buyer[2] 向 supplier[3] 下单，已收货
        dict(buyer_id=buyers[2].id, supplier_id=suppliers[3].id,
             total_amount=9750.0, address='浙江省杭州市西湖区某某路99号',
             status='received',
             items=[(fabrics[14].id, 300, 32.5)]),
    ]

    orders = []
    for d in order_data:
        items = d.pop('items')
        tracking_no = d.pop('tracking_no', None)
        order = Order(order_no=generate_order_no(), tracking_no=tracking_no, **d)
        db.session.add(order)
        db.session.flush()
        for fabric_id, qty, unit_price in items:
            item = OrderItem(
                order_id=order.id,
                fabric_id=fabric_id,
                quantity=qty,
                unit_price=unit_price,
                subtotal=round(qty * unit_price, 2),
            )
            db.session.add(item)
        orders.append(order)

    db.session.flush()
    return orders


# ============================================================
# 主执行入口
# ============================================================
if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        # 清空旧数据并重建表
        db.drop_all()
        db.create_all()

        # 创建数据
        users = create_users()
        admin = users[0]
        buyers = users[1:4]       # 3 个采购方
        suppliers = users[4:9]    # 5 个供应商

        fabrics = create_fabrics(suppliers)
        demands = create_demands(buyers)
        quotes = create_quotes(suppliers, demands)
        messages, convs = create_messages(buyers, suppliers, demands, fabrics)
        samples = create_samples(buyers, suppliers, fabrics)
        orders = create_orders(buyers, suppliers, fabrics)

        db.session.commit()

        print('=' * 50)
        print('开发数据初始化完成！')
        print(f'  用户: {len(users)} 个 (1管理员 + 3采购方 + 5供应商)')
        print(f'  面料: {len(fabrics)} 条')
        print(f'  需求: {len(demands)} 条')
        print(f'  报价: {len(quotes)} 条')
        print(f'  消息: {len(messages)} 条')
        print(f'  会话: {len(convs)} 个')
        print(f'  样品: {len(samples)} 条')
        print(f'  订单: {len(orders)} 条')
        print('=' * 50)
        print()
        print('登录账号:')
        print('  管理员  13800000001 / admin123')
        print('  采购方  13800000010 / buyer123')
        print('  供应商  13800000020 / supplier123')
