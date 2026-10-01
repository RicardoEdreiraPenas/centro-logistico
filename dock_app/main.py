import datetime
import logging
import os
import random
import time

import psycopg2

from utils.sqs_manager import SQSManager
from utils.db_manager_utils import DbManager

TRUCK_MAX_WEIGHT_KG = float(os.getenv("TRUCK_MAX_WEIGHT_KG", 24000))
TRUCK_MAX_PALLETS = int(os.getenv("TRUCK_MAX_PALLETS", 33))


def compute_fulfillment(line: dict, remaining_pallets: int, remaining_kg: float) -> tuple:
    """Returns (fulfillment_status, fulfilled_pallets, new_remaining_pallets, new_remaining_kg)."""
    if remaining_pallets <= 0:
        return "unfulfilled", 0, 0, remaining_kg

    if line["num_pallets"] <= remaining_pallets:
        return (
            "fulfilled",
            line["num_pallets"],
            remaining_pallets - line["num_pallets"],
            remaining_kg - line["total_weight_kg"],
        )

    partial = remaining_pallets
    partial_kg = round(partial * line["units_per_pallet"] * line["weight_kg_unit"], 2)
    return "partial", partial, 0, remaining_kg - partial_kg


def build_cargo_desc(lines: list) -> str:
    parts = [f"{l.get('name') or 'Carga'} × {l['num_pallets']}p" for l in lines]
    return ", ".join(parts)


def update_order_line_fulfillment(conn, line_id: int, status: str, fulfilled: int) -> None:
    if line_id is None:
        return
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE order_lines SET fulfillment_status = %s, fulfilled_pallets = %s WHERE id = %s;",
        (status, fulfilled, line_id),
    )
    conn.commit()
    cursor.close()


def update_inventory(conn, product_id: int, order_type: str, fulfilled_pallets: int) -> None:
    if product_id is None or fulfilled_pallets == 0:
        return
    cursor = conn.cursor()
    if order_type == "unloading":
        cursor.execute(
            "UPDATE inventory SET stock_pallets = stock_pallets + %s, updated_at = NOW() WHERE product_id = %s;",
            (fulfilled_pallets, product_id),
        )
    else:
        cursor.execute(
            "UPDATE inventory SET stock_pallets = GREATEST(0, stock_pallets - %s), updated_at = NOW() WHERE product_id = %s;",
            (fulfilled_pallets, product_id),
        )
    conn.commit()
    cursor.close()


def check_low_stock(conn, product_id: int, product_name: str) -> None:
    if product_id is None:
        return
    cursor = conn.cursor()
    cursor.execute(
        "SELECT stock_pallets, low_stock_threshold FROM inventory WHERE product_id = %s;",
        (product_id,),
    )
    row = cursor.fetchone()
    cursor.close()
    if row and row[0] < row[1]:
        logging.warning(f"LOW STOCK: {product_name} — {row[0]} pallets remaining (threshold: {row[1]})")


def complete_client_order(conn, client_order_id: int) -> None:
    if client_order_id is None:
        return
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE client_orders SET status = 'completed', completed_at = NOW() WHERE id = %s AND status = 'assigned';",
        (client_order_id,),
    )
    conn.commit()
    cursor.close()


def build_dock_event(truck_id: int, order: dict, dock_id: int, status: str,
                     client_order_id: int = None, cargo_desc: str = None) -> dict:
    return {
        "truck_id": truck_id,
        "order_id": order.get("order_id") or order.get("client_order_id"),
        "order_type": order["order_type"],
        "tractora_plate": order.get("tractora_plate", ""),
        "remolque_plate": order.get("remolque_plate", ""),
        "dock_id": dock_id,
        "cargo_desc": cargo_desc or order.get("cargo_desc", ""),
        "num_pallets": order.get("num_pallets", 0),
        "weight_kg": order.get("total_weight_kg") or order.get("weight_kg", 0),
        "status": status,
        "event_at": datetime.datetime.now(),
        "client_order_id": client_order_id,
    }


