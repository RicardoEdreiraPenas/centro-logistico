SELECT id, truck_id, assignment_id, order_type, cargo_desc,
       weight_kg, num_pallets, sequence, status
FROM {{ source('logistics', 'truck_orders') }}
