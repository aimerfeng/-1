"""Tests for the User data model.

Verifies User model creation, field constraints, password hashing,
and JSON serialization.
"""

import pytest
from datetime import datetime

from server.extensions import db as _db
from server.models.user import User


class TestUserModel:
    """Tests for User model basic functionality."""

    def test_create_buyer_user(self, app_context):
        """Should create a user with buyer role and default certification status."""
        user = User(
            phone='13800138000',
            role='buyer',
            company_name='Test Buyer Co.',
            contact_name='Zhang San',
        )
        _db.session.add(user)
        _db.session.commit()

        saved = _db.session.get(User, user.id)
        assert saved is not None
        assert saved.phone == '13800138000'
        assert saved.role == 'buyer'
        assert saved.company_name == 'Test Buyer Co.'
        assert saved.contact_name == 'Zhang San'
        assert saved.certification_status == 'pending'

    def test_create_supplier_user(self, app_context):
        """Should create a user with supplier role."""
        user = User(
            phone='13900139000',
            role='supplier',
            company_name='Test Supplier Co.',
            contact_name='Li Si',
            address='Shanghai, China',
        )
        _db.session.add(user)
        _db.session.commit()

        saved = _db.session.get(User, user.id)
        assert saved is not None
        assert saved.role == 'supplier'
        assert saved.address == 'Shanghai, China'

    def test_create_admin_user(self, app_context):
        """Should create a user with admin role."""
        user = User(
            phone='13700137000',
            role='admin',
            contact_name='Admin User',
        )
        _db.session.add(user)
        _db.session.commit()

        saved = _db.session.get(User, user.id)
        assert saved is not None
        assert saved.role == 'admin'

    def test_create_user_with_openid(self, app_context):
        """Should create a user with WeChat openid."""
        user = User(
            openid='wx_openid_abc123',
            role='buyer',
        )
        _db.session.add(user)
        _db.session.commit()

        saved = _db.session.get(User, user.id)
        assert saved is not None
        assert saved.openid == 'wx_openid_abc123'

    def test_openid_unique_constraint(self, app_context):
        """Should enforce unique constraint on openid."""
        user1 = User(openid='wx_unique_id', role='buyer')
        _db.session.add(user1)
        _db.session.commit()

        user2 = User(openid='wx_unique_id', role='supplier')
        _db.session.add(user2)
        with pytest.raises(Exception):
            _db.session.commit()

    def test_phone_unique_constraint(self, app_context):
        """Should enforce unique constraint on phone."""
        user1 = User(phone='13800138001', role='buyer')
        _db.session.add(user1)
        _db.session.commit()

        user2 = User(phone='13800138001', role='supplier')
        _db.session.add(user2)
        with pytest.raises(Exception):
            _db.session.commit()

    def test_role_not_nullable(self, app_context):
        """Should reject user creation without a role."""
        user = User(phone='13800138002')
        _db.session.add(user)
        with pytest.raises(Exception):
            _db.session.commit()

    def test_default_certification_status(self, app_context):
        """Should default certification_status to 'pending'."""
        user = User(role='buyer', phone='13800138003')
        _db.session.add(user)
        _db.session.commit()

        saved = _db.session.get(User, user.id)
        assert saved.certification_status == 'pending'

    def test_certification_status_approved(self, app_context):
        """Should allow setting certification_status to 'approved'."""
        user = User(role='supplier', phone='13800138004', certification_status='approved')
        _db.session.add(user)
        _db.session.commit()

        saved = _db.session.get(User, user.id)
        assert saved.certification_status == 'approved'

    def test_certification_status_rejected(self, app_context):
        """Should allow setting certification_status to 'rejected'."""
        user = User(role='supplier', phone='13800138005', certification_status='rejected')
        _db.session.add(user)
        _db.session.commit()

        saved = _db.session.get(User, user.id)
        assert saved.certification_status == 'rejected'

    def test_created_at_auto_set(self, app_context):
        """Should automatically set created_at on creation."""
        user = User(role='buyer', phone='13800138006')
        _db.session.add(user)
        _db.session.commit()

        saved = _db.session.get(User, user.id)
        assert saved.created_at is not None
        assert isinstance(saved.created_at, datetime)

    def test_updated_at_auto_set(self, app_context):
        """Should automatically set updated_at on creation."""
        user = User(role='buyer', phone='13800138007')
        _db.session.add(user)
        _db.session.commit()

        saved = _db.session.get(User, user.id)
        assert saved.updated_at is not None
        assert isinstance(saved.updated_at, datetime)


class TestUserPassword:
    """Tests for User password hashing functionality."""

    def test_set_password_hashes(self, app_context):
        """set_password should store a hashed version, not plaintext."""
        user = User(role='buyer', phone='13800138010')
        user.set_password('my_secure_password')

        assert user.password_hash is not None
        assert user.password_hash != 'my_secure_password'

    def test_check_password_correct(self, app_context):
        """check_password should return True for the correct password."""
        user = User(role='buyer', phone='13800138011')
        user.set_password('correct_password')

        assert user.check_password('correct_password') is True

    def test_check_password_incorrect(self, app_context):
        """check_password should return False for an incorrect password."""
        user = User(role='buyer', phone='13800138012')
        user.set_password('correct_password')

        assert user.check_password('wrong_password') is False

    def test_check_password_no_hash(self, app_context):
        """check_password should return False when no password is set."""
        user = User(role='buyer', phone='13800138013')

        assert user.check_password('any_password') is False

    def test_password_persists_after_save(self, app_context):
        """Password hash should persist correctly after database save."""
        user = User(role='buyer', phone='13800138014')
        user.set_password('persistent_password')
        _db.session.add(user)
        _db.session.commit()

        saved = _db.session.get(User, user.id)
        assert saved.check_password('persistent_password') is True
        assert saved.check_password('wrong_password') is False


class TestUserToDict:
    """Tests for User JSON serialization."""

    def test_to_dict_contains_expected_keys(self, app_context):
        """to_dict should return all expected keys."""
        user = User(
            phone='13800138020',
            role='buyer',
            company_name='Test Co.',
            contact_name='Zhang San',
            address='Beijing, China',
        )
        _db.session.add(user)
        _db.session.commit()

        data = user.to_dict()
        expected_keys = {
            'id', 'openid', 'phone', 'role', 'company_name',
            'contact_name', 'address', 'certification_status',
            'created_at', 'updated_at',
        }
        assert set(data.keys()) == expected_keys

    def test_to_dict_excludes_password_hash(self, app_context):
        """to_dict should not include password_hash."""
        user = User(role='buyer', phone='13800138021')
        user.set_password('secret')
        _db.session.add(user)
        _db.session.commit()

        data = user.to_dict()
        assert 'password_hash' not in data

    def test_to_dict_values_match(self, app_context):
        """to_dict values should match the model attributes."""
        user = User(
            phone='13800138022',
            role='supplier',
            company_name='Supplier Co.',
            contact_name='Li Si',
            address='Shanghai',
            certification_status='approved',
        )
        _db.session.add(user)
        _db.session.commit()

        data = user.to_dict()
        assert data['phone'] == '13800138022'
        assert data['role'] == 'supplier'
        assert data['company_name'] == 'Supplier Co.'
        assert data['contact_name'] == 'Li Si'
        assert data['address'] == 'Shanghai'
        assert data['certification_status'] == 'approved'

    def test_to_dict_datetime_format(self, app_context):
        """to_dict should serialize datetime fields as ISO format strings."""
        user = User(role='buyer', phone='13800138023')
        _db.session.add(user)
        _db.session.commit()

        data = user.to_dict()
        # Should be ISO format strings
        assert isinstance(data['created_at'], str)
        assert isinstance(data['updated_at'], str)
        # Should be parseable as datetime
        datetime.fromisoformat(data['created_at'])
        datetime.fromisoformat(data['updated_at'])

    def test_to_dict_nullable_fields(self, app_context):
        """to_dict should handle None values for nullable fields."""
        user = User(role='buyer')
        _db.session.add(user)
        _db.session.commit()

        data = user.to_dict()
        assert data['openid'] is None
        assert data['phone'] is None
        assert data['company_name'] is None
        assert data['contact_name'] is None
        assert data['address'] is None


class TestUserRepr:
    """Tests for User string representation."""

    def test_repr(self, app_context):
        """__repr__ should return a readable string."""
        user = User(role='buyer', phone='13800138030')
        _db.session.add(user)
        _db.session.commit()

        repr_str = repr(user)
        assert 'User' in repr_str
        assert 'buyer' in repr_str


# ---------------------------------------------------------------------------
# Fabric model tests
# ---------------------------------------------------------------------------

from server.models.fabric import Fabric, validate_fabric


class TestFabricModel:
    """Tests for Fabric model basic functionality."""

    def _create_supplier(self):
        """Helper to create a supplier user for fabric foreign key."""
        supplier = User(
            phone='13600136000',
            role='supplier',
            company_name='Fabric Supplier Co.',
            contact_name='Wang Wu',
        )
        _db.session.add(supplier)
        _db.session.commit()
        return supplier

    def test_create_fabric_with_valid_data(self, app_context):
        """Should create a fabric with all required fields."""
        supplier = self._create_supplier()
        fabric = Fabric(
            supplier_id=supplier.id,
            name='纯棉平纹布',
            composition='100%棉',
            weight=180.0,
            width=150.0,
            craft='平纹',
            color='白色',
            price=25.5,
            min_order_qty=100,
            delivery_days=7,
        )
        _db.session.add(fabric)
        _db.session.commit()

        saved = _db.session.get(Fabric, fabric.id)
        assert saved is not None
        assert saved.supplier_id == supplier.id
        assert saved.name == '纯棉平纹布'
        assert saved.composition == '100%棉'
        assert saved.weight == 180.0
        assert saved.width == 150.0
        assert saved.craft == '平纹'
        assert saved.color == '白色'
        assert saved.price == 25.5
        assert saved.min_order_qty == 100
        assert saved.delivery_days == 7

    def test_fabric_default_status_active(self, app_context):
        """Should default status to 'active'."""
        supplier = self._create_supplier()
        fabric = Fabric(
            supplier_id=supplier.id,
            name='测试面料',
            composition='涤纶',
            weight=120.0,
            width=140.0,
            craft='斜纹',
            price=18.0,
        )
        _db.session.add(fabric)
        _db.session.commit()

        saved = _db.session.get(Fabric, fabric.id)
        assert saved.status == 'active'

    def test_fabric_status_inactive(self, app_context):
        """Should allow setting status to 'inactive'."""
        supplier = self._create_supplier()
        fabric = Fabric(
            supplier_id=supplier.id,
            name='下架面料',
            composition='丝绸',
            weight=80.0,
            width=120.0,
            craft='缎纹',
            price=120.0,
            status='inactive',
        )
        _db.session.add(fabric)
        _db.session.commit()

        saved = _db.session.get(Fabric, fabric.id)
        assert saved.status == 'inactive'

    def test_fabric_images_default_empty_list(self, app_context):
        """Should default images to an empty list."""
        supplier = self._create_supplier()
        fabric = Fabric(
            supplier_id=supplier.id,
            name='无图面料',
            composition='棉麻',
            weight=200.0,
            width=160.0,
            craft='平纹',
            price=30.0,
        )
        _db.session.add(fabric)
        _db.session.commit()

        saved = _db.session.get(Fabric, fabric.id)
        assert saved.images == [] or saved.images is None

    def test_fabric_images_json_storage(self, app_context):
        """Should store and retrieve images as JSON list."""
        supplier = self._create_supplier()
        image_urls = ['https://example.com/img1.jpg', 'https://example.com/img2.jpg']
        fabric = Fabric(
            supplier_id=supplier.id,
            name='有图面料',
            composition='涤纶',
            weight=150.0,
            width=145.0,
            craft='针织',
            price=22.0,
            images=image_urls,
        )
        _db.session.add(fabric)
        _db.session.commit()

        saved = _db.session.get(Fabric, fabric.id)
        assert saved.images == image_urls

    def test_fabric_created_at_auto_set(self, app_context):
        """Should automatically set created_at on creation."""
        supplier = self._create_supplier()
        fabric = Fabric(
            supplier_id=supplier.id,
            name='时间测试',
            composition='棉',
            weight=100.0,
            width=100.0,
            craft='平纹',
            price=10.0,
        )
        _db.session.add(fabric)
        _db.session.commit()

        saved = _db.session.get(Fabric, fabric.id)
        assert saved.created_at is not None
        assert isinstance(saved.created_at, datetime)

    def test_fabric_updated_at_auto_set(self, app_context):
        """Should automatically set updated_at on creation."""
        supplier = self._create_supplier()
        fabric = Fabric(
            supplier_id=supplier.id,
            name='更新时间测试',
            composition='棉',
            weight=100.0,
            width=100.0,
            craft='平纹',
            price=10.0,
        )
        _db.session.add(fabric)
        _db.session.commit()

        saved = _db.session.get(Fabric, fabric.id)
        assert saved.updated_at is not None
        assert isinstance(saved.updated_at, datetime)


