"""Unit tests for demand management routes.

Tests all demand endpoints:
- POST /api/demands (create demand, buyer only, triggers matching)
- GET /api/demands (list with role-based filtering)
- GET /api/demands/<id> (detail)
- GET /api/demands/<id>/matches (match results sorted by score)

Also tests:
- Matching trigger on fabric creation in POST /api/fabrics

Validates: Requirements 5.1, 5.4, 5.6
"""

import pytest
from flask_jwt_extended import create_access_token

from server.extensions import db as _db
from server.models.user import User
from server.models.fabric import Fabric
from server.models.demand import Demand, MatchResult


@pytest.fixture
def buyer_token(client):
    """Create a buyer user and return their JWT token and user ID."""
    user = User(phone='13800138001', role='buyer')
    user.set_password('testpass123')
    _db.session.add(user)
    _db.session.commit()
    token = create_access_token(identity=str(user.id))
    return token, user.id


@pytest.fixture
def supplier_token(client):
    """Create a supplier user and return their JWT token and user ID."""
    user = User(phone='13800138002', role='supplier')
    user.set_password('testpass123')
    _db.session.add(user)
    _db.session.commit()
    token = create_access_token(identity=str(user.id))
    return token, user.id


@pytest.fixture
def another_buyer_token(client):
    """Create another buyer user and return their JWT token and user ID."""
    user = User(phone='13800138003', role='buyer')
    user.set_password('testpass123')
    _db.session.add(user)
    _db.session.commit()
    token = create_access_token(identity=str(user.id))
    return token, user.id


@pytest.fixture
def sample_demand_data():
    """Return valid demand creation data."""
    return {
        'title': '采购纯棉面料',
        'composition': '棉',
        'weight_min': 150.0,
        'weight_max': 200.0,
        'width_min': 140.0,
        'width_max': 160.0,
        'craft': '平纹',
        'color': '白色',
        'price_min': 20.0,
        'price_max': 40.0,
        'quantity': 1000,
    }


@pytest.fixture
def sample_fabrics(client, supplier_token):
    """Create sample fabrics in the database for matching tests."""
    token, supplier_id = supplier_token
    fabrics_data = [
        {
            'name': '纯棉面料A',
            'composition': '100%棉',
            'weight': 180.0,
            'width': 150.0,
            'craft': '平纹',
            'color': '白色',
            'price': 25.5,
        },
        {
            'name': '涤纶面料B',
            'composition': '100%涤纶',
            'weight': 120.0,
            'width': 140.0,
            'craft': '斜纹',
            'color': '黑色',
            'price': 15.0,
        },
        {
            'name': '棉麻混纺C',
            'composition': '60%棉40%麻',
            'weight': 200.0,
            'width': 160.0,
            'craft': '平纹',
            'color': '米色',
            'price': 35.0,
        },
    ]
    created_ids = []
    for fd in fabrics_data:
        resp = client.post('/api/fabrics', json=fd,
                           headers=_auth_header(token))
        created_ids.append(resp.get_json()['id'])
    return created_ids


def _auth_header(token):
    """Build Authorization header."""
    return {'Authorization': f'Bearer {token}'}


class TestCreateDemand:
    """Tests for POST /api/demands."""

    def test_create_demand_success(self, client, buyer_token, sample_demand_data):
        token, _ = buyer_token
        resp = client.post('/api/demands', json=sample_demand_data,
                           headers=_auth_header(token))
        assert resp.status_code == 201
        data = resp.get_json()
        assert data['title'] == '采购纯棉面料'
        assert data['composition'] == '棉'
        assert data['weight_min'] == 150.0
        assert data['weight_max'] == 200.0
        assert data['status'] == 'open'
        assert data['id'] is not None

    def test_create_demand_missing_title(self, client, buyer_token):
        token, _ = buyer_token
        resp = client.post('/api/demands', json={
            'composition': '棉',
            'weight_min': 150.0,
        }, headers=_auth_header(token))
        assert resp.status_code == 400
        data = resp.get_json()
        assert 'title' in data.get('errors', {})

    def test_create_demand_empty_title(self, client, buyer_token):
        token, _ = buyer_token
        resp = client.post('/api/demands', json={
            'title': '   ',
            'composition': '棉',
        }, headers=_auth_header(token))
        assert resp.status_code == 400

    def test_create_demand_supplier_forbidden(self, client, supplier_token, sample_demand_data):
        token, _ = supplier_token
        resp = client.post('/api/demands', json=sample_demand_data,
                           headers=_auth_header(token))
        assert resp.status_code == 403

    def test_create_demand_no_auth(self, client, sample_demand_data):
        resp = client.post('/api/demands', json=sample_demand_data)
        assert resp.status_code == 401

    def test_create_demand_triggers_matching(self, client, buyer_token,
                                              sample_fabrics, sample_demand_data):
        token, _ = buyer_token
        resp = client.post('/api/demands', json=sample_demand_data,
                           headers=_auth_header(token))
        assert resp.status_code == 201
        data = resp.get_json()
        # Should have match_count indicating matching was triggered
        assert 'match_count' in data
        assert data['match_count'] == len(sample_fabrics)

    def test_create_demand_generates_match_results(self, client, buyer_token,
                                                     sample_fabrics, sample_demand_data):
        token, _ = buyer_token
        resp = client.post('/api/demands', json=sample_demand_data,
                           headers=_auth_header(token))
        demand_id = resp.get_json()['id']

        # Verify match results were created in the database
        matches_resp = client.get(f'/api/demands/{demand_id}/matches',
                                  headers=_auth_header(token))
        assert matches_resp.status_code == 200
        matches_data = matches_resp.get_json()
        assert matches_data['total'] == len(sample_fabrics)

    def test_create_demand_no_fabrics_no_matches(self, client, buyer_token, sample_demand_data):
        token, _ = buyer_token
        resp = client.post('/api/demands', json=sample_demand_data,
                           headers=_auth_header(token))
        assert resp.status_code == 201
        data = resp.get_json()
        assert data['match_count'] == 0

    def test_create_demand_minimal_data(self, client, buyer_token):
        """Only title is required."""
        token, _ = buyer_token
        resp = client.post('/api/demands', json={'title': '简单需求'},
                           headers=_auth_header(token))
        assert resp.status_code == 201
        data = resp.get_json()
        assert data['title'] == '简单需求'
        assert data['status'] == 'open'


