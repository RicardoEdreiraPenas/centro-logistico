SELECT
    id,
    truck_id,
    order_id,
    order_type,
    tractora_plate,
    remolque_plate,
    dock_id,
    cargo_desc,
    num_pallets,
    weight_kg,
    status,
    event_at
FROM {{ source('dock_events', 'raw_events_dock') }}