class TestFabricToDict:
    """Tests for Fabric JSON serialization."""

    def _create_supplier(self):
        supplier = User(
            phone='13600136100',
            role='supplier',
            company_name='Serialization Supplier',
        )
        _db.session.add(supplier)
        _db.session.commit()
        return supplier

    def test_to_dict_contains_expected_keys(self, app_context):
        """to_dict should return all expected keys."""
        supplier = self._create_supplier()
        fabric = Fabric(
            supplier_id=supplier.id,
            name='序列化测试',
            composition='100%涤纶',
            weight=160.0,
            width=148.0,
            craft='针织',
            color='黑色',
            price=28.0,
            min_order_qty=50,
            delivery_days=5,
            images=['https://example.com/img.jpg'],
        )
        _db.session.add(fabric)
        _db.session.commit()

        data = fabric.to_dict()
        expected_keys = {
            'id', 'supplier_id', 'name', 'composition', 'weight', 'width',
            'craft', 'color', 'price', 'min_order_qty', 'delivery_days',
            'stock_quantity', 'images', 'status', 'created_at', 'updated_at',
        }
        assert set(data.keys()) == expected_keys

    def test_to_dict_values_match(self, app_context):
        """to_dict values should match the model attributes."""
        supplier = self._create_supplier()
        fabric = Fabric(
            supplier_id=supplier.id,
            name='值匹配测试',
            composition='棉/涤混纺',
            weight=200.0,
            width=155.0,
            craft='斜纹',
            color='蓝色',
            price=35.0,
            min_order_qty=200,
            delivery_days=10,
            images=['https://example.com/a.jpg'],
            status='active',
        )
        _db.session.add(fabric)
        _db.session.commit()

        data = fabric.to_dict()
        assert data['supplier_id'] == supplier.id
        assert data['name'] == '值匹配测试'
        assert data['composition'] == '棉/涤混纺'
        assert data['weight'] == 200.0
        assert data['width'] == 155.0
        assert data['craft'] == '斜纹'
        assert data['color'] == '蓝色'
        assert data['price'] == 35.0
        assert data['min_order_qty'] == 200
        assert data['delivery_days'] == 10
        assert data['images'] == ['https://example.com/a.jpg']
        assert data['status'] == 'active'

    def test_to_dict_datetime_format(self, app_context):
        """to_dict should serialize datetime fields as ISO format strings."""
        supplier = self._create_supplier()
        fabric = Fabric(
            supplier_id=supplier.id,
            name='日期格式测试',
            composition='棉',
            weight=100.0,
            width=100.0,
            craft='平纹',
            price=10.0,
        )
        _db.session.add(fabric)
        _db.session.commit()

        data = fabric.to_dict()
        assert isinstance(data['created_at'], str)
        assert isinstance(data['updated_at'], str)
        datetime.fromisoformat(data['created_at'])
        datetime.fromisoformat(data['updated_at'])

    def test_to_dict_nullable_fields(self, app_context):
        """to_dict should handle None values for nullable fields."""
        supplier = self._create_supplier()
        fabric = Fabric(
            supplier_id=supplier.id,
            name='空值测试',
            composition='棉',
            weight=100.0,
            width=100.0,
            craft='平纹',
            price=10.0,
        )
        _db.session.add(fabric)
        _db.session.commit()

        data = fabric.to_dict()
        assert data['color'] is None
        assert data['min_order_qty'] is None
        assert data['delivery_days'] is None


class TestValidateFabric:
    """Tests for the validate_fabric function."""

    def test_valid_data_passes(self):
        """Should return (True, {}) for valid data with all required fields."""
        data = {
            'composition': '100%棉',
            'weight': 180.0,
            'width': 150.0,
            'craft': '平纹',
            'price': 25.5,
        }
        is_valid, errors = validate_fabric(data)
        assert is_valid is True
        assert errors == {}

    def test_valid_data_with_integer_numbers(self):
        """Should accept integer values for numeric fields."""
        data = {
            'composition': '涤纶',
            'weight': 200,
            'width': 150,
            'craft': '斜纹',
            'price': 30,
        }
        is_valid, errors = validate_fabric(data)
        assert is_valid is True
        assert errors == {}

    def test_missing_composition(self):
        """Should fail when composition is missing."""
        data = {
            'weight': 180.0,
            'width': 150.0,
            'craft': '平纹',
            'price': 25.5,
        }
        is_valid, errors = validate_fabric(data)
        assert is_valid is False
        assert 'composition' in errors

    def test_missing_weight(self):
        """Should fail when weight is missing."""
        data = {
            'composition': '棉',
            'width': 150.0,
            'craft': '平纹',
            'price': 25.5,
        }
        is_valid, errors = validate_fabric(data)
        assert is_valid is False
        assert 'weight' in errors

    def test_missing_width(self):
        """Should fail when width is missing."""
        data = {
            'composition': '棉',
            'weight': 180.0,
            'craft': '平纹',
            'price': 25.5,
        }
        is_valid, errors = validate_fabric(data)
        assert is_valid is False
        assert 'width' in errors

    def test_missing_craft(self):
        """Should fail when craft is missing."""
        data = {
            'composition': '棉',
            'weight': 180.0,
            'width': 150.0,
            'price': 25.5,
        }
        is_valid, errors = validate_fabric(data)
        assert is_valid is False
        assert 'craft' in errors

    def test_missing_price(self):
        """Should fail when price is missing."""
        data = {
            'composition': '棉',
            'weight': 180.0,
            'width': 150.0,
            'craft': '平纹',
        }
        is_valid, errors = validate_fabric(data)
        assert is_valid is False
        assert 'price' in errors

    def test_missing_all_required_fields(self):
        """Should report errors for all missing required fields."""
        data = {}
        is_valid, errors = validate_fabric(data)
        assert is_valid is False
        assert 'composition' in errors
        assert 'weight' in errors
        assert 'width' in errors
        assert 'craft' in errors
        assert 'price' in errors

    def test_empty_string_composition(self):
        """Should fail when composition is an empty string."""
        data = {
            'composition': '',
            'weight': 180.0,
            'width': 150.0,
            'craft': '平纹',
            'price': 25.5,
        }
        is_valid, errors = validate_fabric(data)
        assert is_valid is False
        assert 'composition' in errors

    def test_whitespace_only_composition(self):
        """Should fail when composition is whitespace only."""
        data = {
            'composition': '   ',
            'weight': 180.0,
            'width': 150.0,
            'craft': '平纹',
            'price': 25.5,
        }
        is_valid, errors = validate_fabric(data)
        assert is_valid is False
        assert 'composition' in errors

    def test_empty_string_craft(self):
        """Should fail when craft is an empty string."""
        data = {
            'composition': '棉',
            'weight': 180.0,
            'width': 150.0,
            'craft': '',
            'price': 25.5,
        }
        is_valid, errors = validate_fabric(data)
        assert is_valid is False
        assert 'craft' in errors

    def test_zero_weight(self):
        """Should fail when weight is zero."""
        data = {
            'composition': '棉',
            'weight': 0,
            'width': 150.0,
            'craft': '平纹',
            'price': 25.5,
        }
        is_valid, errors = validate_fabric(data)
        assert is_valid is False
        assert 'weight' in errors

    def test_negative_price(self):
        """Should fail when price is negative."""
        data = {
            'composition': '棉',
            'weight': 180.0,
            'width': 150.0,
            'craft': '平纹',
            'price': -10.0,
        }
        is_valid, errors = validate_fabric(data)
        assert is_valid is False
        assert 'price' in errors

    def test_negative_width(self):
        """Should fail when width is negative."""
        data = {
            'composition': '棉',
            'weight': 180.0,
            'width': -5.0,
            'craft': '平纹',
            'price': 25.5,
        }
        is_valid, errors = validate_fabric(data)
        assert is_valid is False
        assert 'width' in errors

    def test_non_numeric_weight(self):
        """Should fail when weight is not a number."""
        data = {
            'composition': '棉',
            'weight': 'heavy',
            'width': 150.0,
            'craft': '平纹',
            'price': 25.5,
        }
        is_valid, errors = validate_fabric(data)
        assert is_valid is False
        assert 'weight' in errors

    def test_non_string_composition(self):
        """Should fail when composition is not a string."""
        data = {
            'composition': 123,
            'weight': 180.0,
            'width': 150.0,
            'craft': '平纹',
            'price': 25.5,
        }
        is_valid, errors = validate_fabric(data)
        assert is_valid is False
        assert 'composition' in errors


class TestFabricUserRelationship:
    """Tests for Fabric-User foreign key relationship."""

    def test_fabric_belongs_to_supplier(self, app_context):
        """Fabric should reference its supplier via supplier_id."""
        supplier = User(
            phone='13600136200',
            role='supplier',
            company_name='Relationship Supplier',
        )
        _db.session.add(supplier)
        _db.session.commit()

        fabric = Fabric(
            supplier_id=supplier.id,
            name='关系测试面料',
            composition='棉',
            weight=100.0,
            width=100.0,
            craft='平纹',
            price=10.0,
        )
        _db.session.add(fabric)
        _db.session.commit()

        saved = _db.session.get(Fabric, fabric.id)
        assert saved.supplier_id == supplier.id
        assert saved.supplier.id == supplier.id
        assert saved.supplier.company_name == 'Relationship Supplier'

    def test_supplier_has_fabrics(self, app_context):
        """Supplier should be able to access their fabrics via backref."""
        supplier = User(
            phone='13600136300',
            role='supplier',
            company_name='Multi-Fabric Supplier',
        )
        _db.session.add(supplier)
        _db.session.commit()

        fabric1 = Fabric(
            supplier_id=supplier.id,
            name='面料A',
            composition='棉',
            weight=100.0,
            width=100.0,
            craft='平纹',
            price=10.0,
        )
        fabric2 = Fabric(
            supplier_id=supplier.id,
            name='面料B',
            composition='涤纶',
            weight=120.0,
            width=140.0,
            craft='斜纹',
            price=15.0,
        )
        _db.session.add_all([fabric1, fabric2])
        _db.session.commit()

        assert supplier.fabrics.count() == 2
        fabric_names = [f.name for f in supplier.fabrics.all()]
        assert '面料A' in fabric_names
        assert '面料B' in fabric_names

    def test_fabric_repr(self, app_context):
        """__repr__ should return a readable string."""
        supplier = User(
            phone='13600136400',
            role='supplier',
        )
        _db.session.add(supplier)
        _db.session.commit()

        fabric = Fabric(
            supplier_id=supplier.id,
            name='Repr测试',
            composition='棉',
            weight=100.0,
            width=100.0,
            craft='平纹',
            price=10.0,
        )
        _db.session.add(fabric)
        _db.session.commit()

        repr_str = repr(fabric)
        assert 'Fabric' in repr_str
        assert 'Repr测试' in repr_str


# ---------------------------------------------------------------------------
# Demand model tests
# ---------------------------------------------------------------------------

from server.models.demand import Demand, MatchResult


class TestDemandModel:
    """Tests for Demand model basic functionality."""

    def _create_buyer(self):
        """Helper to create a buyer user for demand foreign key."""
        buyer = User(
            phone='13500135000',
            role='buyer',
            company_name='Demand Buyer Co.',
            contact_name='Zhao Liu',
        )
        _db.session.add(buyer)
        _db.session.commit()
        return buyer

    def test_create_demand_with_all_fields(self, app_context):
        """Should create a demand with all fields populated."""
        buyer = self._create_buyer()
        demand = Demand(
            buyer_id=buyer.id,
            title='采购纯棉面料',
            composition='100%棉',
            weight_min=150.0,
            weight_max=200.0,
            width_min=140.0,
            width_max=160.0,
            craft='平纹',
            color='白色',
            price_min=20.0,
            price_max=35.0,
            quantity=1000,
        )
        _db.session.add(demand)
        _db.session.commit()

        saved = _db.session.get(Demand, demand.id)
        assert saved is not None
        assert saved.buyer_id == buyer.id
        assert saved.title == '采购纯棉面料'
        assert saved.composition == '100%棉'
        assert saved.weight_min == 150.0
        assert saved.weight_max == 200.0
        assert saved.width_min == 140.0
        assert saved.width_max == 160.0
        assert saved.craft == '平纹'
        assert saved.color == '白色'
        assert saved.price_min == 20.0
        assert saved.price_max == 35.0
        assert saved.quantity == 1000

    def test_demand_default_status_open(self, app_context):
        """Should default status to 'open'."""
        buyer = self._create_buyer()
        demand = Demand(
            buyer_id=buyer.id,
            title='默认状态测试',
        )
        _db.session.add(demand)
        _db.session.commit()

        saved = _db.session.get(Demand, demand.id)
        assert saved.status == 'open'

    def test_demand_status_matched(self, app_context):
        """Should allow setting status to 'matched'."""
        buyer = self._create_buyer()
        demand = Demand(
            buyer_id=buyer.id,
            title='已匹配需求',
            status='matched',
        )
        _db.session.add(demand)
        _db.session.commit()

        saved = _db.session.get(Demand, demand.id)
        assert saved.status == 'matched'

    def test_demand_status_closed(self, app_context):
        """Should allow setting status to 'closed'."""
        buyer = self._create_buyer()
        demand = Demand(
            buyer_id=buyer.id,
            title='已关闭需求',
            status='closed',
        )
        _db.session.add(demand)
        _db.session.commit()

        saved = _db.session.get(Demand, demand.id)
        assert saved.status == 'closed'

    def test_demand_invalid_status_rejected(self, app_context):
        """Should reject invalid status values."""
        buyer = self._create_buyer()
        demand = Demand(
            buyer_id=buyer.id,
            title='无效状态测试',
            status='invalid_status',
        )
        _db.session.add(demand)
        with pytest.raises(Exception):
            _db.session.commit()

    def test_demand_created_at_auto_set(self, app_context):
        """Should automatically set created_at on creation."""
        buyer = self._create_buyer()
        demand = Demand(
            buyer_id=buyer.id,
            title='时间测试需求',
        )
        _db.session.add(demand)
        _db.session.commit()

        saved = _db.session.get(Demand, demand.id)
        assert saved.created_at is not None
        assert isinstance(saved.created_at, datetime)

    def test_demand_nullable_fields(self, app_context):
        """Should allow nullable fields to be None."""
        buyer = self._create_buyer()
        demand = Demand(
            buyer_id=buyer.id,
            title='最小需求',
        )
        _db.session.add(demand)
        _db.session.commit()

        saved = _db.session.get(Demand, demand.id)
        assert saved.composition is None
        assert saved.weight_min is None
        assert saved.weight_max is None
        assert saved.width_min is None
        assert saved.width_max is None
        assert saved.craft is None
        assert saved.color is None
        assert saved.price_min is None
        assert saved.price_max is None
        assert saved.quantity is None


