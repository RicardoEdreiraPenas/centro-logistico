import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from client_app.main import PRODUCTS, CLIENT_SEED, compute_line_weight


def test_products_catalog_has_expected_count():
    assert len(PRODUCTS) >= 20


def test_products_have_required_fields():
    for p in PRODUCTS:
        assert 'sku' in p
        assert 'name' in p
        assert 'category' in p
        assert p['weight_kg_unit'] > 0
        assert p['units_per_pallet'] > 0


def test_products_skus_are_unique():
    skus = [p['sku'] for p in PRODUCTS]
    assert len(skus) == len(set(skus))


def test_client_seed_has_required_fields():
    for c in CLIENT_SEED:
        assert 'name' in c
        assert 'city' in c
        assert c['type'] in ('supplier', 'retailer')


def test_compute_line_weight():
    # 4 pallets × 120 units × 1.02 kg = 489.6 kg
    result = compute_line_weight(num_pallets=4, units_per_pallet=120, weight_kg_unit=1.02)
    assert abs(result - 489.6) < 0.01


def test_compute_line_weight_rounds_to_two_decimals():
    result = compute_line_weight(3, 96, 0.52)
    assert result == round(3 * 96 * 0.52, 2)


from client_app.main import compute_order_totals


def test_compute_order_totals_sums_correctly():
    lines = [
        {"num_pallets": 4, "units_per_pallet": 120, "weight_kg_unit": 1.02},
        {"num_pallets": 2, "units_per_pallet": 96,  "weight_kg_unit": 0.52},
    ]
    total_weight, total_pallets = compute_order_totals(lines)
    assert total_pallets == 6
    assert abs(total_weight - (4*120*1.02 + 2*96*0.52)) < 0.01


def test_compute_order_totals_single_line():
    lines = [{"num_pallets": 3, "units_per_pallet": 80, "weight_kg_unit": 0.42}]
    total_weight, total_pallets = compute_order_totals(lines)
    assert total_pallets == 3
    assert abs(total_weight - 3*80*0.42) < 0.01


from unittest.mock import MagicMock, patch
from client_app.main import expire_stale_orders


def test_expire_stale_orders_returns_count():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchall.return_value = [(1,), (2,), (3,)]

    count = expire_stale_orders(mock_conn)

    assert count == 3
    mock_cursor.execute.assert_called_once()
    sql = mock_cursor.execute.call_args[0][0]
    assert "expired" in sql
    assert "expires_at" in sql
    mock_conn.commit.assert_called_once()


def test_expire_stale_orders_returns_zero_when_none():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchall.return_value = []

    count = expire_stale_orders(mock_conn)
    assert count == 0


from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from client_app.main import build_api


def make_mock_db():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.__enter__ = lambda s: s
    mock_cursor.__exit__ = MagicMock(return_value=False)
    return mock_conn, mock_cursor


def test_post_orders_rejects_duplicate_skus():
    app = build_api(db_config={})
    client = TestClient(app)

    with patch("client_app.main.psycopg2.connect") as mock_connect:
        mock_conn, mock_cursor = make_mock_db()
        mock_connect.return_value = mock_conn
        mock_cursor.fetchone.return_value = (1,)  # client exists
        mock_cursor.fetchall.return_value = [
            {"sku": "LCHE-001", "id": 1, "units_per_pallet": 120, "weight_kg_unit": 1.02},
        ]

        resp = client.post("/orders", json={
            "client_id": 1,
            "order_type": "loading",
            "lines": [
                {"sku": "LCHE-001", "num_pallets": 5},
                {"sku": "LCHE-001", "num_pallets": 3},
            ],
        })
        assert resp.status_code == 400
        assert "Duplicate" in resp.json()["detail"]


def test_post_orders_rejects_invalid_order_type():
    app = build_api(db_config={})
    client = TestClient(app)

    resp = client.post("/orders", json={
        "client_id": 1,
        "order_type": "transfer",
        "lines": [{"sku": "LCHE-001", "num_pallets": 2}],
    })
    assert resp.status_code == 400
    assert "order_type" in resp.json()["detail"]
