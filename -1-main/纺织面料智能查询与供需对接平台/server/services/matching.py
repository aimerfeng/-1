"""Supply-demand matching engine.

Implements the MatchingEngine class that calculates matching scores
between buyer demands and supplier fabrics using keyword matching,
numeric range comparison, and AHP (Analytic Hierarchy Process)
weighted aggregation. This is a pure computation class with no
database operations.
"""


def _get_attr(obj, key, default=None):
    """Get an attribute from an object or dict.

    Supports both model objects (attribute access) and plain dicts
    (key access), making the engine work with either.

    Args:
        obj: A model object or dictionary.
        key: The attribute/key name to retrieve.
        default: Default value if the attribute/key is not found.

    Returns:
        The value of the attribute/key, or default if not found.
    """
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _text_score(demand_value, fabric_value):
    """Calculate text similarity score between demand and fabric fields.

    Scoring rules:
    - If demand field is empty/None, score 100 (no constraint).
    - If fabric field contains demand text (substring match), score 100.
    - If partial overlap (any word matches), score proportionally (50-80).
    - Otherwise score 0.

    Args:
        demand_value: The demand's text requirement (str or None).
        fabric_value: The fabric's text value (str or None).

    Returns:
        A float score between 0 and 100.
    """
    if not demand_value or not str(demand_value).strip():
        return 100.0

    demand_str = str(demand_value).strip().lower()
    fabric_str = str(fabric_value).strip().lower() if fabric_value else ""

    if not fabric_str:
        return 0.0

    # Full substring match
    if demand_str in fabric_str or fabric_str in demand_str:
        return 100.0

    # Partial word overlap
    demand_words = set(demand_str.split())
    fabric_words = set(fabric_str.split())

    if not demand_words:
        return 100.0

    common = demand_words & fabric_words
    if common:
        # Score proportionally between 50 and 80 based on overlap ratio
        ratio = len(common) / len(demand_words)
        return 50.0 + 30.0 * ratio

    # Check character-level partial matching for Chinese text
    # (Chinese text often doesn't have spaces between words)
    demand_chars = set(demand_str.replace(" ", ""))
    fabric_chars = set(fabric_str.replace(" ", ""))

    if demand_chars and fabric_chars:
        common_chars = demand_chars & fabric_chars
        if common_chars:
            ratio = len(common_chars) / len(demand_chars)
            if ratio >= 0.5:
                return 50.0 + 30.0 * ratio

    return 0.0


def _numeric_range_score(fabric_value, range_min, range_max):
    """Calculate numeric range match score.

    Scoring rules:
    - If demand range is not specified (both min and max are None), score 100.
    - If fabric value is within demand range, score 100.
    - If fabric value is close to range (within 20%), score proportionally.
    - If fabric value is far from range, score 0.

    Args:
        fabric_value: The fabric's numeric value (float or None).
        range_min: The demand's minimum value (float or None).
        range_max: The demand's maximum value (float or None).

    Returns:
        A float score between 0 and 100.
    """
    # No constraint specified
    if range_min is None and range_max is None:
        return 100.0

    # Fabric has no value but demand has a constraint
    if fabric_value is None:
        return 0.0

    val = float(fabric_value)

    # Determine effective range
    lo = float(range_min) if range_min is not None else None
    hi = float(range_max) if range_max is not None else None

    # Within range
    in_range = True
    if lo is not None and val < lo:
        in_range = False
    if hi is not None and val > hi:
        in_range = False

    if in_range:
        return 100.0

    # Calculate distance from range and 20% tolerance
    if lo is not None and val < lo:
        # Below minimum
        tolerance = abs(lo) * 0.2 if lo != 0 else 1.0
        distance = lo - val
        if distance <= tolerance and tolerance > 0:
            return max(0.0, 100.0 * (1.0 - distance / tolerance))
        return 0.0

    if hi is not None and val > hi:
        # Above maximum
        tolerance = abs(hi) * 0.2 if hi != 0 else 1.0
        distance = val - hi
        if distance <= tolerance and tolerance > 0:
            return max(0.0, 100.0 * (1.0 - distance / tolerance))
        return 0.0

    return 0.0