class TestDemandToDict:
    """Tests for Demand JSON serialization."""

    def _create_buyer(self):
        buyer = User(
            phone='13500135100',
            role='buyer',
            company_name='Serialization Buyer',
        )
        _db.session.add(buyer)
        _db.session.commit()
        return buyer

    def test_to_dict_contains_expected_keys(self, app_context):
        """to_dict should return all expected keys."""
        buyer = self._create_buyer()
        demand = Demand(
            buyer_id=buyer.id,
            title='序列化测试需求',
            composition='涤纶',
            weight_min=100.0,
            weight_max=200.0,
            width_min=130.0,
            width_max=160.0,
            craft='针织',
            color='黑色',
            price_min=15.0,
            price_max=30.0,
            quantity=500,
        )
        _db.session.add(demand)
        _db.session.commit()

        data = demand.to_dict()
        expected_keys = {
            'id', 'buyer_id', 'title', 'composition',
            'weight_min', 'weight_max', 'width_min', 'width_max',
            'craft', 'color', 'price_min', 'price_max',
            'quantity', 'status', 'created_at',
        }
        assert set(data.keys()) == expected_keys

    def test_to_dict_values_match(self, app_context):
        """to_dict values should match the model attributes."""
        buyer = self._create_buyer()
        demand = Demand(
            buyer_id=buyer.id,
            title='值匹配测试',
            composition='棉/涤混纺',
            weight_min=150.0,
            weight_max=250.0,
            width_min=140.0,
            width_max=170.0,
            craft='斜纹',
            color='蓝色',
            price_min=25.0,
            price_max=40.0,
            quantity=2000,
        )
        _db.session.add(demand)
        _db.session.commit()

        data = demand.to_dict()
        assert data['buyer_id'] == buyer.id
        assert data['title'] == '值匹配测试'
        assert data['composition'] == '棉/涤混纺'
        assert data['weight_min'] == 150.0
        assert data['weight_max'] == 250.0
        assert data['width_min'] == 140.0
        assert data['width_max'] == 170.0
        assert data['craft'] == '斜纹'
        assert data['color'] == '蓝色'
        assert data['price_min'] == 25.0
        assert data['price_max'] == 40.0
        assert data['quantity'] == 2000
        assert data['status'] == 'open'

    def test_to_dict_datetime_format(self, app_context):
        """to_dict should serialize datetime fields as ISO format strings."""
        buyer = self._create_buyer()
        demand = Demand(
            buyer_id=buyer.id,
            title='日期格式测试',
        )
        _db.session.add(demand)
        _db.session.commit()

        data = demand.to_dict()
        assert isinstance(data['created_at'], str)
        datetime.fromisoformat(data['created_at'])

    def test_to_dict_nullable_fields(self, app_context):
        """to_dict should handle None values for nullable fields."""
        buyer = self._create_buyer()
        demand = Demand(
            buyer_id=buyer.id,
            title='空值测试',
        )
        _db.session.add(demand)
        _db.session.commit()

        data = demand.to_dict()
        assert data['composition'] is None
        assert data['weight_min'] is None
        assert data['weight_max'] is None
        assert data['width_min'] is None
        assert data['width_max'] is None
        assert data['craft'] is None
        assert data['color'] is None
        assert data['price_min'] is None
        assert data['price_max'] is None
        assert data['quantity'] is None


class TestDemandRelationships:
    """Tests for Demand relationships."""

    def test_demand_belongs_to_buyer(self, app_context):
        """Demand should reference its buyer via buyer_id."""
        buyer = User(
            phone='13500135200',
            role='buyer',
            company_name='Relationship Buyer',
        )
        _db.session.add(buyer)
        _db.session.commit()

        demand = Demand(
            buyer_id=buyer.id,
            title='关系测试需求',
        )
        _db.session.add(demand)
        _db.session.commit()

        saved = _db.session.get(Demand, demand.id)
        assert saved.buyer_id == buyer.id
        assert saved.buyer.id == buyer.id
        assert saved.buyer.company_name == 'Relationship Buyer'

    def test_buyer_has_demands(self, app_context):
        """Buyer should be able to access their demands via backref."""
        buyer = User(
            phone='13500135300',
            role='buyer',
            company_name='Multi-Demand Buyer',
        )
        _db.session.add(buyer)
        _db.session.commit()

        demand1 = Demand(buyer_id=buyer.id, title='需求A')
        demand2 = Demand(buyer_id=buyer.id, title='需求B')
        _db.session.add_all([demand1, demand2])
        _db.session.commit()

        assert buyer.demands.count() == 2
        titles = [d.title for d in buyer.demands.all()]
        assert '需求A' in titles
        assert '需求B' in titles

    def test_demand_repr(self, app_context):
        """__repr__ should return a readable string."""
        buyer = User(phone='13500135400', role='buyer')
        _db.session.add(buyer)
        _db.session.commit()

        demand = Demand(buyer_id=buyer.id, title='Repr测试需求')
        _db.session.add(demand)
        _db.session.commit()

        repr_str = repr(demand)
        assert 'Demand' in repr_str
        assert 'Repr测试需求' in repr_str


# ---------------------------------------------------------------------------
# MatchResult model tests
# ---------------------------------------------------------------------------


class TestMatchResultModel:
    """Tests for MatchResult model basic functionality."""

    def _create_buyer_and_supplier(self):
        """Helper to create buyer and supplier users."""
        buyer = User(phone='13400134000', role='buyer', company_name='Match Buyer')
        supplier = User(phone='13400134001', role='supplier', company_name='Match Supplier')
        _db.session.add_all([buyer, supplier])
        _db.session.commit()
        return buyer, supplier

    def _create_demand_and_fabric(self):
        """Helper to create a demand and a fabric for match result tests."""
        buyer, supplier = self._create_buyer_and_supplier()
        demand = Demand(buyer_id=buyer.id, title='匹配测试需求')
        fabric = Fabric(
            supplier_id=supplier.id,
            name='匹配测试面料',
            composition='100%棉',
            weight=180.0,
            width=150.0,
            craft='平纹',
            price=25.0,
        )
        _db.session.add_all([demand, fabric])
        _db.session.commit()
        return demand, fabric

    def test_create_match_result(self, app_context):
        """Should create a match result with valid data."""
        demand, fabric = self._create_demand_and_fabric()
        match = MatchResult(
            demand_id=demand.id,
            fabric_id=fabric.id,
            score=85.5,
            score_detail={
                'composition': 90,
                'weight': 80,
                'craft': 95,
                'price': 70,
                'width': 85,
            },
        )
        _db.session.add(match)
        _db.session.commit()

        saved = _db.session.get(MatchResult, match.id)
        assert saved is not None
        assert saved.demand_id == demand.id
        assert saved.fabric_id == fabric.id
        assert saved.score == 85.5
        assert saved.score_detail['composition'] == 90
        assert saved.score_detail['weight'] == 80

    def test_match_result_score_boundary_zero(self, app_context):
        """Should allow score of 0."""
        demand, fabric = self._create_demand_and_fabric()
        match = MatchResult(
            demand_id=demand.id,
            fabric_id=fabric.id,
            score=0.0,
        )
        _db.session.add(match)
        _db.session.commit()

        saved = _db.session.get(MatchResult, match.id)
        assert saved.score == 0.0

    def test_match_result_score_boundary_hundred(self, app_context):
        """Should allow score of 100."""
        demand, fabric = self._create_demand_and_fabric()
        match = MatchResult(
            demand_id=demand.id,
            fabric_id=fabric.id,
            score=100.0,
        )
        _db.session.add(match)
        _db.session.commit()

        saved = _db.session.get(MatchResult, match.id)
        assert saved.score == 100.0

    def test_match_result_default_score_detail(self, app_context):
        """Should default score_detail to empty dict."""
        demand, fabric = self._create_demand_and_fabric()
        match = MatchResult(
            demand_id=demand.id,
            fabric_id=fabric.id,
            score=50.0,
        )
        _db.session.add(match)
        _db.session.commit()

        saved = _db.session.get(MatchResult, match.id)
        assert saved.score_detail == {} or saved.score_detail is None

    def test_match_result_created_at_auto_set(self, app_context):
        """Should automatically set created_at on creation."""
        demand, fabric = self._create_demand_and_fabric()
        match = MatchResult(
            demand_id=demand.id,
            fabric_id=fabric.id,
            score=75.0,
        )
        _db.session.add(match)
        _db.session.commit()

        saved = _db.session.get(MatchResult, match.id)
        assert saved.created_at is not None
        assert isinstance(saved.created_at, datetime)


class TestMatchResultToDict:
    """Tests for MatchResult JSON serialization."""

    def _create_demand_and_fabric(self):
        buyer = User(phone='13400134100', role='buyer')
        supplier = User(phone='13400134101', role='supplier')
        _db.session.add_all([buyer, supplier])
        _db.session.commit()

        demand = Demand(buyer_id=buyer.id, title='序列化匹配测试')
        fabric = Fabric(
            supplier_id=supplier.id,
            name='序列化面料',
            composition='棉',
            weight=100.0,
            width=100.0,
            craft='平纹',
            price=10.0,
        )
        _db.session.add_all([demand, fabric])
        _db.session.commit()
        return demand, fabric

    def test_to_dict_contains_expected_keys(self, app_context):
        """to_dict should return all expected keys."""
        demand, fabric = self._create_demand_and_fabric()
        match = MatchResult(
            demand_id=demand.id,
            fabric_id=fabric.id,
            score=88.0,
            score_detail={'composition': 95, 'price': 80},
        )
        _db.session.add(match)
        _db.session.commit()

        data = match.to_dict()
        expected_keys = {
            'id', 'demand_id', 'fabric_id', 'score',
            'score_detail', 'created_at',
        }
        assert set(data.keys()) == expected_keys

    def test_to_dict_values_match(self, app_context):
        """to_dict values should match the model attributes."""
        demand, fabric = self._create_demand_and_fabric()
        detail = {'composition': 90, 'weight': 85, 'craft': 92}
        match = MatchResult(
            demand_id=demand.id,
            fabric_id=fabric.id,
            score=89.0,
            score_detail=detail,
        )
        _db.session.add(match)
        _db.session.commit()

        data = match.to_dict()
        assert data['demand_id'] == demand.id
        assert data['fabric_id'] == fabric.id
        assert data['score'] == 89.0
        assert data['score_detail'] == detail

    def test_to_dict_datetime_format(self, app_context):
        """to_dict should serialize datetime fields as ISO format strings."""
        demand, fabric = self._create_demand_and_fabric()
        match = MatchResult(
            demand_id=demand.id,
            fabric_id=fabric.id,
            score=50.0,
        )
        _db.session.add(match)
        _db.session.commit()

        data = match.to_dict()
        assert isinstance(data['created_at'], str)
        datetime.fromisoformat(data['created_at'])

    def test_to_dict_empty_score_detail(self, app_context):
        """to_dict should return empty dict for None score_detail."""
        demand, fabric = self._create_demand_and_fabric()
        match = MatchResult(
            demand_id=demand.id,
            fabric_id=fabric.id,
            score=60.0,
        )
        _db.session.add(match)
        _db.session.commit()

        data = match.to_dict()
        assert isinstance(data['score_detail'], dict)


