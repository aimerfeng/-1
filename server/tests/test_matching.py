"""Unit tests for the supply-demand matching engine.

Tests the MatchingEngine class including calculate_score with various
demand/fabric combinations, match sorting, edge cases, and score
range validation.
"""

import pytest

from server.services.matching import MatchingEngine, _text_score, _numeric_range_score


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def engine():
    """Create a MatchingEngine with default AHP weights."""
    return MatchingEngine()


@pytest.fixture
def custom_engine():
    """Create a MatchingEngine with custom AHP weights."""
    return MatchingEngine(ahp_weights={
        'composition': 0.4,
        'weight': 0.15,
        'craft': 0.2,
        'price': 0.15,
        'width': 0.1,
    })


def make_demand(**kwargs):
    """Helper to create a demand dict with defaults."""
    defaults = {
        'id': 1,
        'composition': None,
        'weight_min': None,
        'weight_max': None,
        'width_min': None,
        'width_max': None,
        'craft': None,
        'color': None,
        'price_min': None,
        'price_max': None,
    }
    defaults.update(kwargs)
    return defaults


def make_fabric(**kwargs):
    """Helper to create a fabric dict with defaults."""
    defaults = {
        'id': 1,
        'composition': '100%棉',
        'weight': 200.0,
        'width': 150.0,
        'craft': '平纹',
        'color': '白色',
        'price': 25.0,
    }
    defaults.update(kwargs)
    return defaults


# ---------------------------------------------------------------------------
# Test _text_score helper
# ---------------------------------------------------------------------------

class TestTextScore:
    """Tests for the _text_score helper function."""

    def test_empty_demand_returns_100(self):
        assert _text_score(None, '100%棉') == 100.0
        assert _text_score('', '100%棉') == 100.0
        assert _text_score('  ', '100%棉') == 100.0

    def test_empty_fabric_returns_0(self):
        assert _text_score('棉', None) == 0.0
        assert _text_score('棉', '') == 0.0

    def test_exact_match_returns_100(self):
        assert _text_score('100%棉', '100%棉') == 100.0

    def test_substring_match_returns_100(self):
        assert _text_score('棉', '100%棉 涤纶混纺') == 100.0

    def test_fabric_substring_of_demand_returns_100(self):
        assert _text_score('100%棉', '棉') == 100.0

    def test_no_match_returns_0(self):
        assert _text_score('丝绸', '100%棉') == 0.0

    def test_partial_word_overlap(self):
        score = _text_score('cotton polyester', 'cotton silk')
        assert 50.0 <= score <= 80.0


# ---------------------------------------------------------------------------
# Test _numeric_range_score helper
# ---------------------------------------------------------------------------

class TestNumericRangeScore:
    """Tests for the _numeric_range_score helper function."""

    def test_no_constraint_returns_100(self):
        assert _numeric_range_score(200.0, None, None) == 100.0

    def test_within_range_returns_100(self):
        assert _numeric_range_score(200.0, 150.0, 250.0) == 100.0

    def test_at_boundary_returns_100(self):
        assert _numeric_range_score(150.0, 150.0, 250.0) == 100.0
        assert _numeric_range_score(250.0, 150.0, 250.0) == 100.0

    def test_only_min_within(self):
        assert _numeric_range_score(200.0, 150.0, None) == 100.0

    def test_only_max_within(self):
        assert _numeric_range_score(100.0, None, 150.0) == 100.0

    def test_below_min_within_tolerance(self):
        # min=100, 20% tolerance = 20, fabric=90 -> distance=10, score=50
        score = _numeric_range_score(90.0, 100.0, 200.0)
        assert 0.0 < score < 100.0

    def test_above_max_within_tolerance(self):
        # max=200, 20% tolerance = 40, fabric=220 -> distance=20, score=50
        score = _numeric_range_score(220.0, 100.0, 200.0)
        assert 0.0 < score < 100.0

    def test_far_below_min_returns_0(self):
        assert _numeric_range_score(50.0, 100.0, 200.0) == 0.0

    def test_far_above_max_returns_0(self):
        assert _numeric_range_score(300.0, 100.0, 200.0) == 0.0

    def test_fabric_none_with_constraint_returns_0(self):
        assert _numeric_range_score(None, 100.0, 200.0) == 0.0


# ---------------------------------------------------------------------------
# Test MatchingEngine.calculate_score
# ---------------------------------------------------------------------------

