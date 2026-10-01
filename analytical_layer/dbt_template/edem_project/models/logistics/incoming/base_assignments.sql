SELECT id, truck_id, dock_id, assigned_at, released_at
FROM {{ source('logistics', 'assignments') }}