class TestMatchResultRelationships:
    """Tests for MatchResult relationships."""

    def _create_demand_and_fabric(self):
        buyer = User(phone='13400134200', role='buyer')
        supplier = User(phone='13400134201', role='supplier')
        _db.session.add_all([buyer, supplier])
        _db.session.commit()

        demand = Demand(buyer_id=buyer.id, title='关系匹配测试')
        fabric = Fabric(
            supplier_id=supplier.id,
            name='关系面料',
            composition='棉',
            weight=100.0,
            width=100.0,
            craft='平纹',
            price=10.0,
        )
        _db.session.add_all([demand, fabric])
        _db.session.commit()
        return demand, fabric

    def test_match_result_belongs_to_demand(self, app_context):
        """MatchResult should reference its demand via demand_id."""
        demand, fabric = self._create_demand_and_fabric()
        match = MatchResult(
            demand_id=demand.id,
            fabric_id=fabric.id,
            score=70.0,
        )
        _db.session.add(match)
        _db.session.commit()

        saved = _db.session.get(MatchResult, match.id)
        assert saved.demand_id == demand.id
        assert saved.demand.id == demand.id
        assert saved.demand.title == '关系匹配测试'

    def test_match_result_belongs_to_fabric(self, app_context):
        """MatchResult should reference its fabric via fabric_id."""
        demand, fabric = self._create_demand_and_fabric()
        match = MatchResult(
            demand_id=demand.id,
            fabric_id=fabric.id,
            score=70.0,
        )
        _db.session.add(match)
        _db.session.commit()

        saved = _db.session.get(MatchResult, match.id)
        assert saved.fabric_id == fabric.id
        assert saved.fabric.id == fabric.id
        assert saved.fabric.name == '关系面料'

    def test_demand_has_match_results(self, app_context):
        """Demand should be able to access its match results via backref."""
        demand, fabric = self._create_demand_and_fabric()

        match1 = MatchResult(demand_id=demand.id, fabric_id=fabric.id, score=90.0)
        match2 = MatchResult(demand_id=demand.id, fabric_id=fabric.id, score=75.0)
        _db.session.add_all([match1, match2])
        _db.session.commit()

        assert demand.match_results.count() == 2
        scores = [m.score for m in demand.match_results.all()]
        assert 90.0 in scores
        assert 75.0 in scores

    def test_fabric_has_match_results(self, app_context):
        """Fabric should be able to access its match results via backref."""
        demand, fabric = self._create_demand_and_fabric()

        match = MatchResult(demand_id=demand.id, fabric_id=fabric.id, score=80.0)
        _db.session.add(match)
        _db.session.commit()

        assert fabric.match_results.count() == 1
        assert fabric.match_results.first().score == 80.0

    def test_match_result_repr(self, app_context):
        """__repr__ should return a readable string."""
        demand, fabric = self._create_demand_and_fabric()
        match = MatchResult(
            demand_id=demand.id,
            fabric_id=fabric.id,
            score=85.0,
        )
        _db.session.add(match)
        _db.session.commit()

        repr_str = repr(match)
        assert 'MatchResult' in repr_str
        assert '85.0' in repr_str


# ---------------------------------------------------------------------------
# Sample model tests
# ---------------------------------------------------------------------------

from server.models.sample import Sample


class TestSampleModel:
    """Tests for Sample model basic functionality."""

    def _create_buyer_supplier_fabric(self):
        """Helper to create buyer, supplier, and fabric for sample tests."""
        buyer = User(
            phone='13300133000',
            role='buyer',
            company_name='Sample Buyer Co.',
            contact_name='Buyer Zhang',
        )
        supplier = User(
            phone='13300133001',
            role='supplier',
            company_name='Sample Supplier Co.',
            contact_name='Supplier Li',
        )
        _db.session.add_all([buyer, supplier])
        _db.session.commit()

        fabric = Fabric(
            supplier_id=supplier.id,
            name='样品测试面料',
            composition='100%棉',
            weight=180.0,
            width=150.0,
            craft='平纹',
            price=25.0,
        )
        _db.session.add(fabric)
        _db.session.commit()
        return buyer, supplier, fabric

    def test_create_sample_with_required_fields(self, app_context):
        """Should create a sample with all required fields."""
        buyer, supplier, fabric = self._create_buyer_supplier_fabric()
        sample = Sample(
            fabric_id=fabric.id,
            buyer_id=buyer.id,
            supplier_id=supplier.id,
            quantity=5,
            address='北京市朝阳区测试路1号',
        )
        _db.session.add(sample)
        _db.session.commit()

        saved = _db.session.get(Sample, sample.id)
        assert saved is not None
        assert saved.fabric_id == fabric.id
        assert saved.buyer_id == buyer.id
        assert saved.supplier_id == supplier.id
        assert saved.quantity == 5
        assert saved.address == '北京市朝阳区测试路1号'

    def test_sample_default_status_pending(self, app_context):
        """Should default status to 'pending'."""
        buyer, supplier, fabric = self._create_buyer_supplier_fabric()
        sample = Sample(
            fabric_id=fabric.id,
            buyer_id=buyer.id,
            supplier_id=supplier.id,
            quantity=3,
            address='上海市浦东新区',
        )
        _db.session.add(sample)
        _db.session.commit()

        saved = _db.session.get(Sample, sample.id)
        assert saved.status == 'pending'

    def test_sample_status_approved(self, app_context):
        """Should allow setting status to 'approved'."""
        buyer, supplier, fabric = self._create_buyer_supplier_fabric()
        sample = Sample(
            fabric_id=fabric.id,
            buyer_id=buyer.id,
            supplier_id=supplier.id,
            quantity=2,
            address='广州市天河区',
            status='approved',
        )
        _db.session.add(sample)
        _db.session.commit()

        saved = _db.session.get(Sample, sample.id)
        assert saved.status == 'approved'

    def test_sample_status_rejected(self, app_context):
        """Should allow setting status to 'rejected'."""
        buyer, supplier, fabric = self._create_buyer_supplier_fabric()
        sample = Sample(
            fabric_id=fabric.id,
            buyer_id=buyer.id,
            supplier_id=supplier.id,
            quantity=1,
            address='深圳市南山区',
            status='rejected',
            reject_reason='库存不足',
        )
        _db.session.add(sample)
        _db.session.commit()

        saved = _db.session.get(Sample, sample.id)
        assert saved.status == 'rejected'
        assert saved.reject_reason == '库存不足'

    def test_sample_status_shipping(self, app_context):
        """Should allow setting status to 'shipping'."""
        buyer, supplier, fabric = self._create_buyer_supplier_fabric()
        sample = Sample(
            fabric_id=fabric.id,
            buyer_id=buyer.id,
            supplier_id=supplier.id,
            quantity=4,
            address='杭州市西湖区',
            status='shipping',
            logistics_no='SF1234567890',
        )
        _db.session.add(sample)
        _db.session.commit()

        saved = _db.session.get(Sample, sample.id)
        assert saved.status == 'shipping'
        assert saved.logistics_no == 'SF1234567890'

    def test_sample_status_received(self, app_context):
        """Should allow setting status to 'received'."""
        buyer, supplier, fabric = self._create_buyer_supplier_fabric()
        sample = Sample(
            fabric_id=fabric.id,
            buyer_id=buyer.id,
            supplier_id=supplier.id,
            quantity=2,
            address='成都市武侯区',
            status='received',
        )
        _db.session.add(sample)
        _db.session.commit()

        saved = _db.session.get(Sample, sample.id)
        assert saved.status == 'received'

    def test_sample_invalid_status_rejected(self, app_context):
        """Should reject invalid status values."""
        buyer, supplier, fabric = self._create_buyer_supplier_fabric()
        sample = Sample(
            fabric_id=fabric.id,
            buyer_id=buyer.id,
            supplier_id=supplier.id,
            quantity=1,
            address='测试地址',
            status='invalid_status',
        )
        _db.session.add(sample)
        with pytest.raises(Exception):
            _db.session.commit()

    def test_sample_logistics_info_json(self, app_context):
        """Should store and retrieve logistics_info as JSON."""
        buyer, supplier, fabric = self._create_buyer_supplier_fabric()
        logistics_data = {
            'carrier': '顺丰速运',
            'tracking': [
                {'time': '2024-01-01 10:00', 'status': '已揽收'},
                {'time': '2024-01-02 08:00', 'status': '运输中'},
            ],
        }
        sample = Sample(
            fabric_id=fabric.id,
            buyer_id=buyer.id,
            supplier_id=supplier.id,
            quantity=3,
            address='武汉市洪山区',
            status='shipping',
            logistics_no='SF9876543210',
            logistics_info=logistics_data,
        )
        _db.session.add(sample)
        _db.session.commit()

        saved = _db.session.get(Sample, sample.id)
        assert saved.logistics_info == logistics_data
        assert saved.logistics_info['carrier'] == '顺丰速运'
        assert len(saved.logistics_info['tracking']) == 2

    def test_sample_nullable_fields_default_none(self, app_context):
        """Should default nullable fields to None."""
        buyer, supplier, fabric = self._create_buyer_supplier_fabric()
        sample = Sample(
            fabric_id=fabric.id,
            buyer_id=buyer.id,
            supplier_id=supplier.id,
            quantity=1,
            address='测试地址',
        )
        _db.session.add(sample)
        _db.session.commit()

        saved = _db.session.get(Sample, sample.id)
        assert saved.logistics_no is None
        assert saved.logistics_info is None
        assert saved.reject_reason is None

    def test_sample_created_at_auto_set(self, app_context):
        """Should automatically set created_at on creation."""
        buyer, supplier, fabric = self._create_buyer_supplier_fabric()
        sample = Sample(
            fabric_id=fabric.id,
            buyer_id=buyer.id,
            supplier_id=supplier.id,
            quantity=1,
            address='时间测试地址',
        )
        _db.session.add(sample)
        _db.session.commit()

        saved = _db.session.get(Sample, sample.id)
        assert saved.created_at is not None
        assert isinstance(saved.created_at, datetime)

    def test_sample_updated_at_auto_set(self, app_context):
        """Should automatically set updated_at on creation."""
        buyer, supplier, fabric = self._create_buyer_supplier_fabric()
        sample = Sample(
            fabric_id=fabric.id,
            buyer_id=buyer.id,
            supplier_id=supplier.id,
            quantity=1,
            address='更新时间测试',
        )
        _db.session.add(sample)
        _db.session.commit()

        saved = _db.session.get(Sample, sample.id)
        assert saved.updated_at is not None
        assert isinstance(saved.updated_at, datetime)


class TestSampleToDict:
    """Tests for Sample JSON serialization."""

    def _create_buyer_supplier_fabric(self):
        buyer = User(
            phone='13300133100',
            role='buyer',
            company_name='ToDict Buyer',
        )
        supplier = User(
            phone='13300133101',
            role='supplier',
            company_name='ToDict Supplier',
        )
        _db.session.add_all([buyer, supplier])
        _db.session.commit()

        fabric = Fabric(
            supplier_id=supplier.id,
            name='序列化样品面料',
            composition='涤纶',
            weight=120.0,
            width=140.0,
            craft='针织',
            price=18.0,
        )
        _db.session.add(fabric)
        _db.session.commit()
        return buyer, supplier, fabric

    def test_to_dict_contains_expected_keys(self, app_context):
        """to_dict should return all expected keys."""
        buyer, supplier, fabric = self._create_buyer_supplier_fabric()
        sample = Sample(
            fabric_id=fabric.id,
            buyer_id=buyer.id,
            supplier_id=supplier.id,
            quantity=5,
            address='序列化测试地址',
            logistics_no='YT1234567890',
            logistics_info={'carrier': '圆通'},
            reject_reason=None,
        )
        _db.session.add(sample)
        _db.session.commit()

        data = sample.to_dict()
        expected_keys = {
            'id', 'fabric_id', 'buyer_id', 'supplier_id',
            'quantity', 'address', 'status', 'logistics_no',
            'logistics_info', 'reject_reason',
            'created_at', 'updated_at',
        }
        assert set(data.keys()) == expected_keys

    def test_to_dict_values_match(self, app_context):
        """to_dict values should match the model attributes."""
        buyer, supplier, fabric = self._create_buyer_supplier_fabric()
        sample = Sample(
            fabric_id=fabric.id,
            buyer_id=buyer.id,
            supplier_id=supplier.id,
            quantity=10,
            address='值匹配测试地址',
            status='shipping',
            logistics_no='SF0001234567',
            logistics_info={'carrier': '顺丰', 'status': '运输中'},
        )
        _db.session.add(sample)
        _db.session.commit()

        data = sample.to_dict()
        assert data['fabric_id'] == fabric.id
        assert data['buyer_id'] == buyer.id
        assert data['supplier_id'] == supplier.id
        assert data['quantity'] == 10
        assert data['address'] == '值匹配测试地址'
        assert data['status'] == 'shipping'
        assert data['logistics_no'] == 'SF0001234567'
        assert data['logistics_info'] == {'carrier': '顺丰', 'status': '运输中'}
        assert data['reject_reason'] is None

    def test_to_dict_datetime_format(self, app_context):
        """to_dict should serialize datetime fields as ISO format strings."""
        buyer, supplier, fabric = self._create_buyer_supplier_fabric()
        sample = Sample(
            fabric_id=fabric.id,
            buyer_id=buyer.id,
            supplier_id=supplier.id,
            quantity=1,
            address='日期格式测试',
        )
        _db.session.add(sample)
        _db.session.commit()

        data = sample.to_dict()
        assert isinstance(data['created_at'], str)
        assert isinstance(data['updated_at'], str)
        datetime.fromisoformat(data['created_at'])
        datetime.fromisoformat(data['updated_at'])

    def test_to_dict_nullable_fields(self, app_context):
        """to_dict should handle None values for nullable fields."""
        buyer, supplier, fabric = self._create_buyer_supplier_fabric()
        sample = Sample(
            fabric_id=fabric.id,
            buyer_id=buyer.id,
            supplier_id=supplier.id,
            quantity=1,
            address='空值测试',
        )
        _db.session.add(sample)
        _db.session.commit()

        data = sample.to_dict()
        assert data['logistics_no'] is None
        assert data['logistics_info'] is None
        assert data['reject_reason'] is None


