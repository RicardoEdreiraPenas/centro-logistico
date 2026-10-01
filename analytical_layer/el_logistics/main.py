import logging
import os
import time

from utils.db_manager_utils import DbManager

TABLES_COLUMNS = {
    "trucks": ["id", "tractora_plate", "remolque_plate", "origin_city", "origin_client",
               "dest_city", "dest_client", "arrived_at", "departed_at"],
    "docks": ["id", "status"],
    "assignments": ["id", "truck_id", "dock_id", "assigned_at", "released_at"],
    "truck_orders": ["id", "truck_id", "assignment_id", "order_type", "cargo_desc",
                     "weight_kg", "num_pallets", "sequence", "status"],
    "clients": ["id", "name", "city", "type"],
    "products": ["id", "sku", "name", "category", "weight_kg_unit", "units_per_pallet"],
    "client_orders": ["id", "client_id", "order_type", "status", "total_weight_kg",
                      "total_pallets", "created_at", "expires_at", "assigned_at",
                      "completed_at", "truck_id"],
    "order_lines": ["id", "client_order_id", "product_id", "num_pallets", "units_per_pallet",
                    "total_weight_kg", "fulfillment_status", "fulfilled_pallets"],
    "inventory": ["product_id", "stock_pallets", "low_stock_threshold", "updated_at"],
}


def sync_table(db_manager: DbManager, table: str) -> None:
    logging.info(f"Syncing {table}...")
    data = db_manager.get_operational_data(table)
    if not data:
        logging.warning(f"No data in {table}, skipping.")
        return
    columns = TABLES_COLUMNS[table]
    db_manager.write_to_redshift(data, "logistics", table, columns)
    logging.info(f"Synced {len(data)} rows for {table}.")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()],
    )

    RDS_CONFIG = {
        "dbname": os.getenv('RDS_DB', 'postgres'),
        "user": os.getenv('RDS_USER', 'postgres'),
        "password": os.environ['RDS_PASSWORD'],
        "host": os.environ['RDS_HOST'],
        "port": int(os.getenv('RDS_PORT', 5432)),
    }

    db_manager = DbManager(RDS_CONFIG)

    while True:
        try:
            for table in ["trucks", "docks", "assignments", "truck_orders",
                          "clients", "products", "client_orders", "order_lines", "inventory"]:
                sync_table(db_manager, table)
            logging.info("Sync complete. Waiting 60s...")
            time.sleep(60)
        except KeyboardInterrupt:
            logging.warning("EL pipeline stopped by user.")
            break
        except Exception as e:
            logging.error(f"Error during sync: {e}")
            break
