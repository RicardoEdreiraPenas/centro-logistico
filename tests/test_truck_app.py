import re
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from truck_app.main import (
    generate_tractora_plate,
    generate_remolque_plate,
    create_truck_orders,
)


def test_tractora_plate_format():
    for _ in range(20):
        plate = generate_tractora_plate()
        assert re.match(r'^\d{4}-[BCDFGHJKLMNPRSTUVWXYZ]{3}$', plate), \
            f"Invalid tractora plate: {plate}"


def test_remolque_plate_format():
    for _ in range(20):
        plate = generate_remolque_plate()
        assert re.match(r'^R-[BCDFGHJKLMNPRSTUVWXYZ]\d{4}$', plate), \
            f"Invalid remolque plate: {plate}"


def test_create_truck_orders_single_has_valid_fields():
    orders = create_truck_orders(1)
    assert len(orders) == 1
    o = orders[0]
    assert o['sequence'] == 1
    assert o['order_type'] in ('loading', 'unloading')
    assert 5 <= o['num_pallets'] <= 33
    assert o['weight_kg'] > 0
    assert o['cargo_desc'] != ''


def test_create_truck_orders_double_unloads_first():
    orders = create_truck_orders(2)
    assert len(orders) == 2
    by_seq = {o['sequence']: o for o in orders}
    assert by_seq[1]['order_type'] == 'unloading'
    assert by_seq[2]['order_type'] == 'loading'


def test_create_truck_orders_double_pallets_within_range():
    orders = create_truck_orders(2)
    for o in orders:
        assert 5 <= o['num_pallets'] <= 18
        assert o['weight_kg'] > 0


from unittest.mock import MagicMock
from truck_app.main import assign_client_orders, build_orders_from_assignment


def test_assign_client_orders_returns_empty_when_none_available():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchall.return_value = []

    result = assign_client_orders(mock_conn, truck_id=1)
    assert result == []


def test_build_orders_from_assignment_sets_sequence():
    assigned = [
        {"client_order_id": 1, "order_type": "unloading", "client_name": "Mercadona",
         "total_weight_kg": 500.0, "num_pallets": 6, "lines": []},
        {"client_order_id": 2, "order_type": "loading", "client_name": "Lidl",
         "total_weight_kg": 300.0, "num_pallets": 4, "lines": []},
    ]
    orders = build_orders_from_assignment(assigned)
    assert orders[0]["sequence"] == 1
    assert orders[1]["sequence"] == 2
    assert orders[0]["order_type"] == "unloading"


def test_build_orders_from_assignment_unloading_first():
    assigned = [
        {"client_order_id": 10, "order_type": "loading", "client_name": "A",
         "total_weight_kg": 100.0, "num_pallets": 2, "lines": []},
        {"client_order_id": 11, "order_type": "unloading", "client_name": "B",
         "total_weight_kg": 200.0, "num_pallets": 3, "lines": []},
    ]
    orders = build_orders_from_assignment(assigned)
    assert orders[0]["order_type"] == "unloading"
    assert orders[1]["order_type"] == "loading"