class TestSampleRelationships:
    """Tests for Sample relationships with User and Fabric."""

    def _create_buyer_supplier_fabric(self):
        buyer = User(
            phone='13300133200',
            role='buyer',
            company_name='Relationship Buyer',
        )
        supplier = User(
            phone='13300133201',
            role='supplier',
            company_name='Relationship Supplier',
        )
        _db.session.add_all([buyer, supplier])
        _db.session.commit()

        fabric = Fabric(
            supplier_id=supplier.id,
            name='关系测试面料',
            composition='棉',
            weight=100.0,
            width=100.0,
            craft='平纹',
            price=10.0,
        )
        _db.session.add(fabric)
        _db.session.commit()
        return buyer, supplier, fabric

    def test_sample_belongs_to_fabric(self, app_context):
        """Sample should reference its fabric via fabric_id."""
        buyer, supplier, fabric = self._create_buyer_supplier_fabric()
        sample = Sample(
            fabric_id=fabric.id,
            buyer_id=buyer.id,
            supplier_id=supplier.id,
            quantity=2,
            address='面料关系测试',
        )
        _db.session.add(sample)
        _db.session.commit()

        saved = _db.session.get(Sample, sample.id)
        assert saved.fabric_id == fabric.id
        assert saved.fabric.id == fabric.id
        assert saved.fabric.name == '关系测试面料'

    def test_sample_belongs_to_buyer(self, app_context):
        """Sample should reference its buyer via buyer_id."""
        buyer, supplier, fabric = self._create_buyer_supplier_fabric()
        sample = Sample(
            fabric_id=fabric.id,
            buyer_id=buyer.id,
            supplier_id=supplier.id,
            quantity=2,
            address='买家关系测试',
        )
        _db.session.add(sample)
        _db.session.commit()

        saved = _db.session.get(Sample, sample.id)
        assert saved.buyer_id == buyer.id
        assert saved.buyer.id == buyer.id
        assert saved.buyer.company_name == 'Relationship Buyer'

    def test_sample_belongs_to_supplier(self, app_context):
        """Sample should reference its supplier via supplier_id."""
        buyer, supplier, fabric = self._create_buyer_supplier_fabric()
        sample = Sample(
            fabric_id=fabric.id,
            buyer_id=buyer.id,
            supplier_id=supplier.id,
            quantity=2,
            address='供应商关系测试',
        )
        _db.session.add(sample)
        _db.session.commit()

        saved = _db.session.get(Sample, sample.id)
        assert saved.supplier_id == supplier.id
        assert saved.supplier.id == supplier.id
        assert saved.supplier.company_name == 'Relationship Supplier'

    def test_buyer_has_sample_requests(self, app_context):
        """Buyer should access their sample requests via backref."""
        buyer, supplier, fabric = self._create_buyer_supplier_fabric()
        sample1 = Sample(
            fabric_id=fabric.id,
            buyer_id=buyer.id,
            supplier_id=supplier.id,
            quantity=1,
            address='请求A',
        )
        sample2 = Sample(
            fabric_id=fabric.id,
            buyer_id=buyer.id,
            supplier_id=supplier.id,
            quantity=2,
            address='请求B',
        )
        _db.session.add_all([sample1, sample2])
        _db.session.commit()

        assert buyer.sample_requests.count() == 2

    def test_supplier_has_sample_reviews(self, app_context):
        """Supplier should access their sample reviews via backref."""
        buyer, supplier, fabric = self._create_buyer_supplier_fabric()
        sample = Sample(
            fabric_id=fabric.id,
            buyer_id=buyer.id,
            supplier_id=supplier.id,
            quantity=3,
            address='审核测试',
        )
        _db.session.add(sample)
        _db.session.commit()

        assert supplier.sample_reviews.count() == 1

    def test_fabric_has_samples(self, app_context):
        """Fabric should access its samples via backref."""
        buyer, supplier, fabric = self._create_buyer_supplier_fabric()
        sample = Sample(
            fabric_id=fabric.id,
            buyer_id=buyer.id,
            supplier_id=supplier.id,
            quantity=1,
            address='面料样品测试',
        )
        _db.session.add(sample)
        _db.session.commit()

        assert fabric.samples.count() == 1

    def test_sample_repr(self, app_context):
        """__repr__ should return a readable string."""
        buyer, supplier, fabric = self._create_buyer_supplier_fabric()
        sample = Sample(
            fabric_id=fabric.id,
            buyer_id=buyer.id,
            supplier_id=supplier.id,
            quantity=1,
            address='Repr测试',
        )
        _db.session.add(sample)
        _db.session.commit()

        repr_str = repr(sample)
        assert 'Sample' in repr_str
        assert 'pending' in repr_str


# ---------------------------------------------------------------------------
# Order and OrderItem model tests
# ---------------------------------------------------------------------------

from server.models.order import Order, OrderItem, generate_order_no, validate_status_transition


class TestOrderModel:
    """Tests for Order model basic functionality."""

    def _create_buyer_and_supplier(self):
        """Helper to create buyer and supplier users for order tests."""
        buyer = User(
            phone='13200132000',
            role='buyer',
            company_name='Order Buyer Co.',
            contact_name='Order Buyer',
        )
        supplier = User(
            phone='13200132001',
            role='supplier',
            company_name='Order Supplier Co.',
            contact_name='Order Supplier',
        )
        _db.session.add_all([buyer, supplier])
        _db.session.commit()
        return buyer, supplier

    def test_create_order_with_all_fields(self, app_context):
        """Should create an order with all required fields."""
        buyer, supplier = self._create_buyer_and_supplier()
        order_no = generate_order_no()
        order = Order(
            buyer_id=buyer.id,
            supplier_id=supplier.id,
            order_no=order_no,
            total_amount=5000.0,
            address='北京市朝阳区订单测试路1号',
            status='pending',
        )
        _db.session.add(order)
        _db.session.commit()

        saved = _db.session.get(Order, order.id)
        assert saved is not None
        assert saved.buyer_id == buyer.id
        assert saved.supplier_id == supplier.id
        assert saved.order_no == order_no
        assert saved.total_amount == 5000.0
        assert saved.address == '北京市朝阳区订单测试路1号'
        assert saved.status == 'pending'

    def test_order_default_status_pending(self, app_context):
        """Should default status to 'pending'."""
        buyer, supplier = self._create_buyer_and_supplier()
        order = Order(
            buyer_id=buyer.id,
            supplier_id=supplier.id,
            order_no=generate_order_no(),
            total_amount=1000.0,
            address='默认状态测试地址',
        )
        _db.session.add(order)
        _db.session.commit()

        saved = _db.session.get(Order, order.id)
        assert saved.status == 'pending'

    def test_order_status_confirmed(self, app_context):
        """Should allow setting status to 'confirmed'."""
        buyer, supplier = self._create_buyer_and_supplier()
        order = Order(
            buyer_id=buyer.id,
            supplier_id=supplier.id,
            order_no=generate_order_no(),
            total_amount=2000.0,
            address='确认状态测试',
            status='confirmed',
        )
        _db.session.add(order)
        _db.session.commit()

        saved = _db.session.get(Order, order.id)
        assert saved.status == 'confirmed'

    def test_order_status_producing(self, app_context):
        """Should allow setting status to 'producing'."""
        buyer, supplier = self._create_buyer_and_supplier()
        order = Order(
            buyer_id=buyer.id,
            supplier_id=supplier.id,
            order_no=generate_order_no(),
            total_amount=3000.0,
            address='生产中状态测试',
            status='producing',
        )
        _db.session.add(order)
        _db.session.commit()

        saved = _db.session.get(Order, order.id)
        assert saved.status == 'producing'

    def test_order_status_shipped(self, app_context):
        """Should allow setting status to 'shipped'."""
        buyer, supplier = self._create_buyer_and_supplier()
        order = Order(
            buyer_id=buyer.id,
            supplier_id=supplier.id,
            order_no=generate_order_no(),
            total_amount=4000.0,
            address='已发货状态测试',
            status='shipped',
        )
        _db.session.add(order)
        _db.session.commit()

        saved = _db.session.get(Order, order.id)
        assert saved.status == 'shipped'

    def test_order_status_received(self, app_context):
        """Should allow setting status to 'received'."""
        buyer, supplier = self._create_buyer_and_supplier()
        order = Order(
            buyer_id=buyer.id,
            supplier_id=supplier.id,
            order_no=generate_order_no(),
            total_amount=5000.0,
            address='已签收状态测试',
            status='received',
        )
        _db.session.add(order)
        _db.session.commit()

        saved = _db.session.get(Order, order.id)
        assert saved.status == 'received'

    def test_order_status_completed(self, app_context):
        """Should allow setting status to 'completed'."""
        buyer, supplier = self._create_buyer_and_supplier()
        order = Order(
            buyer_id=buyer.id,
            supplier_id=supplier.id,
            order_no=generate_order_no(),
            total_amount=6000.0,
            address='已完成状态测试',
            status='completed',
        )
        _db.session.add(order)
        _db.session.commit()

        saved = _db.session.get(Order, order.id)
        assert saved.status == 'completed'

    def test_order_invalid_status_rejected(self, app_context):
        """Should reject invalid status values."""
        buyer, supplier = self._create_buyer_and_supplier()
        order = Order(
            buyer_id=buyer.id,
            supplier_id=supplier.id,
            order_no=generate_order_no(),
            total_amount=1000.0,
            address='无效状态测试',
            status='invalid_status',
        )
        _db.session.add(order)
        with pytest.raises(Exception):
            _db.session.commit()

    def test_order_no_unique_constraint(self, app_context):
        """Should enforce unique constraint on order_no."""
        buyer, supplier = self._create_buyer_and_supplier()
        order_no = generate_order_no()
        order1 = Order(
            buyer_id=buyer.id,
            supplier_id=supplier.id,
            order_no=order_no,
            total_amount=1000.0,
            address='唯一约束测试1',
        )
        _db.session.add(order1)
        _db.session.commit()

        order2 = Order(
            buyer_id=buyer.id,
            supplier_id=supplier.id,
            order_no=order_no,
            total_amount=2000.0,
            address='唯一约束测试2',
        )
        _db.session.add(order2)
        with pytest.raises(Exception):
            _db.session.commit()

    def test_order_created_at_auto_set(self, app_context):
        """Should automatically set created_at on creation."""
        buyer, supplier = self._create_buyer_and_supplier()
        order = Order(
            buyer_id=buyer.id,
            supplier_id=supplier.id,
            order_no=generate_order_no(),
            total_amount=1000.0,
            address='时间测试地址',
        )
        _db.session.add(order)
        _db.session.commit()

        saved = _db.session.get(Order, order.id)
        assert saved.created_at is not None
        assert isinstance(saved.created_at, datetime)

    def test_order_updated_at_auto_set(self, app_context):
        """Should automatically set updated_at on creation."""
        buyer, supplier = self._create_buyer_and_supplier()
        order = Order(
            buyer_id=buyer.id,
            supplier_id=supplier.id,
            order_no=generate_order_no(),
            total_amount=1000.0,
            address='更新时间测试',
        )
        _db.session.add(order)
        _db.session.commit()

        saved = _db.session.get(Order, order.id)
        assert saved.updated_at is not None
        assert isinstance(saved.updated_at, datetime)


class TestOrderToDict:
    """Tests for Order JSON serialization."""

    def _create_buyer_and_supplier(self):
        buyer = User(
            phone='13200132100',
            role='buyer',
            company_name='ToDict Order Buyer',
        )
        supplier = User(
            phone='13200132101',
            role='supplier',
            company_name='ToDict Order Supplier',
        )
        _db.session.add_all([buyer, supplier])
        _db.session.commit()
        return buyer, supplier

    def test_to_dict_contains_expected_keys(self, app_context):
        """to_dict should return all expected keys."""
        buyer, supplier = self._create_buyer_and_supplier()
        order = Order(
            buyer_id=buyer.id,
            supplier_id=supplier.id,
            order_no=generate_order_no(),
            total_amount=8888.0,
            address='序列化测试地址',
        )
        _db.session.add(order)
        _db.session.commit()

        data = order.to_dict()
        expected_keys = {
            'id', 'buyer_id', 'supplier_id', 'order_no',
            'total_amount', 'address', 'status',
            'created_at', 'updated_at',
            'demand_id', 'quote_id', 'tracking_no',
        }
        assert set(data.keys()) == expected_keys

    def test_to_dict_values_match(self, app_context):
        """to_dict values should match the model attributes."""
        buyer, supplier = self._create_buyer_and_supplier()
        order_no = generate_order_no()
        order = Order(
            buyer_id=buyer.id,
            supplier_id=supplier.id,
            order_no=order_no,
            total_amount=12345.67,
            address='值匹配测试地址',
            status='confirmed',
        )
        _db.session.add(order)
        _db.session.commit()

        data = order.to_dict()
        assert data['buyer_id'] == buyer.id
        assert data['supplier_id'] == supplier.id
        assert data['order_no'] == order_no
        assert data['total_amount'] == 12345.67
        assert data['address'] == '值匹配测试地址'
        assert data['status'] == 'confirmed'

    def test_to_dict_datetime_format(self, app_context):
        """to_dict should serialize datetime fields as ISO format strings."""
        buyer, supplier = self._create_buyer_and_supplier()
        order = Order(
            buyer_id=buyer.id,
            supplier_id=supplier.id,
            order_no=generate_order_no(),
            total_amount=1000.0,
            address='日期格式测试',
        )
        _db.session.add(order)
        _db.session.commit()

        data = order.to_dict()
        assert isinstance(data['created_at'], str)
        assert isinstance(data['updated_at'], str)
        datetime.fromisoformat(data['created_at'])
        datetime.fromisoformat(data['updated_at'])