class TestCalculateScore:
    """Tests for MatchingEngine.calculate_score."""

    def test_perfect_match(self, engine):
        demand = make_demand(
            composition='100%棉',
            weight_min=180.0, weight_max=220.0,
            width_min=140.0, width_max=160.0,
            craft='平纹',
            price_min=20.0, price_max=30.0,
        )
        fabric = make_fabric(
            composition='100%棉',
            weight=200.0, width=150.0,
            craft='平纹', price=25.0,
        )
        score, detail = engine.calculate_score(demand, fabric)
        assert score == 100.0
        assert detail['composition'] == 100.0
        assert detail['weight'] == 100.0
        assert detail['width'] == 100.0
        assert detail['craft'] == 100.0
        assert detail['price'] == 100.0

    def test_no_constraints_returns_100(self, engine):
        demand = make_demand()  # All None
        fabric = make_fabric()
        score, detail = engine.calculate_score(demand, fabric)
        assert score == 100.0

    def test_no_match_returns_low_score(self, engine):
        demand = make_demand(
            composition='丝绸',
            weight_min=50.0, weight_max=80.0,
            width_min=80.0, width_max=100.0,
            craft='缎纹',
            price_min=100.0, price_max=200.0,
        )
        fabric = make_fabric(
            composition='100%棉',
            weight=200.0, width=150.0,
            craft='平纹', price=25.0,
        )
        score, detail = engine.calculate_score(demand, fabric)
        # Score is low but not necessarily 0 due to Chinese character-level
        # partial matching (e.g., '缎纹' and '平纹' share '纹')
        assert score < 30.0
        assert detail['weight'] == 0.0
        assert detail['width'] == 0.0
        assert detail['price'] == 0.0

    def test_partial_match(self, engine):
        demand = make_demand(
            composition='棉',  # Will match '100%棉'
            weight_min=180.0, weight_max=220.0,
            craft='平纹',
            price_min=20.0, price_max=30.0,
        )
        fabric = make_fabric(
            composition='100%棉',
            weight=200.0, width=150.0,
            craft='平纹', price=25.0,
        )
        score, detail = engine.calculate_score(demand, fabric)
        assert score > 50.0
        assert detail['composition'] == 100.0  # substring match
        assert detail['craft'] == 100.0

    def test_score_always_in_range(self, engine):
        """Score should always be between 0 and 100."""
        demand = make_demand(
            composition='棉',
            weight_min=100.0, weight_max=300.0,
            craft='平纹',
        )
        fabric = make_fabric()
        score, _ = engine.calculate_score(demand, fabric)
        assert 0.0 <= score <= 100.0

    def test_custom_weights(self, custom_engine):
        demand = make_demand(composition='棉', craft='平纹')
        fabric = make_fabric(composition='100%棉', craft='平纹')
        score, _ = custom_engine.calculate_score(demand, fabric)
        assert 0.0 <= score <= 100.0

    def test_returns_score_detail(self, engine):
        demand = make_demand(composition='棉')
        fabric = make_fabric()
        score, detail = engine.calculate_score(demand, fabric)
        assert 'composition' in detail
        assert 'weight' in detail
        assert 'width' in detail
        assert 'craft' in detail
        assert 'price' in detail


# ---------------------------------------------------------------------------
# Test MatchingEngine.match
# ---------------------------------------------------------------------------

class TestMatch:
    """Tests for MatchingEngine.match."""

    def test_returns_sorted_results(self, engine):
        demand = make_demand(
            composition='棉',
            weight_min=180.0, weight_max=220.0,
            craft='平纹',
        )
        fabrics = [
            make_fabric(id=1, composition='丝绸', weight=50.0, craft='缎纹'),
            make_fabric(id=2, composition='100%棉', weight=200.0, craft='平纹'),
            make_fabric(id=3, composition='棉涤混纺', weight=190.0, craft='平纹'),
        ]
        results = engine.match(demand, fabrics)

        assert len(results) == 3
        # Verify descending order
        for i in range(len(results) - 1):
            assert results[i]['score'] >= results[i + 1]['score']

    def test_result_structure(self, engine):
        demand = make_demand()
        fabrics = [make_fabric(id=42)]
        results = engine.match(demand, fabrics)

        assert len(results) == 1
        result = results[0]
        assert 'fabric_id' in result
        assert 'score' in result
        assert 'score_detail' in result
        assert result['fabric_id'] == 42

    def test_empty_fabrics_returns_empty(self, engine):
        demand = make_demand(composition='棉')
        results = engine.match(demand, [])
        assert results == []

    def test_empty_demand_all_score_100(self, engine):
        demand = make_demand()  # All None
        fabrics = [
            make_fabric(id=1),
            make_fabric(id=2, composition='丝绸'),
            make_fabric(id=3, composition='涤纶'),
        ]
        results = engine.match(demand, fabrics)
        for r in results:
            assert r['score'] == 100.0

    def test_all_scores_in_range(self, engine):
        demand = make_demand(
            composition='棉',
            weight_min=100.0, weight_max=300.0,
            craft='平纹',
            price_min=10.0, price_max=50.0,
        )
        fabrics = [
            make_fabric(id=i, weight=50.0 + i * 50, price=5.0 + i * 10)
            for i in range(10)
        ]
        results = engine.match(demand, fabrics)
        for r in results:
            assert 0.0 <= r['score'] <= 100.0

    def test_best_match_first(self, engine):
        demand = make_demand(
            composition='100%棉',
            weight_min=195.0, weight_max=205.0,
            craft='平纹',
            price_min=24.0, price_max=26.0,
            width_min=148.0, width_max=152.0,
        )
        perfect = make_fabric(
            id=1, composition='100%棉', weight=200.0,
            width=150.0, craft='平纹', price=25.0,
        )
        poor = make_fabric(
            id=2, composition='丝绸', weight=50.0,
            width=80.0, craft='缎纹', price=200.0,
        )
        results = engine.match(demand, [poor, perfect])
        assert results[0]['fabric_id'] == 1
        assert results[0]['score'] > results[1]['score']


