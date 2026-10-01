import datetime
import decimal
import logging

import psycopg2


class DbManager:
    def __init__(self, rds_config: dict, warehouse_config: dict = None):
        self.rds_config = rds_config
        self.warehouse_config = warehouse_config or rds_config

    def _connect_rds(self):
        try:
            conn = psycopg2.connect(**self.rds_config)
            logging.info("Connected to RDS successfully.")
            return conn
        except Exception as e:
            logging.error(f"Failed to connect to RDS: {e}")
            raise

    def _connect_warehouse(self):
        try:
            conn = psycopg2.connect(**self.warehouse_config)
            logging.info("Connected to warehouse (RDS) successfully.")
            return conn
        except Exception as e:
            logging.error(f"Failed to connect to warehouse: {e}")
            raise

    @staticmethod
    def _convert_value(value):
        if isinstance(value, decimal.Decimal):
            return float(value)
        if isinstance(value, datetime.datetime):
            return value.isoformat()
        return value

    def get_operational_data(self, table: str) -> list:
        conn = self._connect_rds()
        try:
            cursor = conn.cursor()
            cursor.execute(f"SELECT * FROM {table}")
            rows = cursor.fetchall()
            return [tuple(self._convert_value(v) for v in row) for row in rows]
        except Exception as e:
            logging.error(f"Error fetching {table} from RDS: {e}")
            return []
        finally:
            conn.close()

    def write_to_redshift(self, data: list, schema: str, table: str, columns: list) -> None:
        if not data:
            return
        conn = self._connect_warehouse()
        try:
            cursor = conn.cursor()
            cursor.execute(f"TRUNCATE TABLE {schema}.{table};")
            placeholders = ', '.join(['%s'] * len(columns))
            col_list = ', '.join(columns)
            query = f"INSERT INTO {schema}.{table} ({col_list}) VALUES ({placeholders});"
            cursor.executemany(query, data)
            conn.commit()
            logging.info(f"Wrote {len(data)} rows to {schema}.{table}.")
        except Exception as e:
            logging.error(f"Error writing to warehouse {schema}.{table}: {e}")
            raise
        finally:
            conn.close()

    def insert_event_to_redshift(self, event: dict) -> None:
        conn = self._connect_warehouse()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO dock_events.raw_events_dock
                    (truck_id, order_id, order_type, tractora_plate, remolque_plate,
                     dock_id, cargo_desc, num_pallets, weight_kg, status, event_at,
                     client_order_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
            """, (
                event['truck_id'], event.get('order_id'), event['order_type'],
                event['tractora_plate'], event['remolque_plate'], event['dock_id'],
                event['cargo_desc'], event['num_pallets'], event['weight_kg'],
                event['status'], event['event_at'], event.get('client_order_id'),
            ))
            conn.commit()
        except Exception as e:
            logging.error(f"Error inserting dock event to warehouse: {e}")
        finally:
            conn.close()
