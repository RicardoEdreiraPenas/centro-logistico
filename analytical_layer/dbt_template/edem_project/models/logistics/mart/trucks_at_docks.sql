WITH latest_events AS (
    SELECT
        truck_id, order_id, order_type, tractora_plate, remolque_plate,
        dock_id, cargo_desc, num_pallets, weight_kg, status, event_at,
        ROW_NUMBER() OVER (PARTITION BY truck_id, order_id ORDER BY event_at DESC) AS rn
    FROM {{ ref('base_raw_events_dock') }}
)
SELECT
    le.truck_id, le.tractora_plate, le.remolque_plate,
    le.dock_id, le.order_id, le.order_type,
    le.cargo_desc, le.num_pallets, le.weight_kg,
    le.status, le.event_at,
    t.origin_city, t.origin_client, t.dest_city, t.dest_client
FROM latest_events le
LEFT JOIN {{ ref('base_trucks') }} t ON le.truck_id = t.id
WHERE le.rn = 1
  AND le.status != 'completed'