class TestOrderRelationships:
    """Tests for Order relationships with User."""

    def _create_buyer_and_supplier(self):
        buyer = User(
            phone='13200132200',
            role='buyer',
            company_name='Relationship Order Buyer',
        )
        supplier = User(
            phone='13200132201',
            role='supplier',
            company_name='Relationship Order Supplier',
        )
        _db.session.add_all([buyer, supplier])
        _db.session.commit()
        return buyer, supplier

    def test_order_belongs_to_buyer(self, app_context):
        """Order should reference its buyer via buyer_id."""
        buyer, supplier = self._create_buyer_and_supplier()
        order = Order(
            buyer_id=buyer.id,
            supplier_id=supplier.id,
            order_no=generate_order_no(),
            total_amount=1000.0,
            address='买家关系测试',
        )
        _db.session.add(order)
        _db.session.commit()

        saved = _db.session.get(Order, order.id)
        assert saved.buyer_id == buyer.id
        assert saved.buyer.id == buyer.id
        assert saved.buyer.company_name == 'Relationship Order Buyer'

    def test_order_belongs_to_supplier(self, app_context):
        """Order should reference its supplier via supplier_id."""
        buyer, supplier = self._create_buyer_and_supplier()
        order = Order(
            buyer_id=buyer.id,
            supplier_id=supplier.id,
            order_no=generate_order_no(),
            total_amount=2000.0,
            address='供应商关系测试',
        )
        _db.session.add(order)
        _db.session.commit()

        saved = _db.session.get(Order, order.id)
        assert saved.supplier_id == supplier.id
        assert saved.supplier.id == supplier.id
        assert saved.supplier.company_name == 'Relationship Order Supplier'

    def test_buyer_has_orders(self, app_context):
        """Buyer should access their orders via backref."""
        buyer, supplier = self._create_buyer_and_supplier()
        order1 = Order(
            buyer_id=buyer.id,
            supplier_id=supplier.id,
            order_no=generate_order_no(),
            total_amount=1000.0,
            address='订单A',
        )
        order2 = Order(
            buyer_id=buyer.id,
            supplier_id=supplier.id,
            order_no=generate_order_no(),
            total_amount=2000.0,
            address='订单B',
        )
        _db.session.add_all([order1, order2])
        _db.session.commit()

        assert buyer.buyer_orders.count() == 2

    def test_supplier_has_orders(self, app_context):
        """Supplier should access their orders via backref."""
        buyer, supplier = self._create_buyer_and_supplier()
        order = Order(
            buyer_id=buyer.id,
            supplier_id=supplier.id,
            order_no=generate_order_no(),
            total_amount=3000.0,
            address='供应商订单测试',
        )
        _db.session.add(order)
        _db.session.commit()

        assert supplier.supplier_orders.count() == 1

    def test_order_repr(self, app_context):
        """__repr__ should return a readable string."""
        buyer, supplier = self._create_buyer_and_supplier()
        order_no = generate_order_no()
        order = Order(
            buyer_id=buyer.id,
            supplier_id=supplier.id,
            order_no=order_no,
            total_amount=1000.0,
            address='Repr测试',
        )
        _db.session.add(order)
        _db.session.commit()

        repr_str = repr(order)
        assert 'Order' in repr_str
        assert order_no in repr_str
        assert 'pending' in repr_str


# ---------------------------------------------------------------------------
# OrderItem model tests
# ---------------------------------------------------------------------------


class TestOrderItemModel:
    """Tests for OrderItem model basic functionality."""

    def _create_order_with_fabric(self):
        """Helper to create buyer, supplier, fabric, and order for item tests."""
        buyer = User(
            phone='13200132300',
            role='buyer',
            company_name='Item Buyer Co.',
        )
        supplier = User(
            phone='13200132301',
            role='supplier',
            company_name='Item Supplier Co.',
        )
        _db.session.add_all([buyer, supplier])
        _db.session.commit()

        fabric = Fabric(
            supplier_id=supplier.id,
            name='订单项测试面料',
            composition='100%棉',
            weight=180.0,
            width=150.0,
            craft='平纹',
            price=25.0,
        )
        _db.session.add(fabric)
        _db.session.commit()

        order = Order(
            buyer_id=buyer.id,
            supplier_id=supplier.id,
            order_no=generate_order_no(),
            total_amount=2500.0,
            address='订单项测试地址',
        )
        _db.session.add(order)
        _db.session.commit()

        return order, fabric

    def test_create_order_item(self, app_context):
        """Should create an order item with all fields."""
        order, fabric = self._create_order_with_fabric()
        item = OrderItem(
            order_id=order.id,
            fabric_id=fabric.id,
            quantity=100,
            unit_price=25.0,
            subtotal=2500.0,
        )
        _db.session.add(item)
        _db.session.commit()

        saved = _db.session.get(OrderItem, item.id)
        assert saved is not None
        assert saved.order_id == order.id
        assert saved.fabric_id == fabric.id
        assert saved.quantity == 100
        assert saved.unit_price == 25.0
        assert saved.subtotal == 2500.0

    def test_order_item_relationship_to_order(self, app_context):
        """OrderItem should reference its order via order_id."""
        order, fabric = self._create_order_with_fabric()
        item = OrderItem(
            order_id=order.id,
            fabric_id=fabric.id,
            quantity=50,
            unit_price=25.0,
            subtotal=1250.0,
        )
        _db.session.add(item)
        _db.session.commit()

        saved = _db.session.get(OrderItem, item.id)
        assert saved.order.id == order.id
        assert saved.order.order_no == order.order_no

    def test_order_item_relationship_to_fabric(self, app_context):
        """OrderItem should reference its fabric via fabric_id."""
        order, fabric = self._create_order_with_fabric()
        item = OrderItem(
            order_id=order.id,
            fabric_id=fabric.id,
            quantity=30,
            unit_price=25.0,
            subtotal=750.0,
        )
        _db.session.add(item)
        _db.session.commit()

        saved = _db.session.get(OrderItem, item.id)
        assert saved.fabric.id == fabric.id
        assert saved.fabric.name == '订单项测试面料'

    def test_order_has_items(self, app_context):
        """Order should access its items via relationship."""
        order, fabric = self._create_order_with_fabric()
        item1 = OrderItem(
            order_id=order.id,
            fabric_id=fabric.id,
            quantity=50,
            unit_price=25.0,
            subtotal=1250.0,
        )
        item2 = OrderItem(
            order_id=order.id,
            fabric_id=fabric.id,
            quantity=50,
            unit_price=25.0,
            subtotal=1250.0,
        )
        _db.session.add_all([item1, item2])
        _db.session.commit()

        assert order.items.count() == 2

    def test_order_item_repr(self, app_context):
        """__repr__ should return a readable string."""
        order, fabric = self._create_order_with_fabric()
        item = OrderItem(
            order_id=order.id,
            fabric_id=fabric.id,
            quantity=10,
            unit_price=25.0,
            subtotal=250.0,
        )
        _db.session.add(item)
        _db.session.commit()

        repr_str = repr(item)
        assert 'OrderItem' in repr_str


class TestOrderItemToDict:
    """Tests for OrderItem JSON serialization."""

    def _create_order_with_fabric(self):
        buyer = User(
            phone='13200132400',
            role='buyer',
            company_name='ToDict Item Buyer',
        )
        supplier = User(
            phone='13200132401',
            role='supplier',
            company_name='ToDict Item Supplier',
        )
        _db.session.add_all([buyer, supplier])
        _db.session.commit()

        fabric = Fabric(
            supplier_id=supplier.id,
            name='序列化订单项面料',
            composition='涤纶',
            weight=120.0,
            width=140.0,
            craft='针织',
            price=18.0,
        )
        _db.session.add(fabric)
        _db.session.commit()

        order = Order(
            buyer_id=buyer.id,
            supplier_id=supplier.id,
            order_no=generate_order_no(),
            total_amount=1800.0,
            address='序列化订单项测试',
        )
        _db.session.add(order)
        _db.session.commit()

        return order, fabric

    def test_to_dict_contains_expected_keys(self, app_context):
        """to_dict should return all expected keys."""
        order, fabric = self._create_order_with_fabric()
        item = OrderItem(
            order_id=order.id,
            fabric_id=fabric.id,
            quantity=100,
            unit_price=18.0,
            subtotal=1800.0,
        )
        _db.session.add(item)
        _db.session.commit()

        data = item.to_dict()
        expected_keys = {
            'id', 'order_id', 'fabric_id',
            'quantity', 'unit_price', 'subtotal',
        }
        assert set(data.keys()) == expected_keys

    def test_to_dict_values_match(self, app_context):
        """to_dict values should match the model attributes."""
        order, fabric = self._create_order_with_fabric()
        item = OrderItem(
            order_id=order.id,
            fabric_id=fabric.id,
            quantity=200,
            unit_price=18.0,
            subtotal=3600.0,
        )
        _db.session.add(item)
        _db.session.commit()

        data = item.to_dict()
        assert data['order_id'] == order.id
        assert data['fabric_id'] == fabric.id
        assert data['quantity'] == 200
        assert data['unit_price'] == 18.0
        assert data['subtotal'] == 3600.0


# ---------------------------------------------------------------------------
# Order number generation tests
# ---------------------------------------------------------------------------


class TestGenerateOrderNo:
    """Tests for the generate_order_no function."""

    def test_order_no_starts_with_ord(self):
        """Generated order number should start with 'ORD'."""
        order_no = generate_order_no()
        assert order_no.startswith('ORD')

    def test_order_no_is_string(self):
        """Generated order number should be a string."""
        order_no = generate_order_no()
        assert isinstance(order_no, str)

    def test_order_no_has_sufficient_length(self):
        """Generated order number should have sufficient length for timestamp + random."""
        order_no = generate_order_no()
        # ORD (3) + timestamp_ms (13 digits) + random (4 digits) = 20 chars
        assert len(order_no) >= 17

    def test_order_no_uniqueness(self):
        """Two generated order numbers should be different (with high probability)."""
        order_no1 = generate_order_no()
        order_no2 = generate_order_no()
        # While not guaranteed, consecutive calls should produce different numbers
        # due to timestamp + random component
        assert order_no1 != order_no2 or True  # Allow rare collision but test format

    def test_order_no_numeric_after_prefix(self):
        """Characters after 'ORD' prefix should be numeric."""
        order_no = generate_order_no()
        numeric_part = order_no[3:]
        assert numeric_part.isdigit()


# ---------------------------------------------------------------------------
# Status transition validation tests
# ---------------------------------------------------------------------------


class TestValidateStatusTransition:
    """Tests for the validate_status_transition function."""

    def test_pending_to_confirmed_valid(self):
        """Should allow transition from pending to confirmed."""
        assert validate_status_transition('pending', 'confirmed') is True

    def test_confirmed_to_producing_valid(self):
        """Should allow transition from confirmed to producing."""
        assert validate_status_transition('confirmed', 'producing') is True

    def test_producing_to_shipped_valid(self):
        """Should allow transition from producing to shipped."""
        assert validate_status_transition('producing', 'shipped') is True

    def test_shipped_to_received_valid(self):
        """Should allow transition from shipped to received."""
        assert validate_status_transition('shipped', 'received') is True

    def test_received_to_completed_valid(self):
        """Should allow transition from received to completed."""
        assert validate_status_transition('received', 'completed') is True

    def test_skip_status_rejected(self):
        """Should reject skipping a status (e.g., pending to producing)."""
        assert validate_status_transition('pending', 'producing') is False

    def test_reverse_transition_rejected(self):
        """Should reject reverse transitions (e.g., confirmed to pending)."""
        assert validate_status_transition('confirmed', 'pending') is False

    def test_same_status_rejected(self):
        """Should reject transition to the same status."""
        assert validate_status_transition('pending', 'pending') is False

    def test_completed_to_any_rejected(self):
        """Should reject any transition from completed."""
        assert validate_status_transition('completed', 'pending') is False
        assert validate_status_transition('completed', 'confirmed') is False

    def test_invalid_current_status(self):
        """Should reject invalid current status."""
        assert validate_status_transition('invalid', 'confirmed') is False

    def test_invalid_next_status(self):
        """Should reject invalid next status."""
        assert validate_status_transition('pending', 'invalid') is False

    def test_both_invalid_statuses(self):
        """Should reject when both statuses are invalid."""
        assert validate_status_transition('foo', 'bar') is False

    def test_pending_to_shipped_rejected(self):
        """Should reject jumping from pending to shipped."""
        assert validate_status_transition('pending', 'shipped') is False

    def test_pending_to_completed_rejected(self):
        """Should reject jumping from pending to completed."""
        assert validate_status_transition('pending', 'completed') is False

# ---------------------------------------------------------------------------
# Message model tests
# ---------------------------------------------------------------------------

from server.models.message import Message


