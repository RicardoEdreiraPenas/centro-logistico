SELECT
    e.id,
    e.truck_id,
    e.order_id,
    e.order_type,
    e.tractora_plate,
    e.remolque_plate,
    e.dock_id,
    e.cargo_desc,
    e.num_pallets,
    e.weight_kg,
    e.status,
    e.event_at,
    t.origin_city,
    t.origin_client,
    t.dest_city,
    t.dest_client
FROM {{ ref('base_raw_events_dock') }} e
LEFT JOIN {{ ref('base_trucks') }} t ON e.truck_id = t.id
