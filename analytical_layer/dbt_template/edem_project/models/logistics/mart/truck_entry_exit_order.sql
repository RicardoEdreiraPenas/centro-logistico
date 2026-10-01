SELECT
    id                                                       AS truck_id,
    tractora_plate,
    remolque_plate,
    origin_city,
    origin_client,
    dest_city,
    dest_client,
    arrived_at,
    departed_at,
    ROW_NUMBER() OVER (ORDER BY arrived_at ASC)             AS entry_order,
    ROW_NUMBER() OVER (ORDER BY departed_at ASC NULLS LAST) AS exit_order
FROM {{ ref('base_trucks') }}
WHERE arrived_at IS NOT NULL
