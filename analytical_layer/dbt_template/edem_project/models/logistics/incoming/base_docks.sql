SELECT id, status FROM {{ source('logistics', 'docks') }}