class MatchingEngine:
    """Supply-demand matching engine using AHP weighted scoring.

    Calculates matching scores between buyer demands and supplier fabrics
    across multiple dimensions (composition, weight, craft, price, width),
    using text similarity for text fields, numeric range matching for
    numeric fields, and AHP (Analytic Hierarchy Process) weights for
    aggregation.

    This is a pure computation class with no database dependencies.
    It works with both SQLAlchemy model objects and plain dictionaries.
    """

    DEFAULT_WEIGHTS = {
        'composition': 0.3,
        'weight': 0.2,
        'craft': 0.25,
        'price': 0.15,
        'width': 0.1,
    }

    def __init__(self, ahp_weights=None):
        """Initialize the matching engine with AHP weights.

        Args:
            ahp_weights: Dictionary mapping dimension names to their
                weights. Keys should include: composition, weight,
                craft, price, width. If None, default weights are used.
                Example: {'composition': 0.3, 'weight': 0.2,
                          'craft': 0.25, 'price': 0.15, 'width': 0.1}
        """
        if ahp_weights is None:
            self.weights = dict(self.DEFAULT_WEIGHTS)
        else:
            self.weights = dict(ahp_weights)

    def calculate_score(self, demand, fabric):
        """Calculate matching score between a demand and a fabric.

        Computes individual dimension scores using text similarity
        (for composition and craft) and numeric range matching
        (for weight, width, and price), then aggregates them using
        AHP weights.

        Args:
            demand: A Demand model object or dict with fields:
                composition, weight_min, weight_max, width_min,
                width_max, craft, price_min, price_max.
            fabric: A Fabric model object or dict with fields:
                composition, weight, width, craft, price.

        Returns:
            A float score between 0 and 100 representing the
            matching degree.
        """
        score_detail = {}

        # Text similarity scores
        composition_score = _text_score(
            _get_attr(demand, 'composition'),
            _get_attr(fabric, 'composition'),
        )
        score_detail['composition'] = round(composition_score, 2)

        craft_score = _text_score(
            _get_attr(demand, 'craft'),
            _get_attr(fabric, 'craft'),
        )
        score_detail['craft'] = round(craft_score, 2)

        # Numeric range scores
        weight_score = _numeric_range_score(
            _get_attr(fabric, 'weight'),
            _get_attr(demand, 'weight_min'),
            _get_attr(demand, 'weight_max'),
        )
        score_detail['weight'] = round(weight_score, 2)

        width_score = _numeric_range_score(
            _get_attr(fabric, 'width'),
            _get_attr(demand, 'width_min'),
            _get_attr(demand, 'width_max'),
        )
        score_detail['width'] = round(width_score, 2)

        price_score = _numeric_range_score(
            _get_attr(fabric, 'price'),
            _get_attr(demand, 'price_min'),
            _get_attr(demand, 'price_max'),
        )
        score_detail['price'] = round(price_score, 2)

        # AHP weighted aggregation
        total_score = (
            self.weights.get('composition', 0) * composition_score
            + self.weights.get('weight', 0) * weight_score
            + self.weights.get('craft', 0) * craft_score
            + self.weights.get('price', 0) * price_score
            + self.weights.get('width', 0) * width_score
        )

        # Clamp to 0-100 range
        total_score = max(0.0, min(100.0, total_score))
        total_score = round(total_score, 2)

        return total_score, score_detail

    def match(self, demand, fabrics):
        """Match a demand against a list of fabrics.

        Calculates matching scores for all fabrics and returns
        results sorted by score in descending order.

        Args:
            demand: A Demand model object or dict with demand fields.
            fabrics: A list of Fabric model objects or dicts.

        Returns:
            A list of dicts, each containing:
                - fabric_id: The fabric's ID.
                - score: The matching score (0-100).
                - score_detail: Dict with per-dimension scores.
            Sorted by score in descending order.
        """
        results = []

        for fabric in fabrics:
            fabric_id = _get_attr(fabric, 'id')
            total_score, score_detail = self.calculate_score(demand, fabric)

            results.append({
                'fabric_id': fabric_id,
                'score': total_score,
                'score_detail': score_detail,
            })

        # Sort by score descending
        results.sort(key=lambda x: x['score'], reverse=True)

        return results