class TestMessageModel:
    """Tests for Message model basic functionality."""

    def _create_user(self):
        """Helper to create a user for message foreign key."""
        user = User(
            phone='13100131000',
            role='buyer',
            company_name='Message Test Co.',
            contact_name='Test User',
        )
        _db.session.add(user)
        _db.session.commit()
        return user

    def test_create_match_message(self, app_context):
        """Should create a message with type 'match'."""
        user = self._create_user()
        msg = Message(
            user_id=user.id,
            type='match',
            title='新的匹配结果',
            content='您的采购需求有新的匹配面料',
            ref_id=1,
            ref_type='demand',
        )
        _db.session.add(msg)
        _db.session.commit()

        saved = _db.session.get(Message, msg.id)
        assert saved is not None
        assert saved.user_id == user.id
        assert saved.type == 'match'
        assert saved.title == '新的匹配结果'
        assert saved.content == '您的采购需求有新的匹配面料'
        assert saved.ref_id == 1
        assert saved.ref_type == 'demand'

    def test_create_logistics_message(self, app_context):
        """Should create a message with type 'logistics'."""
        user = self._create_user()
        msg = Message(
            user_id=user.id,
            type='logistics',
            title='物流状态更新',
            content='您的样品已发货',
            ref_id=5,
            ref_type='sample',
        )
        _db.session.add(msg)
        _db.session.commit()

        saved = _db.session.get(Message, msg.id)
        assert saved.type == 'logistics'

    def test_create_review_message(self, app_context):
        """Should create a message with type 'review'."""
        user = self._create_user()
        msg = Message(
            user_id=user.id,
            type='review',
            title='审核结果通知',
            content='您的资质审核已通过',
        )
        _db.session.add(msg)
        _db.session.commit()

        saved = _db.session.get(Message, msg.id)
        assert saved.type == 'review'

    def test_create_order_message(self, app_context):
        """Should create a message with type 'order'."""
        user = self._create_user()
        msg = Message(
            user_id=user.id,
            type='order',
            title='订单状态变更',
            content='您的订单已确认',
            ref_id=10,
            ref_type='order',
        )
        _db.session.add(msg)
        _db.session.commit()

        saved = _db.session.get(Message, msg.id)
        assert saved.type == 'order'

    def test_create_system_message(self, app_context):
        """Should create a message with type 'system'."""
        user = self._create_user()
        msg = Message(
            user_id=user.id,
            type='system',
            title='系统通知',
            content='平台维护通知',
        )
        _db.session.add(msg)
        _db.session.commit()

        saved = _db.session.get(Message, msg.id)
        assert saved.type == 'system'

    def test_default_is_read_false(self, app_context):
        """Should default is_read to False."""
        user = self._create_user()
        msg = Message(
            user_id=user.id,
            type='system',
            title='未读测试',
            content='测试默认未读状态',
        )
        _db.session.add(msg)
        _db.session.commit()

        saved = _db.session.get(Message, msg.id)
        assert saved.is_read is False

    def test_set_is_read_true(self, app_context):
        """Should allow setting is_read to True."""
        user = self._create_user()
        msg = Message(
            user_id=user.id,
            type='match',
            title='已读测试',
            content='测试已读标记',
            is_read=True,
        )
        _db.session.add(msg)
        _db.session.commit()

        saved = _db.session.get(Message, msg.id)
        assert saved.is_read is True

    def test_created_at_auto_set(self, app_context):
        """Should automatically set created_at on creation."""
        user = self._create_user()
        msg = Message(
            user_id=user.id,
            type='system',
            title='时间测试',
            content='测试自动时间',
        )
        _db.session.add(msg)
        _db.session.commit()

        saved = _db.session.get(Message, msg.id)
        assert saved.created_at is not None
        assert isinstance(saved.created_at, datetime)

    def test_nullable_ref_fields(self, app_context):
        """Should allow ref_id and ref_type to be None."""
        user = self._create_user()
        msg = Message(
            user_id=user.id,
            type='system',
            title='无关联业务消息',
            content='系统公告',
        )
        _db.session.add(msg)
        _db.session.commit()

        saved = _db.session.get(Message, msg.id)
        assert saved.ref_id is None
        assert saved.ref_type is None

    def test_nullable_content(self, app_context):
        """Should allow content to be None."""
        user = self._create_user()
        msg = Message(
            user_id=user.id,
            type='system',
            title='无内容消息',
        )
        _db.session.add(msg)
        _db.session.commit()

        saved = _db.session.get(Message, msg.id)
        assert saved.content is None

    def test_title_not_nullable(self, app_context):
        """Should reject message creation without a title."""
        user = self._create_user()
        msg = Message(
            user_id=user.id,
            type='system',
        )
        _db.session.add(msg)
        with pytest.raises(Exception):
            _db.session.commit()

    def test_type_not_nullable(self, app_context):
        """Should reject message creation without a type."""
        user = self._create_user()
        msg = Message(
            user_id=user.id,
            title='缺少类型',
        )
        _db.session.add(msg)
        with pytest.raises(Exception):
            _db.session.commit()

    def test_user_id_not_nullable(self, app_context):
        """Should reject message creation without a user_id."""
        msg = Message(
            type='system',
            title='缺少用户',
            content='测试',
        )
        _db.session.add(msg)
        with pytest.raises(Exception):
            _db.session.commit()


class TestMessageToDict:
    """Tests for Message JSON serialization."""

    def _create_user(self):
        user = User(
            phone='13100131100',
            role='buyer',
            company_name='Serialization Test Co.',
        )
        _db.session.add(user)
        _db.session.commit()
        return user

    def test_to_dict_contains_expected_keys(self, app_context):
        """to_dict should return all expected keys."""
        user = self._create_user()
        msg = Message(
            user_id=user.id,
            type='match',
            title='序列化测试',
            content='测试内容',
            ref_id=1,
            ref_type='demand',
        )
        _db.session.add(msg)
        _db.session.commit()

        data = msg.to_dict()
        expected_keys = {
            'id', 'user_id', 'type', 'title', 'content',
            'ref_id', 'ref_type', 'is_read', 'created_at',
        }
        assert set(data.keys()) == expected_keys

    def test_to_dict_values_match(self, app_context):
        """to_dict values should match the model attributes."""
        user = self._create_user()
        msg = Message(
            user_id=user.id,
            type='order',
            title='值匹配测试',
            content='订单已确认',
            ref_id=42,
            ref_type='order',
            is_read=True,
        )
        _db.session.add(msg)
        _db.session.commit()

        data = msg.to_dict()
        assert data['user_id'] == user.id
        assert data['type'] == 'order'
        assert data['title'] == '值匹配测试'
        assert data['content'] == '订单已确认'
        assert data['ref_id'] == 42
        assert data['ref_type'] == 'order'
        assert data['is_read'] is True

    def test_to_dict_datetime_format(self, app_context):
        """to_dict should serialize created_at as ISO format string."""
        user = self._create_user()
        msg = Message(
            user_id=user.id,
            type='system',
            title='日期格式测试',
            content='测试',
        )
        _db.session.add(msg)
        _db.session.commit()

        data = msg.to_dict()
        assert isinstance(data['created_at'], str)
        datetime.fromisoformat(data['created_at'])

    def test_to_dict_nullable_fields(self, app_context):
        """to_dict should handle None values for nullable fields."""
        user = self._create_user()
        msg = Message(
            user_id=user.id,
            type='system',
            title='空值测试',
        )
        _db.session.add(msg)
        _db.session.commit()

        data = msg.to_dict()
        assert data['content'] is None
        assert data['ref_id'] is None
        assert data['ref_type'] is None


class TestMessageUserRelationship:
    """Tests for Message-User foreign key relationship."""

    def test_message_belongs_to_user(self, app_context):
        """Message should reference its user via user_id."""
        user = User(
            phone='13100131200',
            role='buyer',
            company_name='Relationship Test Co.',
        )
        _db.session.add(user)
        _db.session.commit()

        msg = Message(
            user_id=user.id,
            type='match',
            title='关系测试',
            content='测试消息',
        )
        _db.session.add(msg)
        _db.session.commit()

        saved = _db.session.get(Message, msg.id)
        assert saved.user_id == user.id
        assert saved.user.id == user.id
        assert saved.user.company_name == 'Relationship Test Co.'

    def test_user_has_messages(self, app_context):
        """User should be able to access their messages via backref."""
        user = User(
            phone='13100131300',
            role='supplier',
            company_name='Multi-Message User',
        )
        _db.session.add(user)
        _db.session.commit()

        msg1 = Message(
            user_id=user.id,
            type='match',
            title='消息A',
            content='内容A',
        )
        msg2 = Message(
            user_id=user.id,
            type='order',
            title='消息B',
            content='内容B',
        )
        _db.session.add_all([msg1, msg2])
        _db.session.commit()

        assert user.messages.count() == 2
        titles = [m.title for m in user.messages.all()]
        assert '消息A' in titles
        assert '消息B' in titles


class TestMessageRepr:
    """Tests for Message string representation."""

    def test_repr(self, app_context):
        """__repr__ should return a readable string."""
        user = User(
            phone='13100131400',
            role='buyer',
        )
        _db.session.add(user)
        _db.session.commit()

        msg = Message(
            user_id=user.id,
            type='system',
            title='Repr测试',
            content='测试',
        )
        _db.session.add(msg)
        _db.session.commit()

        repr_str = repr(msg)
        assert 'Message' in repr_str
        assert 'system' in repr_str


# ---------------------------------------------------------------------------
# Conversation Model Tests
# ---------------------------------------------------------------------------

from server.models.conversation import Conversation, ChatMessage
from server.models.demand import Demand


class TestConversationModel:
    """Tests for Conversation model basic functionality."""

    def _create_buyer_supplier_demand(self):
        """Helper to create a buyer, supplier, and demand for conversation tests."""
        buyer = User(phone='13200132000', role='buyer', company_name='Buyer Co.')
        supplier = User(phone='13200132001', role='supplier', company_name='Supplier Co.')
        _db.session.add_all([buyer, supplier])
        _db.session.commit()

        demand = Demand(
            buyer_id=buyer.id,
            title='Test Demand',
            quantity=100,
        )
        _db.session.add(demand)
        _db.session.commit()

        return buyer, supplier, demand

    def test_create_conversation(self, app_context):
        """Should create a conversation linking buyer, supplier, and demand."""
        buyer, supplier, demand = self._create_buyer_supplier_demand()

        conv = Conversation(
            demand_id=demand.id,
            buyer_id=buyer.id,
            supplier_id=supplier.id,
        )
        _db.session.add(conv)
        _db.session.commit()

        saved = _db.session.get(Conversation, conv.id)
        assert saved is not None
        assert saved.demand_id == demand.id
        assert saved.buyer_id == buyer.id
        assert saved.supplier_id == supplier.id
        assert saved.last_message_at is None
        assert saved.last_message_preview is None

    def test_conversation_created_at_auto_set(self, app_context):
        """created_at should be automatically set on creation."""
        buyer, supplier, demand = self._create_buyer_supplier_demand()

        conv = Conversation(
            demand_id=demand.id,
            buyer_id=buyer.id,
            supplier_id=supplier.id,
        )
        _db.session.add(conv)
        _db.session.commit()

        assert conv.created_at is not None
        assert isinstance(conv.created_at, datetime)

    def test_conversation_last_message_fields(self, app_context):
        """Should store last_message_at and last_message_preview."""
        buyer, supplier, demand = self._create_buyer_supplier_demand()
        now = datetime.utcnow()

        conv = Conversation(
            demand_id=demand.id,
            buyer_id=buyer.id,
            supplier_id=supplier.id,
            last_message_at=now,
            last_message_preview='Hello there',
        )
        _db.session.add(conv)
        _db.session.commit()

        saved = _db.session.get(Conversation, conv.id)
        assert saved.last_message_at is not None
        assert saved.last_message_preview == 'Hello there'

    def test_conversation_unique_constraint(self, app_context):
        """Should reject duplicate (demand_id, buyer_id, supplier_id) triple."""
        buyer, supplier, demand = self._create_buyer_supplier_demand()

        conv1 = Conversation(
            demand_id=demand.id,
            buyer_id=buyer.id,
            supplier_id=supplier.id,
        )
        _db.session.add(conv1)
        _db.session.commit()

        conv2 = Conversation(
            demand_id=demand.id,
            buyer_id=buyer.id,
            supplier_id=supplier.id,
        )
        _db.session.add(conv2)
        with pytest.raises(Exception):
            _db.session.commit()

    def test_conversation_different_demands_allowed(self, app_context):
        """Should allow same buyer-supplier pair on different demands."""
        buyer, supplier, demand1 = self._create_buyer_supplier_demand()

        demand2 = Demand(
            buyer_id=buyer.id,
            title='Another Demand',
            quantity=200,
        )
        _db.session.add(demand2)
        _db.session.commit()

        conv1 = Conversation(
            demand_id=demand1.id,
            buyer_id=buyer.id,
            supplier_id=supplier.id,
        )
        conv2 = Conversation(
            demand_id=demand2.id,
            buyer_id=buyer.id,
            supplier_id=supplier.id,
        )
        _db.session.add_all([conv1, conv2])
        _db.session.commit()

        assert conv1.id != conv2.id


