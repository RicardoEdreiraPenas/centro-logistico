SELECT
    id,
    tractora_plate,
    remolque_plate,
    origin_city,
    origin_client,
    dest_city,
    dest_client,
    arrived_at,
    departed_at
FROM {{ source('logistics', 'trucks') }}
