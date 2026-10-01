import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dock_app.main import build_dock_event


def test_build_dock_event_contains_required_fields():
    order = {
        'order_id': 1, 'order_type': 'unloading',
        'tractora_plate': '1234-ABC', 'remolque_plate': 'R-B5678',
        'cargo_desc': 'Bebidas', 'num_pallets': 10, 'weight_kg': 3000.0,
    }
    event = build_dock_event(truck_id=42, order=order, dock_id=5, status='in_progress')
    assert event['truck_id'] == 42
    assert event['order_id'] == 1
    assert event['dock_id'] == 5
    assert event['order_type'] == 'unloading'
    assert event['status'] == 'in_progress'
    assert event['num_pallets'] == 10
    assert event['weight_kg'] == 3000.0
    assert event['cargo_desc'] == 'Bebidas'
    assert event['tractora_plate'] == '1234-ABC'
    assert event['remolque_plate'] == 'R-B5678'
    assert 'event_at' in event


def test_build_dock_event_status_values():
    order = {
        'order_id': 2, 'order_type': 'loading',
        'tractora_plate': '5678-XYZ', 'remolque_plate': 'R-C1234',
        'cargo_desc': 'Lácteos', 'num_pallets': 8, 'weight_kg': 1500.0,
    }
    for status in ('assigned', 'in_progress', 'completed'):
        event = build_dock_event(truck_id=1, order=order, dock_id=3, status=status)
        assert event['status'] == status


from dock_app.main import compute_fulfillment, build_cargo_desc


def test_compute_fulfillment_full():
    line = {"num_pallets": 5, "total_weight_kg": 500.0, "units_per_pallet": 120, "weight_kg_unit": 0.83}
    status, fulfilled, rem_pal, rem_kg = compute_fulfillment(line, remaining_pallets=10, remaining_kg=5000.0)
    assert status == "fulfilled"
    assert fulfilled == 5
    assert rem_pal == 5
    assert abs(rem_kg - 4500.0) < 0.01


def test_compute_fulfillment_partial():
    line = {"num_pallets": 10, "total_weight_kg": 1000.0, "units_per_pallet": 120, "weight_kg_unit": 0.83}
    status, fulfilled, rem_pal, rem_kg = compute_fulfillment(line, remaining_pallets=3, remaining_kg=5000.0)
    assert status == "partial"
    assert fulfilled == 3
    assert rem_pal == 0


def test_compute_fulfillment_unfulfilled():
    line = {"num_pallets": 5, "total_weight_kg": 500.0, "units_per_pallet": 120, "weight_kg_unit": 0.83}
    status, fulfilled, rem_pal, rem_kg = compute_fulfillment(line, remaining_pallets=0, remaining_kg=1000.0)
    assert status == "unfulfilled"
    assert fulfilled == 0
    assert rem_pal == 0


def test_build_cargo_desc_single_line():
    lines = [{"name": "Leche entera 1L", "num_pallets": 4}]
    assert build_cargo_desc(lines) == "Leche entera 1L × 4p"


def test_build_cargo_desc_multiple_lines():
    lines = [
        {"name": "Leche entera 1L", "num_pallets": 4},
        {"name": "Yogur natural 500g", "num_pallets": 2},
    ]
    assert build_cargo_desc(lines) == "Leche entera 1L × 4p, Yogur natural 500g × 2p"


def test_build_cargo_desc_fallback_name():
    lines = [{"name": None, "num_pallets": 3}]
    desc = build_cargo_desc(lines)
    assert "3p" in desc
