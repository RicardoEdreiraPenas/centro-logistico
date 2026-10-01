import datetime
import logging
import os
import random
import string
import sys
import time

import psycopg2

from utils.sqs_manager import SQSManager

CITIES = [
    "Madrid", "Barcelona", "Valencia", "Sevilla", "Bilbao",
    "Zaragoza", "Málaga", "Murcia", "Palma", "Valladolid",
]

CLIENTS = [
    "Mercadona", "Carrefour", "Lidl", "Alcampo", "Dia",
    "Consum", "El Corte Inglés", "Eroski", "Bon Preu", "Condis",
]

CARGO_TYPES = [
    "Conservas y latas", "Productos frescos", "Bebidas",
    "Lácteos", "Congelados", "Droguería", "Textil",
    "Electrónica", "Papelería", "Ferretería",
]


def generate_tractora_plate() -> str:
    digits = ''.join(random.choices(string.digits, k=4))
    letters = ''.join(random.choices('BCDFGHJKLMNPRSTUVWXYZ', k=3))
    return f"{digits}-{letters}"


def generate_remolque_plate() -> str:
    letter = random.choice('BCDFGHJKLMNPRSTUVWXYZ')
    digits = ''.join(random.choices(string.digits, k=4))
    return f"R-{letter}{digits}"


def create_truck_orders(num_orders: int) -> list:
    """Returns 1 or 2 order dicts. If 2, unloading is always sequence=1."""
    if num_orders == 1:
        return [{
            'order_type': random.choice(['loading', 'unloading']),
            'cargo_desc': random.choice(CARGO_TYPES),
            'weight_kg': round(random.uniform(500, 12000), 2),
            'num_pallets': random.randint(5, 33),
            'sequence': 1,
        }]
    return [
        {
            'order_type': 'unloading',
            'cargo_desc': random.choice(CARGO_TYPES),
            'weight_kg': round(random.uniform(500, 6000), 2),
            'num_pallets': random.randint(5, 18),
            'sequence': 1,
        },
        {
            'order_type': 'loading',
            'cargo_desc': random.choice(CARGO_TYPES),
            'weight_kg': round(random.uniform(500, 6000), 2),
            'num_pallets': random.randint(5, 18),
            'sequence': 2,
        },
    ]


def assign_client_orders(conn, truck_id: int, max_orders: int = 2) -> list:
    """Atomically claim up to max_orders pending client_orders. Returns list of order dicts.
    Returns [] silently if client_orders table doesn't exist yet (client_app not started)."""
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT 1 FROM client_orders LIMIT 1;")
    except Exception:
        conn.rollback()
        cursor.close()
        return []
    cursor.execute("""
        UPDATE client_orders
        SET status = 'assigned', assigned_at = NOW(), truck_id = %s
        WHERE id IN (
            SELECT id FROM client_orders
            WHERE status = 'pending' AND expires_at > NOW()
            ORDER BY created_at
            LIMIT %s
            FOR UPDATE SKIP LOCKED
        )
        RETURNING id, client_id, order_type, total_weight_kg, total_pallets;
    """, (truck_id, max_orders))
    assigned_rows = cursor.fetchall()
    conn.commit()

    orders = []
    for order_id, client_id, order_type, total_weight, total_pallets in assigned_rows:
        cursor.execute(
            """SELECT ol.id, ol.num_pallets, ol.total_weight_kg,
                      p.sku, p.name, p.units_per_pallet, p.weight_kg_unit, p.id AS product_id
               FROM order_lines ol JOIN products p ON p.id = ol.product_id
               WHERE ol.client_order_id = %s ORDER BY ol.id;""",
            (order_id,),
        )
        lines = [
            {"line_id": r[0], "num_pallets": r[1], "total_weight_kg": r[2],
             "sku": r[3], "name": r[4], "units_per_pallet": r[5],
             "weight_kg_unit": r[6], "product_id": r[7]}
            for r in cursor.fetchall()
        ]
        cursor.execute("SELECT name FROM clients WHERE id = %s;", (client_id,))
        client_name = cursor.fetchone()[0]
        orders.append({
            "client_order_id": order_id,
            "client_name": client_name,
            "order_type": order_type,
            "total_weight_kg": total_weight,
            "num_pallets": total_pallets,
            "lines": lines,
        })
    cursor.close()
    return orders


def build_orders_from_assignment(assigned: list) -> list:
    """Sort assigned orders: unloading first, then loading. Set sequence numbers."""
    sorted_orders = sorted(assigned, key=lambda o: (0 if o["order_type"] == "unloading" else 1))
    for i, o in enumerate(sorted_orders, start=1):
        o["sequence"] = i
    return sorted_orders


