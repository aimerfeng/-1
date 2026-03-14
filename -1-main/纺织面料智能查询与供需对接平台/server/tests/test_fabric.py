"""Property-based tests for fabric validation module.

**Feature: textile-fabric-platform**
**Validates: Requirements 3.1, 3.2, 3.5**

Uses Hypothesis to verify:
- Property 6: Fabric parameter standardized validation
- Property 8: Fabric field completeness
"""

import threading

from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

from server.extensions import db as _db
from server.models.fabric import Fabric, validate_fabric
from server.models.user import User


# Thread-safe counter for generating unique phone numbers within a test run
_phone_counter = 0
_phone_lock = threading.Lock()


def _unique_phone():
    """Generate a unique valid Chinese phone number for testing."""
    global _phone_counter
    with _phone_lock:
        _phone_counter += 1
        counter = _phone_counter
    # Format: 139XXXXXXXX where X is zero-padded counter
    return f'139{counter:08d}'


# Required fields for validate_fabric
REQUIRED_FIELDS = ['composition', 'weight', 'width', 'craft', 'price']

# All expected fields in to_dict() output for fabric records
EXPECTED_FABRIC_FIELDS = [
    'composition', 'weight', 'width', 'craft', 'color',
    'price', 'min_order_qty', 'delivery_days',
]


# Strategy for generating valid fabric data dictionaries
def valid_fabric_data_strategy():
    """Generate a dictionary with all required fabric fields having valid values."""
    return st.fixed_dictionaries({
        'composition': st.text(
            alphabet=st.characters(whitelist_categories=('L', 'N', 'Zs')),
            min_size=1,
            max_size=50,
        ).filter(lambda s: s.strip()),
        'weight': st.floats(min_value=0.01, max_value=10000.0, allow_nan=False, allow_infinity=False),
        'width': st.floats(min_value=0.01, max_value=10000.0, allow_nan=False, allow_infinity=False),
        'craft': st.text(
            alphabet=st.characters(whitelist_categories=('L', 'N', 'Zs')),
            min_size=1,
            max_size=50,
        ).filter(lambda s: s.strip()),
        'price': st.floats(min_value=0.01, max_value=100000.0, allow_nan=False, allow_infinity=False),
    })


# ===========================================================================
# Property 6: 面料参数标准化校验
# ===========================================================================