# ---------------------------------------------------------------------------
# Test default weights initialization
# ---------------------------------------------------------------------------

class TestEngineInit:
    """Tests for MatchingEngine initialization."""

    def test_default_weights(self):
        engine = MatchingEngine()
        assert engine.weights == {
            'composition': 0.3,
            'weight': 0.2,
            'craft': 0.25,
            'price': 0.15,
            'width': 0.1,
        }

    def test_custom_weights(self):
        custom = {'composition': 0.5, 'weight': 0.1, 'craft': 0.2, 'price': 0.1, 'width': 0.1}
        engine = MatchingEngine(ahp_weights=custom)
        assert engine.weights == custom

    def test_weights_sum_to_one(self):
        engine = MatchingEngine()
        total = sum(engine.weights.values())
        assert abs(total - 1.0) < 1e-9


# ---------------------------------------------------------------------------
# Property-Based Tests (Hypothesis)
# ---------------------------------------------------------------------------

from hypothesis import given, settings, assume
from hypothesis import strategies as st


# ---------------------------------------------------------------------------
# Hypothesis strategies for generating random demands and fabrics
# ---------------------------------------------------------------------------

def demand_strategy():
    """Generate random demand dicts with realistic field ranges."""
    return st.fixed_dictionaries({
        'id': st.integers(min_value=1, max_value=10000),
        'composition': st.one_of(
            st.none(),
            st.sampled_from(['棉', '100%棉', '涤纶', '丝绸', '棉涤混纺', '亚麻', '羊毛', 'cotton', 'polyester']),
        ),
        'weight_min': st.one_of(st.none(), st.floats(min_value=10.0, max_value=500.0, allow_nan=False, allow_infinity=False)),
        'weight_max': st.one_of(st.none(), st.floats(min_value=10.0, max_value=500.0, allow_nan=False, allow_infinity=False)),
        'width_min': st.one_of(st.none(), st.floats(min_value=50.0, max_value=300.0, allow_nan=False, allow_infinity=False)),
        'width_max': st.one_of(st.none(), st.floats(min_value=50.0, max_value=300.0, allow_nan=False, allow_infinity=False)),
        'craft': st.one_of(
            st.none(),
            st.sampled_from(['平纹', '斜纹', '缎纹', '针织', '提花', '印花', 'plain', 'twill']),
        ),
        'color': st.one_of(st.none(), st.sampled_from(['白色', '黑色', '红色', '蓝色', '绿色'])),
        'price_min': st.one_of(st.none(), st.floats(min_value=1.0, max_value=500.0, allow_nan=False, allow_infinity=False)),
        'price_max': st.one_of(st.none(), st.floats(min_value=1.0, max_value=500.0, allow_nan=False, allow_infinity=False)),
    })


def fabric_strategy():
    """Generate random fabric dicts with realistic field ranges."""
    return st.fixed_dictionaries({
        'id': st.integers(min_value=1, max_value=10000),
        'composition': st.sampled_from(['100%棉', '涤纶', '丝绸', '棉涤混纺', '亚麻', '羊毛', 'cotton', 'polyester', '莫代尔']),
        'weight': st.floats(min_value=10.0, max_value=500.0, allow_nan=False, allow_infinity=False),
        'width': st.floats(min_value=50.0, max_value=300.0, allow_nan=False, allow_infinity=False),
        'craft': st.sampled_from(['平纹', '斜纹', '缎纹', '针织', '提花', '印花', 'plain', 'twill']),
        'color': st.sampled_from(['白色', '黑色', '红色', '蓝色', '绿色']),
        'price': st.floats(min_value=1.0, max_value=500.0, allow_nan=False, allow_infinity=False),
        'status': st.just('active'),
    })


# ---------------------------------------------------------------------------
# Property 12: 供需匹配评分范围与排序
# **Feature: textile-fabric-platform, Property 12: 供需匹配评分范围与排序**
# **Validates: Requirements 5.1, 5.2, 5.3**
#
# For any demand and set of fabrics, every matching score must be in [0, 100],
# and results must be sorted by score in descending order.
# ---------------------------------------------------------------------------