def _create_tables(conn) -> None:
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trucks (
            id             SERIAL PRIMARY KEY,
            tractora_plate VARCHAR(10) NOT NULL,
            remolque_plate VARCHAR(10) NOT NULL,
            origin_city    VARCHAR(50),
            origin_client  VARCHAR(100),
            dest_city      VARCHAR(50),
            dest_client    VARCHAR(100),
            arrived_at     TIMESTAMP,
            departed_at    TIMESTAMP
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS docks (
            id     INT PRIMARY KEY,
            status VARCHAR(20) NOT NULL DEFAULT 'available'
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS assignments (
            id          SERIAL PRIMARY KEY,
            truck_id    INT REFERENCES trucks(id),
            dock_id     INT REFERENCES docks(id),
            assigned_at TIMESTAMP,
            released_at TIMESTAMP
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS truck_orders (
            id            SERIAL PRIMARY KEY,
            truck_id      INT REFERENCES trucks(id),
            assignment_id INT REFERENCES assignments(id),
            order_type    VARCHAR(20) NOT NULL,
            cargo_desc    VARCHAR(200),
            weight_kg     FLOAT,
            num_pallets   INT,
            sequence      INT NOT NULL,
            status        VARCHAR(20) NOT NULL DEFAULT 'pending'
        );
    """)
    cursor.execute("SELECT COUNT(*) FROM docks;")
    if cursor.fetchone()[0] == 0:
        for i in range(1, 11):
            cursor.execute("INSERT INTO docks (id, status) VALUES (%s, 'available');", (i,))
    conn.commit()
    cursor.close()


def insert_truck(conn, truck_data: dict) -> int:
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO trucks
           (tractora_plate, remolque_plate, origin_city, origin_client,
            dest_city, dest_client, arrived_at)
           VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id;""",
        (
            truck_data['tractora_plate'], truck_data['remolque_plate'],
            truck_data['origin_city'], truck_data['origin_client'],
            truck_data['dest_city'], truck_data['dest_client'],
            truck_data['arrived_at'],
        ),
    )
    truck_id = cursor.fetchone()[0]
    conn.commit()
    cursor.close()
    return truck_id


def insert_truck_orders(conn, truck_id: int, orders: list) -> list:
    cursor = conn.cursor()
    order_ids = []
    for order in orders:
        cursor.execute(
            """INSERT INTO truck_orders
               (truck_id, order_type, cargo_desc, weight_kg, num_pallets, sequence, status)
               VALUES (%s, %s, %s, %s, %s, %s, 'pending') RETURNING id;""",
            (
                truck_id, order['order_type'], order['cargo_desc'],
                order['weight_kg'], order['num_pallets'], order['sequence'],
            ),
        )
        order_ids.append(cursor.fetchone()[0])
    conn.commit()
    cursor.close()
    return order_ids


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()],
    )
    logger = logging.getLogger()

    DB_CONFIG = {
        "dbname": os.getenv('RDS_DB', 'postgres'),
        "user": os.getenv('RDS_USER', 'postgres'),
        "password": os.environ['RDS_PASSWORD'],
        "host": os.environ['RDS_HOST'],
        "port": int(os.getenv('RDS_PORT', 5432)),
    }

    conn = psycopg2.connect(**DB_CONFIG)
    _create_tables(conn)
    conn.close()
    logger.info("Tables created and docks seeded.")

    producer = SQSManager('truck-events')
    producer.create_publisher()

    while True:
        conn = psycopg2.connect(**DB_CONFIG)
        try:
            tractora = generate_tractora_plate()
            remolque = generate_remolque_plate()
            origin_city = random.choice(CITIES)
            dest_city = random.choice([c for c in CITIES if c != origin_city])
            origin_client = random.choice(CLIENTS)
            dest_client = random.choice(CLIENTS)
            arrived_at = datetime.datetime.now().isoformat()

            truck_data = {
                'tractora_plate': tractora, 'remolque_plate': remolque,
                'origin_city': origin_city, 'origin_client': origin_client,
                'dest_city': dest_city, 'dest_client': dest_client,
                'arrived_at': arrived_at,
            }
            truck_id = insert_truck(conn, truck_data)
            logger.info(f"Truck {truck_id} ({tractora}/{remolque}) arrived from {origin_city}")

            # Try to assign pre-generated client orders
            assigned = assign_client_orders(conn, truck_id)
            if assigned:
                orders_for_sqs = build_orders_from_assignment(assigned)
                logger.info(f"Truck {truck_id}: assigned {len(orders_for_sqs)} client order(s)")
            else:
                # Fallback: generate random orders (no client_app running or no pending orders)
                num_orders = random.choices([1, 2], weights=[50, 50])[0]
                random_orders = create_truck_orders(num_orders)
                order_ids = insert_truck_orders(conn, truck_id, random_orders)
                orders_for_sqs = [
                    {
                        "order_id": oid, "client_order_id": None, "client_name": None,
                        "order_type": o["order_type"], "total_weight_kg": o["weight_kg"],
                        "num_pallets": o["num_pallets"], "sequence": o["sequence"],
                        "lines": [{"sku": None, "name": o["cargo_desc"],
                                   "num_pallets": o["num_pallets"],
                                   "total_weight_kg": o["weight_kg"],
                                   "units_per_pallet": 1, "weight_kg_unit": 0,
                                   "line_id": None, "product_id": None}],
                    }
                    for o, oid in zip(random_orders, order_ids)
                ]
                logger.info(f"Truck {truck_id}: fallback random orders {[o['order_type'] for o in random_orders]}")

            producer.send_message({
                "truck_id": truck_id, "tractora_plate": tractora,
                "remolque_plate": remolque, "origin_city": origin_city,
                "origin_client": origin_client, "dest_city": dest_city,
                "dest_client": dest_client, "arrived_at": arrived_at,
                "orders": orders_for_sqs,
            })
            logger.info(f"Published SQS truck-event for truck {truck_id}")

        except Exception as e:
            logger.error(f"Error: {e}")
        finally:
            conn.close()

        time.sleep(random.randint(30, 60))
