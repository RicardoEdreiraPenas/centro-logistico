import logging
import os

import psycopg2

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DB_CONFIG = {
    "dbname": os.getenv('RDS_DB', 'postgres'),
    "user": os.getenv('RDS_USER', 'postgres'),
    "password": os.environ['RDS_PASSWORD'],
    "host": os.environ['RDS_HOST'],
    "port": int(os.getenv('RDS_PORT', 5432)),
}

SQL = """
CREATE SCHEMA IF NOT EXISTS logistics;
CREATE SCHEMA IF NOT EXISTS dock_events;

-- Existing operational → analytical copies
CREATE TABLE IF NOT EXISTS logistics.trucks (
    id INT, tractora_plate VARCHAR(10), remolque_plate VARCHAR(10),
    origin_city VARCHAR(50), origin_client VARCHAR(100),
    dest_city VARCHAR(50), dest_client VARCHAR(100),
    arrived_at TIMESTAMP, departed_at TIMESTAMP
);
CREATE TABLE IF NOT EXISTS logistics.docks (id INT, status VARCHAR(20));
CREATE TABLE IF NOT EXISTS logistics.assignments (
    id INT, truck_id INT, dock_id INT,
    assigned_at TIMESTAMP, released_at TIMESTAMP
);
CREATE TABLE IF NOT EXISTS logistics.truck_orders (
    id INT, truck_id INT, assignment_id INT,
    order_type VARCHAR(20), cargo_desc VARCHAR(200),
    weight_kg FLOAT, num_pallets INT, sequence INT, status VARCHAR(20)
);

-- New analytical copies
CREATE TABLE IF NOT EXISTS logistics.clients (
    id INT, name VARCHAR(100), city VARCHAR(50), type VARCHAR(20)
);
CREATE TABLE IF NOT EXISTS logistics.products (
    id INT, sku VARCHAR(20), name VARCHAR(100), category VARCHAR(50),
    weight_kg_unit FLOAT, units_per_pallet INT
);
CREATE TABLE IF NOT EXISTS logistics.client_orders (
    id INT, client_id INT, order_type VARCHAR(20), status VARCHAR(20),
    total_weight_kg FLOAT, total_pallets INT,
    created_at TIMESTAMP, expires_at TIMESTAMP,
    assigned_at TIMESTAMP, completed_at TIMESTAMP, truck_id INT
);
CREATE TABLE IF NOT EXISTS logistics.order_lines (
    id INT, client_order_id INT, product_id INT,
    num_pallets INT, units_per_pallet INT, total_weight_kg FLOAT,
    fulfillment_status VARCHAR(20), fulfilled_pallets INT
);
CREATE TABLE IF NOT EXISTS logistics.inventory (
    product_id INT, stock_pallets INT,
    low_stock_threshold INT, updated_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS dock_events.raw_events_dock (
    id BIGSERIAL PRIMARY KEY,
    truck_id INT, order_id INT, order_type VARCHAR(20),
    tractora_plate VARCHAR(10), remolque_plate VARCHAR(10),
    dock_id INT, cargo_desc VARCHAR(200),
    num_pallets INT, weight_kg FLOAT,
    status VARCHAR(20), event_at TIMESTAMP,
    client_order_id INT
);

ALTER TABLE dock_events.raw_events_dock ADD COLUMN IF NOT EXISTS client_order_id INT;
"""

if __name__ == "__main__":
    logging.info(f"Connecting to RDS at {DB_CONFIG['host']}...")
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = True
    cursor = conn.cursor()
    logging.info("Connected. Creating schemas and tables...")
    cursor.execute(SQL)
    logging.info("Done. Verifying...")

    for schema, table in [
        ('logistics', 'trucks'), ('logistics', 'docks'),
        ('logistics', 'assignments'), ('logistics', 'truck_orders'),
        ('logistics', 'clients'), ('logistics', 'products'),
        ('logistics', 'client_orders'), ('logistics', 'order_lines'),
        ('logistics', 'inventory'),
        ('dock_events', 'raw_events_dock'),
    ]:
        cursor.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=%s AND table_name=%s",
            (schema, table)
        )
        exists = cursor.fetchone()[0]
        status = "OK" if exists else "MISSING"
        logging.info(f"  {schema}.{table}: {status}")

    cursor.close()
    conn.close()
    logging.info("Setup complete.")