class TestProperty12ScoreRangeAndSorting:
    """Property 12: Score range [0-100] and descending sort order."""

    @given(
        demand=demand_strategy(),
        fabrics=st.lists(fabric_strategy(), min_size=0, max_size=20),
    )
    @settings(max_examples=150)
    def test_all_scores_in_0_100_range(self, demand, fabrics):
        """Every matching score must be within [0, 100]."""
        engine = MatchingEngine()
        results = engine.match(demand, fabrics)

        for result in results:
            assert 0.0 <= result['score'] <= 100.0, (
                f"Score {result['score']} out of range [0, 100] "
                f"for fabric_id={result['fabric_id']}"
            )

    @given(
        demand=demand_strategy(),
        fabrics=st.lists(fabric_strategy(), min_size=0, max_size=20),
    )
    @settings(max_examples=150)
    def test_results_sorted_descending_by_score(self, demand, fabrics):
        """Results must be sorted by score in descending order."""
        engine = MatchingEngine()
        results = engine.match(demand, fabrics)

        for i in range(len(results) - 1):
            assert results[i]['score'] >= results[i + 1]['score'], (
                f"Results not sorted: index {i} score={results[i]['score']} "
                f"< index {i+1} score={results[i+1]['score']}"
            )

    @given(
        demand=demand_strategy(),
        fabrics=st.lists(fabric_strategy(), min_size=0, max_size=20),
    )
    @settings(max_examples=150)
    def test_score_detail_dimensions_in_range(self, demand, fabrics):
        """Each dimension score in score_detail must also be in [0, 100]."""
        engine = MatchingEngine()
        results = engine.match(demand, fabrics)

        for result in results:
            for dim, dim_score in result['score_detail'].items():
                assert 0.0 <= dim_score <= 100.0, (
                    f"Dimension '{dim}' score {dim_score} out of range "
                    f"for fabric_id={result['fabric_id']}"
                )


# ---------------------------------------------------------------------------
# Property 13: 需求发布触发匹配
# **Feature: textile-fabric-platform, Property 13: 需求发布触发匹配**
# **Validates: Requirements 5.1, 5.6**
#
# For any new demand, if active fabrics exist, the matching process should
# be executed (results returned). For any new fabric, it should match
# against all open demands.
# ---------------------------------------------------------------------------

class TestProperty13MatchingTriggered:
    """Property 13: Matching is triggered for demands and fabrics."""

    @given(
        demand=demand_strategy(),
        fabrics=st.lists(fabric_strategy(), min_size=1, max_size=20),
    )
    @settings(max_examples=150)
    def test_match_returns_results_for_nonempty_fabrics(self, demand, fabrics):
        """When match() is called with non-empty fabrics, results are returned
        and the number of results equals the number of fabrics."""
        engine = MatchingEngine()
        results = engine.match(demand, fabrics)

        # Matching process was executed: results list is returned
        assert isinstance(results, list)
        # Number of results equals number of input fabrics
        assert len(results) == len(fabrics), (
            f"Expected {len(fabrics)} results, got {len(results)}"
        )

    @given(
        demand=demand_strategy(),
        fabrics=st.lists(fabric_strategy(), min_size=1, max_size=20),
    )
    @settings(max_examples=150)
    def test_each_fabric_has_a_result(self, demand, fabrics):
        """Every input fabric should appear in the results."""
        engine = MatchingEngine()
        results = engine.match(demand, fabrics)

        result_fabric_ids = {r['fabric_id'] for r in results}
        input_fabric_ids = {f['id'] for f in fabrics}
        assert result_fabric_ids == input_fabric_ids, (
            f"Mismatch: input IDs={input_fabric_ids}, result IDs={result_fabric_ids}"
        )

    @given(
        fabric=fabric_strategy(),
        demands=st.lists(demand_strategy(), min_size=1, max_size=10),
    )
    @settings(max_examples=150)
    def test_new_fabric_matches_against_all_demands(self, fabric, demands):
        """A new fabric should be matchable against all open demands.
        For each demand, calling match with the fabric should produce a result."""
        engine = MatchingEngine()

        for demand in demands:
            results = engine.match(demand, [fabric])
            # Matching was executed for this demand
            assert len(results) == 1
            assert results[0]['fabric_id'] == fabric['id']
            assert 0.0 <= results[0]['score'] <= 100.0

    @given(demand=demand_strategy())
    @settings(max_examples=150)
    def test_empty_fabrics_returns_empty_results(self, demand):
        """When no fabrics exist, match returns empty list (matching still executes)."""
        engine = MatchingEngine()
        results = engine.match(demand, [])
        assert results == []