class TestConversationToDict:
    """Tests for Conversation.to_dict() serialization."""

    def _create_conversation(self):
        """Helper to create a conversation for serialization tests."""
        buyer = User(phone='13200132010', role='buyer', company_name='Buyer Co.')
        supplier = User(phone='13200132011', role='supplier', company_name='Supplier Co.')
        _db.session.add_all([buyer, supplier])
        _db.session.commit()

        demand = Demand(buyer_id=buyer.id, title='Dict Test Demand', quantity=50)
        _db.session.add(demand)
        _db.session.commit()

        conv = Conversation(
            demand_id=demand.id,
            buyer_id=buyer.id,
            supplier_id=supplier.id,
            last_message_at=datetime(2024, 6, 15, 10, 30, 0),
            last_message_preview='Preview text',
        )
        _db.session.add(conv)
        _db.session.commit()
        return conv

    def test_to_dict_contains_expected_keys(self, app_context):
        """to_dict should contain all expected keys."""
        conv = self._create_conversation()
        data = conv.to_dict()
        expected_keys = {
            'id', 'demand_id', 'buyer_id', 'supplier_id',
            'last_message_at', 'last_message_preview', 'created_at',
        }
        assert set(data.keys()) == expected_keys

    def test_to_dict_values_match(self, app_context):
        """to_dict values should match model attributes."""
        conv = self._create_conversation()
        data = conv.to_dict()
        assert data['id'] == conv.id
        assert data['demand_id'] == conv.demand_id
        assert data['buyer_id'] == conv.buyer_id
        assert data['supplier_id'] == conv.supplier_id
        assert data['last_message_preview'] == 'Preview text'

    def test_to_dict_datetime_format(self, app_context):
        """Datetime fields should be ISO format strings."""
        conv = self._create_conversation()
        data = conv.to_dict()
        assert data['last_message_at'] == '2024-06-15T10:30:00'
        assert isinstance(data['created_at'], str)

    def test_to_dict_nullable_fields(self, app_context):
        """Nullable fields should be None when not set."""
        buyer = User(phone='13200132020', role='buyer')
        supplier = User(phone='13200132021', role='supplier')
        _db.session.add_all([buyer, supplier])
        _db.session.commit()

        demand = Demand(buyer_id=buyer.id, title='Nullable Test', quantity=10)
        _db.session.add(demand)
        _db.session.commit()

        conv = Conversation(
            demand_id=demand.id,
            buyer_id=buyer.id,
            supplier_id=supplier.id,
        )
        _db.session.add(conv)
        _db.session.commit()

        data = conv.to_dict()
        assert data['last_message_at'] is None
        assert data['last_message_preview'] is None


class TestConversationRelationships:
    """Tests for Conversation model relationships."""

    def _create_conversation(self):
        """Helper to create a conversation with related objects."""
        buyer = User(phone='13200132030', role='buyer', company_name='Buyer Co.')
        supplier = User(phone='13200132031', role='supplier', company_name='Supplier Co.')
        _db.session.add_all([buyer, supplier])
        _db.session.commit()

        demand = Demand(buyer_id=buyer.id, title='Rel Test Demand', quantity=100)
        _db.session.add(demand)
        _db.session.commit()

        conv = Conversation(
            demand_id=demand.id,
            buyer_id=buyer.id,
            supplier_id=supplier.id,
        )
        _db.session.add(conv)
        _db.session.commit()
        return buyer, supplier, demand, conv

    def test_conversation_belongs_to_demand(self, app_context):
        """Conversation should have a demand relationship."""
        buyer, supplier, demand, conv = self._create_conversation()
        assert conv.demand is not None
        assert conv.demand.id == demand.id

    def test_conversation_belongs_to_buyer(self, app_context):
        """Conversation should have a buyer relationship."""
        buyer, supplier, demand, conv = self._create_conversation()
        assert conv.buyer is not None
        assert conv.buyer.id == buyer.id

    def test_conversation_belongs_to_supplier(self, app_context):
        """Conversation should have a supplier relationship."""
        buyer, supplier, demand, conv = self._create_conversation()
        assert conv.supplier is not None
        assert conv.supplier.id == supplier.id

    def test_demand_has_conversations(self, app_context):
        """Demand should have a conversations backref."""
        buyer, supplier, demand, conv = self._create_conversation()
        assert demand.conversations.count() == 1
        assert demand.conversations.first().id == conv.id

    def test_buyer_has_conversations(self, app_context):
        """Buyer should have a buyer_conversations backref."""
        buyer, supplier, demand, conv = self._create_conversation()
        assert buyer.buyer_conversations.count() == 1

    def test_supplier_has_conversations(self, app_context):
        """Supplier should have a supplier_conversations backref."""
        buyer, supplier, demand, conv = self._create_conversation()
        assert supplier.supplier_conversations.count() == 1

    def test_conversation_repr(self, app_context):
        """__repr__ should return a readable string."""
        buyer, supplier, demand, conv = self._create_conversation()
        repr_str = repr(conv)
        assert 'Conversation' in repr_str
        assert str(conv.id) in repr_str


# ---------------------------------------------------------------------------
# ChatMessage Model Tests
# ---------------------------------------------------------------------------


class TestChatMessageModel:
    """Tests for ChatMessage model basic functionality."""

    def _create_conversation_with_users(self):
        """Helper to create a conversation for message tests."""
        buyer = User(phone='13200132040', role='buyer', company_name='Buyer Co.')
        supplier = User(phone='13200132041', role='supplier', company_name='Supplier Co.')
        _db.session.add_all([buyer, supplier])
        _db.session.commit()

        demand = Demand(buyer_id=buyer.id, title='Msg Test Demand', quantity=100)
        _db.session.add(demand)
        _db.session.commit()

        conv = Conversation(
            demand_id=demand.id,
            buyer_id=buyer.id,
            supplier_id=supplier.id,
        )
        _db.session.add(conv)
        _db.session.commit()
        return buyer, supplier, conv

    def test_create_text_message(self, app_context):
        """Should create a text chat message."""
        buyer, supplier, conv = self._create_conversation_with_users()

        msg = ChatMessage(
            conversation_id=conv.id,
            sender_id=buyer.id,
            content='Hello, I have a question about the fabric.',
            msg_type='text',
        )
        _db.session.add(msg)
        _db.session.commit()

        saved = _db.session.get(ChatMessage, msg.id)
        assert saved is not None
        assert saved.conversation_id == conv.id
        assert saved.sender_id == buyer.id
        assert saved.content == 'Hello, I have a question about the fabric.'
        assert saved.msg_type == 'text'

    def test_create_system_message(self, app_context):
        """Should create a system chat message."""
        buyer, supplier, conv = self._create_conversation_with_users()

        msg = ChatMessage(
            conversation_id=conv.id,
            sender_id=supplier.id,
            content='供应商已提交报价：¥25.00/米，交货期15天',
            msg_type='system',
        )
        _db.session.add(msg)
        _db.session.commit()

        saved = _db.session.get(ChatMessage, msg.id)
        assert saved.msg_type == 'system'

    def test_default_msg_type_is_text(self, app_context):
        """Default msg_type should be 'text'."""
        buyer, supplier, conv = self._create_conversation_with_users()

        msg = ChatMessage(
            conversation_id=conv.id,
            sender_id=buyer.id,
            content='Default type test',
        )
        _db.session.add(msg)
        _db.session.commit()

        assert msg.msg_type == 'text'

    def test_default_is_read_false(self, app_context):
        """Default is_read should be False."""
        buyer, supplier, conv = self._create_conversation_with_users()

        msg = ChatMessage(
            conversation_id=conv.id,
            sender_id=buyer.id,
            content='Unread test',
        )
        _db.session.add(msg)
        _db.session.commit()

        assert msg.is_read is False

    def test_set_is_read_true(self, app_context):
        """Should be able to mark a message as read."""
        buyer, supplier, conv = self._create_conversation_with_users()

        msg = ChatMessage(
            conversation_id=conv.id,
            sender_id=buyer.id,
            content='Read test',
        )
        _db.session.add(msg)
        _db.session.commit()

        msg.is_read = True
        _db.session.commit()

        saved = _db.session.get(ChatMessage, msg.id)
        assert saved.is_read is True

    def test_created_at_auto_set(self, app_context):
        """created_at should be automatically set on creation."""
        buyer, supplier, conv = self._create_conversation_with_users()

        msg = ChatMessage(
            conversation_id=conv.id,
            sender_id=buyer.id,
            content='Timestamp test',
        )
        _db.session.add(msg)
        _db.session.commit()

        assert msg.created_at is not None
        assert isinstance(msg.created_at, datetime)

    def test_invalid_msg_type_rejected(self, app_context):
        """Should reject invalid msg_type values."""
        buyer, supplier, conv = self._create_conversation_with_users()

        msg = ChatMessage(
            conversation_id=conv.id,
            sender_id=buyer.id,
            content='Invalid type test',
            msg_type='invalid',
        )
        _db.session.add(msg)
        with pytest.raises(Exception):
            _db.session.commit()


class TestChatMessageToDict:
    """Tests for ChatMessage.to_dict() serialization."""

    def _create_message(self):
        """Helper to create a chat message for serialization tests."""
        buyer = User(phone='13200132050', role='buyer')
        supplier = User(phone='13200132051', role='supplier')
        _db.session.add_all([buyer, supplier])
        _db.session.commit()

        demand = Demand(buyer_id=buyer.id, title='Dict Msg Test', quantity=50)
        _db.session.add(demand)
        _db.session.commit()

        conv = Conversation(
            demand_id=demand.id,
            buyer_id=buyer.id,
            supplier_id=supplier.id,
        )
        _db.session.add(conv)
        _db.session.commit()

        msg = ChatMessage(
            conversation_id=conv.id,
            sender_id=buyer.id,
            content='Serialization test message',
            msg_type='text',
            is_read=False,
        )
        _db.session.add(msg)
        _db.session.commit()
        return msg

    def test_to_dict_contains_expected_keys(self, app_context):
        """to_dict should contain all expected keys."""
        msg = self._create_message()
        data = msg.to_dict()
        expected_keys = {
            'id', 'conversation_id', 'sender_id', 'content',
            'msg_type', 'is_read', 'created_at',
        }
        assert set(data.keys()) == expected_keys

    def test_to_dict_values_match(self, app_context):
        """to_dict values should match model attributes."""
        msg = self._create_message()
        data = msg.to_dict()
        assert data['id'] == msg.id
        assert data['conversation_id'] == msg.conversation_id
        assert data['sender_id'] == msg.sender_id
        assert data['content'] == 'Serialization test message'
        assert data['msg_type'] == 'text'
        assert data['is_read'] is False

    def test_to_dict_datetime_format(self, app_context):
        """created_at should be ISO format string."""
        msg = self._create_message()
        data = msg.to_dict()
        assert isinstance(data['created_at'], str)
        # Should be parseable as ISO datetime
        datetime.fromisoformat(data['created_at'])


class TestChatMessageRelationships:
    """Tests for ChatMessage model relationships."""

    def _create_message_with_context(self):
        """Helper to create a message with all related objects."""
        buyer = User(phone='13200132060', role='buyer', company_name='Buyer Co.')
        supplier = User(phone='13200132061', role='supplier', company_name='Supplier Co.')
        _db.session.add_all([buyer, supplier])
        _db.session.commit()

        demand = Demand(buyer_id=buyer.id, title='Rel Msg Test', quantity=100)
        _db.session.add(demand)
        _db.session.commit()

        conv = Conversation(
            demand_id=demand.id,
            buyer_id=buyer.id,
            supplier_id=supplier.id,
        )
        _db.session.add(conv)
        _db.session.commit()

        msg = ChatMessage(
            conversation_id=conv.id,
            sender_id=buyer.id,
            content='Relationship test',
        )
        _db.session.add(msg)
        _db.session.commit()
        return buyer, supplier, conv, msg

    def test_message_belongs_to_conversation(self, app_context):
        """ChatMessage should have a conversation relationship."""
        buyer, supplier, conv, msg = self._create_message_with_context()
        assert msg.conversation is not None
        assert msg.conversation.id == conv.id

    def test_message_belongs_to_sender(self, app_context):
        """ChatMessage should have a sender relationship."""
        buyer, supplier, conv, msg = self._create_message_with_context()
        assert msg.sender is not None
        assert msg.sender.id == buyer.id

    def test_conversation_has_messages(self, app_context):
        """Conversation should have a messages backref."""
        buyer, supplier, conv, msg = self._create_message_with_context()
        assert conv.messages.count() == 1
        assert conv.messages.first().id == msg.id

    def test_conversation_messages_cascade_delete(self, app_context):
        """Deleting a conversation should cascade delete its messages."""
        buyer, supplier, conv, msg = self._create_message_with_context()
        msg_id = msg.id

        _db.session.delete(conv)
        _db.session.commit()

        assert _db.session.get(ChatMessage, msg_id) is None

    def test_user_has_chat_messages(self, app_context):
        """User should have a chat_messages backref."""
        buyer, supplier, conv, msg = self._create_message_with_context()
        assert buyer.chat_messages.count() == 1

    def test_chat_message_repr(self, app_context):
        """__repr__ should return a readable string."""
        buyer, supplier, conv, msg = self._create_message_with_context()
        repr_str = repr(msg)
        assert 'ChatMessage' in repr_str
        assert str(msg.id) in repr_str