def get_and_reserve_dock(conn) -> int | None:
    """Atomic SELECT+UPDATE — avoids race conditions."""
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE docks SET status = 'occupied'
        WHERE id = (SELECT id FROM docks WHERE status = 'available' ORDER BY id LIMIT 1)
        RETURNING id;
    """)
    row = cursor.fetchone()
    conn.commit()
    cursor.close()
    return row[0] if row else None


def release_dock(conn, dock_id: int) -> None:
    cursor = conn.cursor()
    cursor.execute("UPDATE docks SET status = 'available' WHERE id = %s;", (dock_id,))
    conn.commit()
    cursor.close()


def create_assignment(conn, truck_id: int, dock_id: int) -> int:
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO assignments (truck_id, dock_id, assigned_at) VALUES (%s, %s, %s) RETURNING id;",
        (truck_id, dock_id, datetime.datetime.now()),
    )
    assignment_id = cursor.fetchone()[0]
    conn.commit()
    cursor.close()
    return assignment_id


def complete_assignment(conn, assignment_id: int) -> None:
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE assignments SET released_at = %s WHERE id = %s;",
        (datetime.datetime.now(), assignment_id),
    )
    conn.commit()
    cursor.close()


def update_order_status(conn, order_id: int, status: str, assignment_id: int = None) -> None:
    cursor = conn.cursor()
    if assignment_id is not None:
        cursor.execute(
            "UPDATE truck_orders SET status = %s, assignment_id = %s WHERE id = %s;",
            (status, assignment_id, order_id),
        )
    else:
        cursor.execute("UPDATE truck_orders SET status = %s WHERE id = %s;", (status, order_id))
    conn.commit()
    cursor.close()


def update_truck_departed(conn, truck_id: int) -> None:
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE trucks SET departed_at = %s WHERE id = %s;",
        (datetime.datetime.now(), truck_id),
    )
    conn.commit()
    cursor.close()


def process_truck(rds_conn, db_manager, message: dict) -> None:
    truck_id = message["truck_id"]
    orders = sorted(message["orders"], key=lambda o: o["sequence"])

    if not orders:
        logging.warning(f"Truck {truck_id} has no orders, skipping.")
        return

    dock_id = None
    for attempt in range(10):
        dock_id = get_and_reserve_dock(rds_conn)
        if dock_id:
            break
        logging.info(f"No dock available (attempt {attempt + 1}/10). Waiting 10s...")
        time.sleep(10)

    if not dock_id:
        logging.error(f"No dock available for truck {truck_id}. Skipping.")
        return

    assignment_id = create_assignment(rds_conn, truck_id, dock_id)
    logging.info(f"Truck {truck_id} ({message['tractora_plate']}) → dock {dock_id}")

    remaining_kg = TRUCK_MAX_WEIGHT_KG
    remaining_pallets = TRUCK_MAX_PALLETS

    for order in orders:
        client_order_id = order.get("client_order_id")
        lines = order.get("lines", [])
        enriched_order = {
            **order,
            "tractora_plate": message["tractora_plate"],
            "remolque_plate": message["remolque_plate"],
        }

        event = build_dock_event(truck_id, enriched_order, dock_id, "assigned", client_order_id,
                                 build_cargo_desc(lines))
        db_manager.insert_event_to_redshift(event)

        order_id = order.get("order_id") or order.get("client_order_id")
        if order_id and not order.get("client_order_id"):
            update_order_status(rds_conn, order_id, "in_progress", assignment_id)

        time.sleep(random.randint(5, 15))

        for line in lines:
            f_status, fulfilled, remaining_pallets, remaining_kg = compute_fulfillment(
                line, remaining_pallets, remaining_kg
            )
            update_order_line_fulfillment(rds_conn, line.get("line_id"), f_status, fulfilled)
            update_inventory(rds_conn, line.get("product_id"), order["order_type"], fulfilled)
            check_low_stock(rds_conn, line.get("product_id"), line.get("name", ""))
            logging.info(
                f"Truck {truck_id} dock {dock_id}: {line.get('name','?')} "
                f"{fulfilled}/{line['num_pallets']}p [{f_status}]"
            )

        time.sleep(random.randint(10, 30))

        cargo_desc = build_cargo_desc(lines)
        event = build_dock_event(truck_id, enriched_order, dock_id, "completed", client_order_id, cargo_desc)
        db_manager.insert_event_to_redshift(event)

        if order_id and not order.get("client_order_id"):
            update_order_status(rds_conn, order_id, "completed")

        complete_client_order(rds_conn, client_order_id)
        logging.info(f"Truck {truck_id} dock {dock_id}: order {client_order_id or order_id} COMPLETED")

    complete_assignment(rds_conn, assignment_id)
    release_dock(rds_conn, dock_id)
    update_truck_departed(rds_conn, truck_id)
    logging.info(f"Truck {truck_id} departed. Dock {dock_id} available.")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()],
    )
    logger = logging.getLogger()

    RDS_CONFIG = {
        "dbname": os.getenv('RDS_DB', 'postgres'),
        "user": os.getenv('RDS_USER', 'postgres'),
        "password": os.environ['RDS_PASSWORD'],
        "host": os.environ['RDS_HOST'],
        "port": int(os.getenv('RDS_PORT', 5432)),
    }

    db_manager = DbManager(RDS_CONFIG)
    subscriber = SQSManager('truck-events')
    subscriber.create_subscriber()

    while True:
        try:
            rds_conn = psycopg2.connect(**RDS_CONFIG)
            for message in subscriber.consume_messages():
                process_truck(rds_conn, db_manager, message)
            rds_conn.close()
        except KeyboardInterrupt:
            logger.info("Process stopped by user.")
            break
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            time.sleep(5)