class TestFabricValidationProperty:
    """Property 6: 面料参数标准化校验

    **Feature: textile-fabric-platform, Property 6: 面料参数标准化校验**
    **Validates: Requirements 3.1, 3.2**

    For any fabric submission data, if any required field (composition,
    weight, width, craft, price) is missing, validation should fail and
    return the missing field name; if all required fields are present
    and correctly formatted, validation should pass.
    """

    @given(data=valid_fabric_data_strategy())
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_all_required_fields_present_passes_validation(self, data):
        """When all required fields are present and valid, validate_fabric returns (True, {}).

        **Validates: Requirements 3.1**
        """
        is_valid, errors = validate_fabric(data)
        assert is_valid is True, f"Expected validation to pass but got errors: {errors}"
        assert errors == {}, f"Expected no errors but got: {errors}"

    @given(
        data=valid_fabric_data_strategy(),
        field_to_remove=st.sampled_from(REQUIRED_FIELDS),
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_missing_required_field_fails_validation(self, data, field_to_remove):
        """When any required field is missing, validate_fabric returns (False, {field: error_msg}).

        **Validates: Requirements 3.2**
        """
        # Remove the selected required field
        data_copy = dict(data)
        del data_copy[field_to_remove]

        is_valid, errors = validate_fabric(data_copy)
        assert is_valid is False, (
            f"Expected validation to fail when '{field_to_remove}' is missing, "
            f"but it passed"
        )
        assert field_to_remove in errors, (
            f"Expected '{field_to_remove}' in errors dict but got: {errors}"
        )


# ===========================================================================
# Property 8: 面料字段完整性
# ===========================================================================


class TestFabricFieldCompletenessProperty:
    """Property 8: 面料字段完整性

    **Feature: textile-fabric-platform, Property 8: 面料字段完整性**
    **Validates: Requirements 3.5**

    For any fabric record, to_dict() should contain all expected fields:
    composition, weight, width, craft, color, price, min_order_qty,
    delivery_days.
    """

    @given(
        data=st.fixed_dictionaries({
            'name': st.text(
                alphabet=st.characters(whitelist_categories=('L', 'N')),
                min_size=1,
                max_size=50,
            ),
            'composition': st.text(
                alphabet=st.characters(whitelist_categories=('L', 'N', 'Zs')),
                min_size=1,
                max_size=50,
            ).filter(lambda s: s.strip()),
            'weight': st.floats(min_value=0.01, max_value=10000.0, allow_nan=False, allow_infinity=False),
            'width': st.floats(min_value=0.01, max_value=10000.0, allow_nan=False, allow_infinity=False),
            'craft': st.text(
                alphabet=st.characters(whitelist_categories=('L', 'N', 'Zs')),
                min_size=1,
                max_size=50,
            ).filter(lambda s: s.strip()),
            'color': st.one_of(
                st.none(),
                st.text(
                    alphabet=st.characters(whitelist_categories=('L', 'N')),
                    min_size=1,
                    max_size=30,
                ),
            ),
            'price': st.floats(min_value=0.01, max_value=100000.0, allow_nan=False, allow_infinity=False),
            'min_order_qty': st.one_of(st.none(), st.integers(min_value=1, max_value=100000)),
            'delivery_days': st.one_of(st.none(), st.integers(min_value=1, max_value=365)),
        }),
    )
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_fabric_to_dict_contains_all_fields(self, app_context, data):
        """Every fabric record's to_dict() should contain all expected fields.

        **Validates: Requirements 3.5**
        """
        # Create a supplier user for the fabric
        phone = _unique_phone()
        supplier = User(phone=phone, role='supplier')
        _db.session.add(supplier)
        _db.session.commit()
        supplier_id = supplier.id

        # Create a fabric record with the generated data
        fabric = Fabric(
            supplier_id=supplier_id,
            name=data['name'],
            composition=data['composition'],
            weight=data['weight'],
            width=data['width'],
            craft=data['craft'],
            color=data['color'],
            price=data['price'],
            min_order_qty=data['min_order_qty'],
            delivery_days=data['delivery_days'],
        )
        _db.session.add(fabric)
        _db.session.commit()

        # Retrieve and verify to_dict() contains all expected fields
        saved_fabric = _db.session.get(Fabric, fabric.id)
        fabric_dict = saved_fabric.to_dict()

        for field in EXPECTED_FABRIC_FIELDS:
            assert field in fabric_dict, (
                f"Expected field '{field}' in fabric to_dict() output, "
                f"but it was missing. Keys present: {list(fabric_dict.keys())}"
            )

        # Clean up
        _db.session.delete(saved_fabric)
        _db.session.delete(supplier)
        _db.session.commit()


# ---------------------------------------------------------------------------
# Shared imports and helpers for Properties 7, 9, 10, 11
# ---------------------------------------------------------------------------

from flask_jwt_extended import create_access_token


def _create_supplier_and_token(db_session):
    """Create a supplier user and return (user, access_token).

    Uses thread-safe unique phone generation.
    """
    phone = _unique_phone()
    supplier = User(phone=phone, role='supplier')
    db_session.add(supplier)
    db_session.commit()
    token = create_access_token(identity=str(supplier.id))
    return supplier, token


def _fabric_create_data():
    """Hypothesis strategy for generating valid fabric creation payloads."""
    return st.fixed_dictionaries({
        'name': st.text(
            alphabet=st.characters(whitelist_categories=('L', 'N')),
            min_size=1,
            max_size=50,
        ),
        'composition': st.text(
            alphabet=st.characters(whitelist_categories=('L', 'N', 'Zs')),
            min_size=1,
            max_size=50,
        ).filter(lambda s: s.strip()),
        'weight': st.floats(min_value=1.0, max_value=5000.0, allow_nan=False, allow_infinity=False),
        'width': st.floats(min_value=1.0, max_value=5000.0, allow_nan=False, allow_infinity=False),
        'craft': st.text(
            alphabet=st.characters(whitelist_categories=('L', 'N', 'Zs')),
            min_size=1,
            max_size=50,
        ).filter(lambda s: s.strip()),
        'color': st.one_of(
            st.none(),
            st.text(
                alphabet=st.characters(whitelist_categories=('L', 'N')),
                min_size=1,
                max_size=30,
            ),
        ),
        'price': st.floats(min_value=0.01, max_value=50000.0, allow_nan=False, allow_infinity=False),
        'min_order_qty': st.one_of(st.none(), st.integers(min_value=1, max_value=100000)),
        'delivery_days': st.one_of(st.none(), st.integers(min_value=1, max_value=365)),
    })


# ===========================================================================
# Property 7: 面料数据持久化往返
# ===========================================================================


class TestFabricPersistenceRoundTripProperty:
    """Property 7: 面料数据持久化往返

    **Feature: textile-fabric-platform, Property 7: 面料数据持久化往返**
    **Validates: Requirements 3.3, 3.6**

    For any valid fabric data, creating a fabric via POST and then
    retrieving it via GET should return consistent data. After updating
    via PUT, a subsequent GET should return the updated data.
    """

    @given(
        create_data=_fabric_create_data(),
        update_data=_fabric_create_data(),
    )
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_create_then_get_returns_consistent_data(self, client, create_data, update_data):
        """Create a fabric via POST, GET by ID, verify fields match.
        Then PUT updated data, GET again, verify updated fields match.

        **Validates: Requirements 3.3, 3.6**
        """
        # --- Setup: create supplier and token ---
        from server.extensions import db as test_db
        supplier, token = _create_supplier_and_token(test_db.session)
        auth_header = {'Authorization': f'Bearer {token}'}

        # --- Step 1: Create fabric via POST ---
        resp = client.post(
            '/api/fabrics',
            json=create_data,
            headers=auth_header,
        )
        assert resp.status_code == 201, f"Create failed: {resp.get_json()}"
        created = resp.get_json()
        fabric_id = created['id']

        # --- Step 2: GET by ID and verify consistency ---
        resp = client.get(f'/api/fabrics/{fabric_id}')
        assert resp.status_code == 200
        fetched = resp.get_json()

        # Verify all submitted fields match the fetched record
        assert fetched['composition'] == create_data['composition']
        assert fetched['craft'] == create_data['craft']
        assert fetched['name'] == create_data['name']
        assert fetched['color'] == create_data.get('color')
        assert fetched['min_order_qty'] == create_data.get('min_order_qty')
        assert fetched['delivery_days'] == create_data.get('delivery_days')
        # Float comparison with tolerance for weight/width/price
        assert abs(fetched['weight'] - create_data['weight']) < 1e-4
        assert abs(fetched['width'] - create_data['width']) < 1e-4
        assert abs(fetched['price'] - create_data['price']) < 1e-4

        # --- Step 3: Update fabric via PUT ---
        resp = client.put(
            f'/api/fabrics/{fabric_id}',
            json=update_data,
            headers=auth_header,
        )
        assert resp.status_code == 200, f"Update failed: {resp.get_json()}"

        # --- Step 4: GET again and verify updated data ---
        resp = client.get(f'/api/fabrics/{fabric_id}')
        assert resp.status_code == 200
        updated_fetched = resp.get_json()

        assert updated_fetched['composition'] == update_data['composition']
        assert updated_fetched['craft'] == update_data['craft']
        assert updated_fetched['name'] == update_data['name']
        assert updated_fetched['color'] == update_data.get('color')
        assert updated_fetched['min_order_qty'] == update_data.get('min_order_qty')
        assert updated_fetched['delivery_days'] == update_data.get('delivery_days')
        assert abs(updated_fetched['weight'] - update_data['weight']) < 1e-4
        assert abs(updated_fetched['width'] - update_data['width']) < 1e-4
        assert abs(updated_fetched['price'] - update_data['price']) < 1e-4

        # --- Cleanup ---
        fabric = test_db.session.get(Fabric, fabric_id)
        if fabric:
            test_db.session.delete(fabric)
        test_db.session.delete(supplier)
        test_db.session.commit()


# ===========================================================================
# Property 9: 面料多条件筛选正确性
# ===========================================================================


class TestFabricFilterCorrectnessProperty:
    """Property 9: 面料多条件筛选正确性

    **Feature: textile-fabric-platform, Property 9: 面料多条件筛选正确性**
    **Validates: Requirements 4.1**

    For any combination of query conditions (composition, craft, price
    range, weight range), every returned fabric record satisfies ALL
    specified filter conditions.
    """

    @given(
        fabrics_data=st.lists(
            _fabric_create_data(),
            min_size=3,
            max_size=8,
        ),
        filter_composition=st.one_of(st.none(), st.just('A'), st.just('B')),
        filter_craft=st.one_of(st.none(), st.just('X'), st.just('Y')),
        filter_price_min=st.one_of(st.none(), st.floats(min_value=0.01, max_value=25000.0, allow_nan=False, allow_infinity=False)),
        filter_price_max=st.one_of(st.none(), st.floats(min_value=0.01, max_value=50000.0, allow_nan=False, allow_infinity=False)),
        filter_weight_min=st.one_of(st.none(), st.floats(min_value=1.0, max_value=2500.0, allow_nan=False, allow_infinity=False)),
        filter_weight_max=st.one_of(st.none(), st.floats(min_value=1.0, max_value=5000.0, allow_nan=False, allow_infinity=False)),
    )
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_every_returned_fabric_satisfies_all_filters(
        self, client, fabrics_data,
        filter_composition, filter_craft,
        filter_price_min, filter_price_max,
        filter_weight_min, filter_weight_max,
    ):
        """Create multiple fabrics, query with random filters, verify each
        returned fabric satisfies ALL specified conditions.

        **Validates: Requirements 4.1**
        """
        from server.extensions import db as test_db

        supplier, token = _create_supplier_and_token(test_db.session)
        auth_header = {'Authorization': f'Bearer {token}'}

        # Create fabrics
        created_ids = []
        for fdata in fabrics_data:
            resp = client.post('/api/fabrics', json=fdata, headers=auth_header)
            assert resp.status_code == 201
            created_ids.append(resp.get_json()['id'])

        # Build query params
        params = {'per_page': 100}
        if filter_composition is not None:
            params['composition'] = filter_composition
        if filter_craft is not None:
            params['craft'] = filter_craft
        if filter_price_min is not None:
            params['price_min'] = filter_price_min
        if filter_price_max is not None:
            params['price_max'] = filter_price_max
        if filter_weight_min is not None:
            params['weight_min'] = filter_weight_min
        if filter_weight_max is not None:
            params['weight_max'] = filter_weight_max

        resp = client.get('/api/fabrics', query_string=params)
        assert resp.status_code == 200
        result = resp.get_json()

        # Verify every returned fabric satisfies ALL filter conditions
        for item in result['items']:
            if filter_composition is not None:
                assert filter_composition.lower() in item['composition'].lower(), (
                    f"Fabric {item['id']} composition '{item['composition']}' "
                    f"does not contain filter '{filter_composition}'"
                )
            if filter_craft is not None:
                assert filter_craft.lower() in item['craft'].lower(), (
                    f"Fabric {item['id']} craft '{item['craft']}' "
                    f"does not contain filter '{filter_craft}'"
                )
            if filter_price_min is not None:
                assert item['price'] >= filter_price_min, (
                    f"Fabric {item['id']} price {item['price']} < price_min {filter_price_min}"
                )
            if filter_price_max is not None:
                assert item['price'] <= filter_price_max, (
                    f"Fabric {item['id']} price {item['price']} > price_max {filter_price_max}"
                )
            if filter_weight_min is not None:
                assert item['weight'] >= filter_weight_min, (
                    f"Fabric {item['id']} weight {item['weight']} < weight_min {filter_weight_min}"
                )
            if filter_weight_max is not None:
                assert item['weight'] <= filter_weight_max, (
                    f"Fabric {item['id']} weight {item['weight']} > weight_max {filter_weight_max}"
                )

        # Cleanup
        for fid in created_ids:
            fabric = test_db.session.get(Fabric, fid)
            if fabric:
                test_db.session.delete(fabric)
        test_db.session.delete(supplier)
        test_db.session.commit()


# ===========================================================================
# Property 10: 面料对比数据完整性
# ===========================================================================


class TestFabricCompareCompletenessProperty:
    """Property 10: 面料对比数据完整性

    **Feature: textile-fabric-platform, Property 10: 面料对比数据完整性**
    **Validates: Requirements 4.5**

    For any set of fabric IDs, the compare endpoint result contains
    each fabric's full parameter fields, and the count matches the
    number of requested IDs.
    """

    COMPARE_REQUIRED_FIELDS = [
        'id', 'supplier_id', 'name', 'composition', 'weight', 'width',
        'craft', 'color', 'price', 'min_order_qty', 'delivery_days',
    ]

    @given(
        fabrics_data=st.lists(
            _fabric_create_data(),
            min_size=1,
            max_size=6,
        ),
        # Select a random subset of indices to compare
        data=st.data(),
    )
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_compare_returns_complete_data_for_all_ids(self, client, fabrics_data, data):
        """Create multiple fabrics, compare a subset, verify result count
        and field completeness.

        **Validates: Requirements 4.5**
        """
        from server.extensions import db as test_db

        supplier, token = _create_supplier_and_token(test_db.session)
        auth_header = {'Authorization': f'Bearer {token}'}

        # Create fabrics
        created_ids = []
        for fdata in fabrics_data:
            resp = client.post('/api/fabrics', json=fdata, headers=auth_header)
            assert resp.status_code == 201
            created_ids.append(resp.get_json()['id'])

        # Draw a non-empty subset of IDs to compare
        subset_indices = data.draw(
            st.lists(
                st.sampled_from(range(len(created_ids))),
                min_size=1,
                max_size=len(created_ids),
                unique=True,
            )
        )
        compare_ids = [created_ids[i] for i in subset_indices]
        ids_param = ','.join(str(i) for i in compare_ids)

        resp = client.get(f'/api/fabrics/compare?ids={ids_param}')
        assert resp.status_code == 200
        result = resp.get_json()

        # Verify count matches requested IDs
        assert result['total'] == len(compare_ids), (
            f"Expected {len(compare_ids)} fabrics in compare result, got {result['total']}"
        )
        assert len(result['items']) == len(compare_ids), (
            f"Expected {len(compare_ids)} items, got {len(result['items'])}"
        )

        # Verify each fabric has all required parameter fields
        for item in result['items']:
            for field in self.COMPARE_REQUIRED_FIELDS:
                assert field in item, (
                    f"Fabric {item.get('id')} missing field '{field}' in compare result. "
                    f"Keys present: {list(item.keys())}"
                )

        # Verify all requested IDs are present in the result
        returned_ids = {item['id'] for item in result['items']}
        for cid in compare_ids:
            assert cid in returned_ids, (
                f"Requested fabric ID {cid} not found in compare result"
            )

        # Cleanup
        for fid in created_ids:
            fabric = test_db.session.get(Fabric, fid)
            if fabric:
                test_db.session.delete(fabric)
        test_db.session.delete(supplier)
        test_db.session.commit()


# ===========================================================================
# Property 11: 分页查询正确性
# ===========================================================================


class TestFabricPaginationCorrectnessProperty:
    """Property 11: 分页查询正确性

    **Feature: textile-fabric-platform, Property 11: 分页查询正确性**
    **Validates: Requirements 4.6**

    For any pagination query (page, per_page), the number of returned
    items does not exceed per_page, and the total field correctly
    reflects the total count of matching records.
    """

    @given(
        num_fabrics=st.integers(min_value=1, max_value=15),
        page=st.integers(min_value=1, max_value=10),
        per_page=st.integers(min_value=1, max_value=10),
    )
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_pagination_respects_per_page_and_total(self, client, num_fabrics, page, per_page):
        """Create N fabrics, query with random page/per_page, verify
        len(items) <= per_page and total == N.

        **Validates: Requirements 4.6**
        """
        from server.extensions import db as test_db

        supplier, token = _create_supplier_and_token(test_db.session)
        auth_header = {'Authorization': f'Bearer {token}'}

        # Create fabrics with deterministic data to avoid Hypothesis overhead
        created_ids = []
        for i in range(num_fabrics):
            fabric_data = {
                'name': f'PaginationFabric{i}',
                'composition': 'PaginationTestComp',
                'weight': 100.0 + i,
                'width': 150.0,
                'craft': 'PaginationTestCraft',
                'price': 10.0 + i,
            }
            resp = client.post('/api/fabrics', json=fabric_data, headers=auth_header)
            assert resp.status_code == 201
            created_ids.append(resp.get_json()['id'])

        # Query with specific composition to isolate our test fabrics
        resp = client.get('/api/fabrics', query_string={
            'composition': 'PaginationTestComp',
            'page': page,
            'per_page': per_page,
        })
        assert resp.status_code == 200
        result = resp.get_json()

        # Verify: items count does not exceed per_page
        assert len(result['items']) <= per_page, (
            f"Returned {len(result['items'])} items but per_page is {per_page}"
        )

        # Verify: total reflects the actual count of matching records
        assert result['total'] == num_fabrics, (
            f"Expected total={num_fabrics} but got total={result['total']}"
        )

        # Verify: items count is correct for the given page
        expected_items = max(0, min(per_page, num_fabrics - (page - 1) * per_page))
        assert len(result['items']) == expected_items, (
            f"Expected {expected_items} items on page {page} "
            f"(total={num_fabrics}, per_page={per_page}), "
            f"got {len(result['items'])}"
        )

        # Cleanup
        for fid in created_ids:
            fabric = test_db.session.get(Fabric, fid)
            if fabric:
                test_db.session.delete(fabric)
        test_db.session.delete(supplier)
        test_db.session.commit()