class TestListDemands:
    """Tests for GET /api/demands."""

    def _create_demands(self, client, buyer_token, count=3):
        """Helper to create multiple demands."""
        token, _ = buyer_token
        for i in range(count):
            client.post('/api/demands', json={
                'title': f'需求{i + 1}',
                'composition': '棉',
            }, headers=_auth_header(token))

    def test_buyer_sees_own_demands(self, client, buyer_token, another_buyer_token):
        token, _ = buyer_token
        other_token, _ = another_buyer_token

        # Create demands for both buyers
        client.post('/api/demands', json={'title': '买家1需求'},
                    headers=_auth_header(token))
        client.post('/api/demands', json={'title': '买家2需求'},
                    headers=_auth_header(other_token))

        # Buyer 1 should only see their own demand
        resp = client.get('/api/demands', headers=_auth_header(token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['total'] == 1
        assert data['items'][0]['title'] == '买家1需求'

    def test_supplier_sees_open_demands(self, client, buyer_token, supplier_token):
        b_token, _ = buyer_token
        s_token, _ = supplier_token

        # Create demands as buyer
        client.post('/api/demands', json={'title': '开放需求'},
                    headers=_auth_header(b_token))

        # Supplier should see all open demands
        resp = client.get('/api/demands', headers=_auth_header(s_token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['total'] == 1
        assert data['items'][0]['title'] == '开放需求'

    def test_list_demands_pagination(self, client, buyer_token):
        self._create_demands(client, buyer_token, count=5)
        token, _ = buyer_token

        resp = client.get('/api/demands?page=1&per_page=2',
                          headers=_auth_header(token))
        data = resp.get_json()
        assert data['total'] == 5
        assert len(data['items']) == 2
        assert data['page'] == 1
        assert data['per_page'] == 2

    def test_list_demands_page_2(self, client, buyer_token):
        self._create_demands(client, buyer_token, count=5)
        token, _ = buyer_token

        resp = client.get('/api/demands?page=2&per_page=2',
                          headers=_auth_header(token))
        data = resp.get_json()
        assert data['total'] == 5
        assert len(data['items']) == 2

    def test_list_demands_no_auth(self, client):
        resp = client.get('/api/demands')
        assert resp.status_code == 401

    def test_list_demands_empty(self, client, buyer_token):
        token, _ = buyer_token
        resp = client.get('/api/demands', headers=_auth_header(token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['total'] == 0
        assert data['items'] == []


class TestGetDemand:
    """Tests for GET /api/demands/<id>."""

    def test_get_demand_success(self, client, buyer_token, sample_demand_data):
        token, _ = buyer_token
        create_resp = client.post('/api/demands', json=sample_demand_data,
                                  headers=_auth_header(token))
        demand_id = create_resp.get_json()['id']

        resp = client.get(f'/api/demands/{demand_id}',
                          headers=_auth_header(token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['id'] == demand_id
        assert data['title'] == '采购纯棉面料'

    def test_get_demand_not_found(self, client, buyer_token):
        token, _ = buyer_token
        resp = client.get('/api/demands/99999',
                          headers=_auth_header(token))
        assert resp.status_code == 404

    def test_get_demand_no_auth(self, client):
        resp = client.get('/api/demands/1')
        assert resp.status_code == 401

    def test_get_demand_supplier_can_view(self, client, buyer_token, supplier_token,
                                           sample_demand_data):
        """Suppliers should be able to view demand details."""
        b_token, _ = buyer_token
        s_token, _ = supplier_token

        create_resp = client.post('/api/demands', json=sample_demand_data,
                                  headers=_auth_header(b_token))
        demand_id = create_resp.get_json()['id']

        resp = client.get(f'/api/demands/{demand_id}',
                          headers=_auth_header(s_token))
        assert resp.status_code == 200


class TestGetDemandMatches:
    """Tests for GET /api/demands/<id>/matches."""

    def test_get_matches_success(self, client, buyer_token, sample_fabrics,
                                  sample_demand_data):
        token, _ = buyer_token
        create_resp = client.post('/api/demands', json=sample_demand_data,
                                  headers=_auth_header(token))
        demand_id = create_resp.get_json()['id']

        resp = client.get(f'/api/demands/{demand_id}/matches',
                          headers=_auth_header(token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['total'] == len(sample_fabrics)
        assert len(data['items']) == len(sample_fabrics)

    def test_matches_sorted_by_score_desc(self, client, buyer_token, sample_fabrics,
                                           sample_demand_data):
        token, _ = buyer_token
        create_resp = client.post('/api/demands', json=sample_demand_data,
                                  headers=_auth_header(token))
        demand_id = create_resp.get_json()['id']

        resp = client.get(f'/api/demands/{demand_id}/matches',
                          headers=_auth_header(token))
        data = resp.get_json()
        scores = [item['score'] for item in data['items']]
        assert scores == sorted(scores, reverse=True)

    def test_matches_include_fabric_info(self, client, buyer_token, sample_fabrics,
                                          sample_demand_data):
        token, _ = buyer_token
        create_resp = client.post('/api/demands', json=sample_demand_data,
                                  headers=_auth_header(token))
        demand_id = create_resp.get_json()['id']

        resp = client.get(f'/api/demands/{demand_id}/matches',
                          headers=_auth_header(token))
        data = resp.get_json()
        for item in data['items']:
            assert 'fabric' in item
            assert item['fabric'] is not None
            assert 'name' in item['fabric']
            assert 'composition' in item['fabric']

    def test_matches_demand_not_found(self, client, buyer_token):
        token, _ = buyer_token
        resp = client.get('/api/demands/99999/matches',
                          headers=_auth_header(token))
        assert resp.status_code == 404

    def test_matches_no_auth(self, client):
        resp = client.get('/api/demands/1/matches')
        assert resp.status_code == 401

    def test_matches_empty_when_no_fabrics(self, client, buyer_token, sample_demand_data):
        token, _ = buyer_token
        create_resp = client.post('/api/demands', json=sample_demand_data,
                                  headers=_auth_header(token))
        demand_id = create_resp.get_json()['id']

        resp = client.get(f'/api/demands/{demand_id}/matches',
                          headers=_auth_header(token))
        data = resp.get_json()
        assert data['total'] == 0
        assert data['items'] == []

    def test_match_scores_in_valid_range(self, client, buyer_token, sample_fabrics,
                                          sample_demand_data):
        token, _ = buyer_token
        create_resp = client.post('/api/demands', json=sample_demand_data,
                                  headers=_auth_header(token))
        demand_id = create_resp.get_json()['id']

        resp = client.get(f'/api/demands/{demand_id}/matches',
                          headers=_auth_header(token))
        data = resp.get_json()
        for item in data['items']:
            assert 0 <= item['score'] <= 100


class TestFabricCreationTriggersMatching:
    """Tests that creating a new fabric triggers matching with open demands."""

    def test_new_fabric_triggers_matching(self, client, buyer_token, supplier_token):
        """When a new fabric is created, it should match against open demands."""
        b_token, _ = buyer_token
        s_token, _ = supplier_token

        # First create a demand
        client.post('/api/demands', json={
            'title': '需要棉面料',
            'composition': '棉',
            'weight_min': 150.0,
            'weight_max': 200.0,
            'craft': '平纹',
        }, headers=_auth_header(b_token))

        # Now create a fabric - should trigger matching
        client.post('/api/fabrics', json={
            'name': '新棉面料',
            'composition': '100%棉',
            'weight': 180.0,
            'width': 150.0,
            'craft': '平纹',
            'price': 25.0,
        }, headers=_auth_header(s_token))

        # Check that match results were created for the demand
        demands_resp = client.get('/api/demands', headers=_auth_header(b_token))
        demand_id = demands_resp.get_json()['items'][0]['id']

        matches_resp = client.get(f'/api/demands/{demand_id}/matches',
                                  headers=_auth_header(b_token))
        matches_data = matches_resp.get_json()
        # Should have at least 1 match result from the fabric creation trigger
        assert matches_data['total'] >= 1

    def test_new_fabric_no_open_demands(self, client, supplier_token):
        """Creating a fabric when no open demands exist should not fail."""
        token, _ = supplier_token
        resp = client.post('/api/fabrics', json={
            'name': '新面料',
            'composition': '100%棉',
            'weight': 180.0,
            'width': 150.0,
            'craft': '平纹',
            'price': 25.0,
        }, headers=_auth_header(token))
        assert resp.status_code == 201
