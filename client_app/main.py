import datetime
import logging
import os
import random
import threading
import time

import psycopg2
import psycopg2.extras

PRODUCTS = [
    {"sku": "LCHE-001", "name": "Leche entera 1L",        "category": "Lácteos",          "weight_kg_unit": 1.02, "units_per_pallet": 120},
    {"sku": "YOGR-002", "name": "Yogur natural 500g",      "category": "Lácteos",          "weight_kg_unit": 0.52, "units_per_pallet": 96},
    {"sku": "QUSO-003", "name": "Queso curado 400g",       "category": "Lácteos",          "weight_kg_unit": 0.42, "units_per_pallet": 80},
    {"sku": "AGUA-004", "name": "Agua mineral 1.5L",       "category": "Bebidas",          "weight_kg_unit": 1.52, "units_per_pallet": 84},
    {"sku": "ZUMO-005", "name": "Zumo naranja 1L",         "category": "Bebidas",          "weight_kg_unit": 1.05, "units_per_pallet": 72},
    {"sku": "CERV-006", "name": "Cerveza 33cl",            "category": "Bebidas",          "weight_kg_unit": 0.38, "units_per_pallet": 200},
    {"sku": "TOMT-007", "name": "Tomate triturado 400g",   "category": "Conservas y latas","weight_kg_unit": 0.42, "units_per_pallet": 144},
    {"sku": "ATUN-008", "name": "Atún en aceite 80g",      "category": "Conservas y latas","weight_kg_unit": 0.10, "units_per_pallet": 240},
    {"sku": "LNTJ-009", "name": "Lentejas cocidas 400g",   "category": "Conservas y latas","weight_kg_unit": 0.42, "units_per_pallet": 144},
    {"sku": "POLL-010", "name": "Pollo entero 1.5kg",      "category": "Productos frescos","weight_kg_unit": 1.55, "units_per_pallet": 48},
    {"sku": "TERN-011", "name": "Ternera filetes 500g",    "category": "Productos frescos","weight_kg_unit": 0.52, "units_per_pallet": 60},
    {"sku": "PIZZ-012", "name": "Pizza margherita 350g",   "category": "Congelados",       "weight_kg_unit": 0.36, "units_per_pallet": 80},
    {"sku": "GUIS-013", "name": "Guisantes congelados 1kg","category": "Congelados",       "weight_kg_unit": 1.02, "units_per_pallet": 60},
    {"sku": "DETG-014", "name": "Detergente líquido 1.5L", "category": "Droguería",        "weight_kg_unit": 1.55, "units_per_pallet": 60},
    {"sku": "PPHL-015", "name": "Papel higiénico 12ud",    "category": "Droguería",        "weight_kg_unit": 1.20, "units_per_pallet": 48},
    {"sku": "CMST-016", "name": "Camiseta básica",         "category": "Textil",           "weight_kg_unit": 0.30, "units_per_pallet": 200},
    {"sku": "CALC-017", "name": "Calcetines pack 3",       "category": "Textil",           "weight_kg_unit": 0.15, "units_per_pallet": 300},
    {"sku": "USBC-018", "name": "Cable USB-C 1m",          "category": "Electrónica",      "weight_kg_unit": 0.08, "units_per_pallet": 400},
    {"sku": "CHRG-019", "name": "Cargador 20W",            "category": "Electrónica",      "weight_kg_unit": 0.12, "units_per_pallet": 300},
    {"sku": "BOLI-020", "name": "Bolígrafo azul pack 10",  "category": "Papelería",        "weight_kg_unit": 0.10, "units_per_pallet": 500},
    {"sku": "CUAD-021", "name": "Cuaderno A4",             "category": "Papelería",        "weight_kg_unit": 0.35, "units_per_pallet": 200},
    {"sku": "TORN-022", "name": "Tornillo M6 pack 50",     "category": "Ferretería",       "weight_kg_unit": 0.25, "units_per_pallet": 400},
    {"sku": "LLAV-023", "name": "Llave inglesa 200mm",     "category": "Ferretería",       "weight_kg_unit": 0.45, "units_per_pallet": 100},
]

CLIENT_SEED = [
    {"name": "Mercadona",       "city": "Valencia",   "type": "retailer"},
    {"name": "Carrefour",       "city": "Madrid",     "type": "retailer"},
    {"name": "Lidl",            "city": "Madrid",     "type": "retailer"},
    {"name": "Alcampo",         "city": "Zaragoza",   "type": "retailer"},
    {"name": "Dia",             "city": "Madrid",     "type": "retailer"},
    {"name": "Consum",          "city": "Valencia",   "type": "retailer"},
    {"name": "El Corte Inglés", "city": "Madrid",     "type": "retailer"},
    {"name": "Eroski",          "city": "Bilbao",     "type": "retailer"},
    {"name": "Bon Preu",        "city": "Barcelona",  "type": "retailer"},
    {"name": "Condis",          "city": "Barcelona",  "type": "retailer"},
]


def compute_line_weight(num_pallets: int, units_per_pallet: int, weight_kg_unit: float) -> float:
    return round(num_pallets * units_per_pallet * weight_kg_unit, 2)


def create_tables(conn) -> None:
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id               SERIAL PRIMARY KEY,
            sku              VARCHAR(20) UNIQUE NOT NULL,
            name             VARCHAR(100) NOT NULL,
            category         VARCHAR(50) NOT NULL,
            weight_kg_unit   FLOAT NOT NULL,
            units_per_pallet INT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS clients (
            id   SERIAL PRIMARY KEY,
            name VARCHAR(100) UNIQUE NOT NULL,
            city VARCHAR(50) NOT NULL,
            type VARCHAR(20) NOT NULL
        );
        CREATE TABLE IF NOT EXISTS client_orders (
            id               SERIAL PRIMARY KEY,
            client_id        INT REFERENCES clients(id) NOT NULL,
            order_type       VARCHAR(20) NOT NULL,
            status           VARCHAR(20) NOT NULL DEFAULT 'pending',
            total_weight_kg  FLOAT NOT NULL DEFAULT 0,
            total_pallets    INT NOT NULL DEFAULT 0,
            created_at       TIMESTAMP NOT NULL,
            expires_at       TIMESTAMP NOT NULL,
            assigned_at      TIMESTAMP,
            completed_at     TIMESTAMP,
            truck_id         INT
        );
        CREATE TABLE IF NOT EXISTS order_lines (
            id                 SERIAL PRIMARY KEY,
            client_order_id    INT REFERENCES client_orders(id) NOT NULL,
            product_id         INT REFERENCES products(id) NOT NULL,
            num_pallets        INT NOT NULL,
            units_per_pallet   INT NOT NULL,
            total_weight_kg    FLOAT NOT NULL,
            fulfillment_status VARCHAR(20) NOT NULL DEFAULT 'pending',
            fulfilled_pallets  INT,
            UNIQUE (client_order_id, product_id)
        );
        CREATE TABLE IF NOT EXISTS inventory (
            product_id          INT REFERENCES products(id) PRIMARY KEY,
            stock_pallets       INT NOT NULL DEFAULT 0,
            low_stock_threshold INT NOT NULL DEFAULT 5,
            updated_at          TIMESTAMP NOT NULL
        );
    """)
    conn.commit()
    cursor.close()


def seed_products(conn) -> None:
    cursor = conn.cursor()
    for p in PRODUCTS:
        cursor.execute(
            """INSERT INTO products (sku, name, category, weight_kg_unit, units_per_pallet)
               VALUES (%s, %s, %s, %s, %s) ON CONFLICT (sku) DO NOTHING;""",
            (p["sku"], p["name"], p["category"], p["weight_kg_unit"], p["units_per_pallet"]),
        )
    cursor.execute(
        "INSERT INTO inventory (product_id, stock_pallets, updated_at) "
        "SELECT id, 0, NOW() FROM products ON CONFLICT (product_id) DO NOTHING;"
    )
    conn.commit()
    cursor.close()
    logging.info(f"Seeded {len(PRODUCTS)} products and inventory rows.")


def seed_clients(conn) -> None:
    cursor = conn.cursor()
    for c in CLIENT_SEED:
        cursor.execute(
            "INSERT INTO clients (name, city, type) VALUES (%s, %s, %s) ON CONFLICT (name) DO NOTHING;",
            (c["name"], c["city"], c["type"]),
        )
    conn.commit()
    cursor.close()
    logging.info(f"Seeded {len(CLIENT_SEED)} clients.")


def compute_order_totals(lines: list) -> tuple:
    """Returns (total_weight_kg, total_pallets) from a list of line dicts."""
    total_weight = sum(
        compute_line_weight(l["num_pallets"], l["units_per_pallet"], l["weight_kg_unit"])
        for l in lines
    )
    total_pallets = sum(l["num_pallets"] for l in lines)
    return round(total_weight, 2), total_pallets


def generate_client_order(conn, ttl_minutes: int = 10) -> int:
    """Insert one client_order with 1-5 distinct order_lines. Returns client_order_id."""
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM clients ORDER BY random() LIMIT 1;")
    client_id = cursor.fetchone()[0]
    order_type = random.choice(["loading", "unloading"])

    num_lines = random.randint(1, 5)
    cursor.execute(
        "SELECT id, units_per_pallet, weight_kg_unit FROM products ORDER BY random() LIMIT %s;",
        (num_lines,),
    )
    products = cursor.fetchall()

    lines_meta = []
    for product_id, units_per_pallet, weight_kg_unit in products:
        num_pallets = random.randint(1, 10)
        lines_meta.append({
            "product_id": product_id,
            "num_pallets": num_pallets,
            "units_per_pallet": units_per_pallet,
            "weight_kg_unit": weight_kg_unit,
        })

    total_weight, total_pallets = compute_order_totals(lines_meta)
    now = datetime.datetime.now()
    expires_at = now + datetime.timedelta(minutes=ttl_minutes)

    cursor.execute(
        """INSERT INTO client_orders
           (client_id, order_type, status, total_weight_kg, total_pallets, created_at, expires_at)
           VALUES (%s, %s, 'pending', %s, %s, %s, %s) RETURNING id;""",
        (client_id, order_type, total_weight, total_pallets, now, expires_at),
    )
    order_id = cursor.fetchone()[0]

    for lm in lines_meta:
        line_weight = compute_line_weight(lm["num_pallets"], lm["units_per_pallet"], lm["weight_kg_unit"])
        cursor.execute(
            """INSERT INTO order_lines
               (client_order_id, product_id, num_pallets, units_per_pallet, total_weight_kg)
               VALUES (%s, %s, %s, %s, %s);""",
            (order_id, lm["product_id"], lm["num_pallets"], lm["units_per_pallet"], line_weight),
        )

    conn.commit()
    cursor.close()
    return order_id


def generation_loop(db_config: dict, ttl_minutes: int) -> None:
    """Main generation loop: creates 1-2 orders every 20-40s."""
    while True:
        try:
            conn = psycopg2.connect(**db_config)
            num_orders = random.randint(1, 2)
            for _ in range(num_orders):
                order_id = generate_client_order(conn, ttl_minutes)
                logging.info(f"Generated client_order {order_id}")
            conn.close()
        except Exception as e:
            logging.error(f"Generation error: {e}")
        time.sleep(random.randint(20, 40))


def expire_stale_orders(conn) -> int:
    """Mark pending orders past their expires_at as expired. Returns count."""
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE client_orders SET status = 'expired'
        WHERE status = 'pending' AND expires_at < NOW()
        RETURNING id;
    """)
    expired = cursor.fetchall()
    conn.commit()
    cursor.close()
    if expired:
        logging.info(f"Expired {len(expired)} stale orders: {[r[0] for r in expired]}")
    return len(expired)


def expiration_loop(db_config: dict) -> None:
    """Background thread: checks for expired orders every 60s."""
    while True:
        try:
            conn = psycopg2.connect(**db_config)
            expire_stale_orders(conn)
            conn.close()
        except Exception as e:
            logging.error(f"Expiration error: {e}")
        time.sleep(60)


def start_expiration_thread(db_config: dict) -> threading.Thread:
    t = threading.Thread(target=expiration_loop, args=(db_config,), daemon=True)
    t.start()
    return t


from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import HTMLResponse
from pydantic import BaseModel


class OrderLineIn(BaseModel):
    sku: str
    num_pallets: int


class OrderIn(BaseModel):
    client_id: int
    order_type: str
    lines: list[OrderLineIn]


def build_api(db_config: dict) -> FastAPI:
    app = FastAPI(title="Logistics Client API")

    def get_db():
        conn = psycopg2.connect(**db_config)
        try:
            yield conn
        finally:
            conn.close()

    @app.post("/orders", status_code=201)
    def create_order(order: OrderIn):
        if order.order_type not in ("loading", "unloading"):
            raise HTTPException(400, "order_type must be 'loading' or 'unloading'")
        skus = [l.sku for l in order.lines]
        if len(skus) != len(set(skus)):
            raise HTTPException(400, "Duplicate SKUs in order lines")
        conn = psycopg2.connect(**db_config)
        try:
            return _create_order_with_conn(order, skus, conn)
        finally:
            conn.close()

    def _create_order_with_conn(order: OrderIn, skus: list, conn):

        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT id FROM clients WHERE id = %s;", (order.client_id,))
        if not cursor.fetchone():
            raise HTTPException(400, f"Client {order.client_id} not found")

        cursor.execute(
            "SELECT id, sku, units_per_pallet, weight_kg_unit FROM products WHERE sku = ANY(%s);",
            (skus,),
        )
        by_sku = {r["sku"]: r for r in cursor.fetchall()}
        missing = [s for s in skus if s not in by_sku]
        if missing:
            raise HTTPException(400, f"Unknown SKUs: {missing}")

        lines_data, total_weight, total_pallets = [], 0.0, 0
        for line in order.lines:
            p = by_sku[line.sku]
            w = compute_line_weight(line.num_pallets, p["units_per_pallet"], p["weight_kg_unit"])
            total_weight += w
            total_pallets += line.num_pallets
            lines_data.append((p["id"], line.num_pallets, p["units_per_pallet"], w))

        ttl = int(os.getenv("ORDER_TTL_MINUTES", 10))
        now = datetime.datetime.now()
        expires_at = now + datetime.timedelta(minutes=ttl)
        cursor.execute(
            """INSERT INTO client_orders
               (client_id, order_type, status, total_weight_kg, total_pallets, created_at, expires_at)
               VALUES (%s, %s, 'pending', %s, %s, %s, %s) RETURNING id, expires_at;""",
            (order.client_id, order.order_type, round(total_weight, 2), total_pallets, now, expires_at),
        )
        row = cursor.fetchone()
        order_id, exp = row["id"], row["expires_at"]
        for product_id, num_pallets, units_per_pallet, line_weight in lines_data:
            cursor.execute(
                "INSERT INTO order_lines (client_order_id, product_id, num_pallets, units_per_pallet, total_weight_kg) "
                "VALUES (%s, %s, %s, %s, %s);",
                (order_id, product_id, num_pallets, units_per_pallet, line_weight),
            )
        conn.commit()
        return {"client_order_id": order_id, "expires_at": exp.isoformat()}

    @app.get("/orders")
    def list_orders(status: str = None, conn=Depends(get_db)):
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        if status:
            cursor.execute("SELECT * FROM client_orders WHERE status = %s ORDER BY created_at DESC LIMIT 100;", (status,))
        else:
            cursor.execute("SELECT * FROM client_orders ORDER BY created_at DESC LIMIT 100;")
        return cursor.fetchall()

    @app.get("/orders/{order_id}")
    def get_order(order_id: int, conn=Depends(get_db)):
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT * FROM client_orders WHERE id = %s;", (order_id,))
        order = cursor.fetchone()
        if not order:
            raise HTTPException(404, "Order not found")
        cursor.execute(
            """SELECT ol.*, p.sku, p.name AS product_name FROM order_lines ol
               JOIN products p ON p.id = ol.product_id
               WHERE ol.client_order_id = %s ORDER BY ol.id;""",
            (order_id,),
        )
        return {**order, "lines": cursor.fetchall()}

    @app.get("/clients")
    def list_clients(conn=Depends(get_db)):
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT * FROM clients ORDER BY name;")
        return cursor.fetchall()

    @app.get("/products")
    def list_products(conn=Depends(get_db)):
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT * FROM products ORDER BY category, name;")
        return cursor.fetchall()

    @app.get("/inventory")
    def get_inventory(conn=Depends(get_db)):
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute(
            """SELECT p.sku, p.name, p.category, i.stock_pallets, i.low_stock_threshold,
                      i.stock_pallets < i.low_stock_threshold AS low_stock, i.updated_at
               FROM inventory i JOIN products p ON p.id = i.product_id
               ORDER BY p.name;"""
        )
        return cursor.fetchall()

    return app


FLOOR_HTML = """<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Centro Logístico — Plano en Tiempo Real</title>
  <style>
    body{font-family:monospace;background:#1a1a2e;color:#eee;margin:0;padding:20px}
    h1{color:#e94560;margin-bottom:4px}
    #updated{color:#aaa;font-size:12px;margin-bottom:20px}
    #grid{display:grid;grid-template-columns:repeat(5,1fr);gap:12px}
    .dock{background:#16213e;border-radius:8px;padding:14px;border:2px solid #0f3460;min-height:200px}
    .dock.available{border-color:#28a745}.dock.occupied{border-color:#e94560}
    .dock-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px}
    .dock-num{font-size:18px;font-weight:bold;color:#e94560}
    .badge{padding:2px 8px;border-radius:4px;font-size:11px;font-weight:bold}
    .badge.available{background:#28a745;color:#fff}.badge.occupied{background:#e94560;color:#fff}
    .plate{font-weight:bold;color:#00b4d8}.route{color:#90e0ef;margin:4px 0;font-size:12px}
    .order-type{display:inline-block;padding:2px 6px;border-radius:3px;font-size:10px;font-weight:bold;margin:4px 0}
    .loading{background:#ff9f1c;color:#000}.unloading{background:#2ec4b6;color:#000}
    .line{font-size:11px;padding:3px 0;border-bottom:1px solid #0f3460;color:#caf0f8}
    .line:last-child{border-bottom:none}
    .fulfilled{color:#28a745}.pending-line{color:#aaa}.empty{color:#444;font-size:12px;text-align:center;margin-top:40px}
  </style>
</head>
<body>
  <h1>Centro Logístico — Plano en Tiempo Real</h1>
  <div id="updated">Cargando...</div>
  <div id="grid"></div>
  <script>
    async function refresh(){
      try{
        const res=await fetch('/floor');
        const docks=await res.json();
        document.getElementById('grid').innerHTML=docks.map(d=>{
          const occ=!!d.truck_id;
          const cls=occ?'occupied':'available';
          const badge=occ?'OCUPADO':'LIBRE';
          let inner='';
          if(occ){
            const ot=d.order_type||'';
            const lines=(d.lines||[]).map(l=>
              `<div class="line ${l.fulfillment_status==='fulfilled'?'fulfilled':'pending-line'}">
                ${l.sku} x${l.num_pallets}p [${l.fulfillment_status}]
               </div>`).join('');
            inner=`<div style="font-size:12px">
              <div class="plate">${d.tractora_plate||''} / ${d.remolque_plate||''}</div>
              <div class="route">${d.origin_city||'?'} → ${d.dest_city||'?'}</div>
              <div style="font-size:11px;color:#aaa">${d.origin_client||''} → ${d.dest_client||''}</div>
              ${ot?`<span class="order-type ${ot}">${ot.toUpperCase()}</span>`:''}
              ${d.client_name?`<div style="font-size:11px;color:#ffd166">📦 ${d.client_name}</div>`:''}
              <div style="margin-top:6px">${lines||'<div class="line pending-line">Sin líneas activas</div>'}</div>
            </div>`;
          }else{
            inner='<div class="empty">— Libre —</div>';
          }
          return `<div class="dock ${cls}">
            <div class="dock-header">
              <span class="dock-num">Muelle ${d.dock_id}</span>
              <span class="badge ${cls}">${badge}</span>
            </div>${inner}</div>`;
        }).join('');
        document.getElementById('updated').textContent='Última actualización: '+new Date().toLocaleTimeString();
      }catch(e){document.getElementById('updated').textContent='Error: '+e.message;}
    }
    refresh();
    setInterval(refresh,5000);
  </script>
</body>
</html>"""


def _extend_api_with_floor(app: FastAPI, db_config: dict) -> None:
    """Adds /floor and /floor/view routes to an existing FastAPI app."""
    import psycopg2.extras as _extras

    def get_db():
        conn = psycopg2.connect(**db_config)
        try:
            yield conn
        finally:
            conn.close()

    @app.get("/floor")
    def floor_data(conn=Depends(get_db)):
        cursor = conn.cursor(cursor_factory=_extras.RealDictCursor)
        cursor.execute("""
            SELECT
                d.id AS dock_id, d.status AS dock_status,
                t.id AS truck_id, t.tractora_plate, t.remolque_plate,
                t.origin_city, t.origin_client, t.dest_city, t.dest_client,
                co.id AS client_order_id, co.order_type, cl.name AS client_name,
                ol.id AS line_id, p.sku, p.name AS product_name,
                ol.num_pallets AS line_pallets, ol.fulfillment_status
            FROM docks d
            LEFT JOIN assignments a ON a.dock_id = d.id AND a.released_at IS NULL
            LEFT JOIN trucks t ON t.id = a.truck_id
            LEFT JOIN client_orders co ON co.truck_id = t.id AND co.status = 'assigned'
            LEFT JOIN clients cl ON cl.id = co.client_id
            LEFT JOIN order_lines ol ON ol.client_order_id = co.id
            LEFT JOIN products p ON p.id = ol.product_id
            ORDER BY d.id, ol.id;
        """)
        rows = cursor.fetchall()
        docks = {}
        for r in rows:
            did = r["dock_id"]
            if did not in docks:
                docks[did] = {k: r[k] for k in
                    ("dock_id", "dock_status", "truck_id", "tractora_plate", "remolque_plate",
                     "origin_city", "origin_client", "dest_city", "dest_client",
                     "client_order_id", "order_type", "client_name")}
                docks[did]["lines"] = []
            if r["line_id"]:
                docks[did]["lines"].append({
                    "sku": r["sku"], "product_name": r["product_name"],
                    "num_pallets": r["line_pallets"],
                    "fulfillment_status": r["fulfillment_status"],
                })
        return list(docks.values())

    @app.get("/floor/view", response_class=HTMLResponse)
    def floor_view():
        return FLOOR_HTML


def main() -> None:
    import uvicorn

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )

    DB_CONFIG = {
        "dbname": os.getenv("RDS_DB", "postgres"),
        "user": os.getenv("RDS_USER", "postgres"),
        "password": os.environ["RDS_PASSWORD"],
        "host": os.environ["RDS_HOST"],
        "port": int(os.getenv("RDS_PORT", 5432)),
    }

    conn = psycopg2.connect(**DB_CONFIG)
    create_tables(conn)
    seed_products(conn)
    seed_clients(conn)
    conn.close()
    logging.info("Tables created and seeded.")

    start_expiration_thread(DB_CONFIG)
    logging.info("Expiration thread started.")

    ttl = int(os.getenv("ORDER_TTL_MINUTES", 10))
    gen_thread = threading.Thread(target=generation_loop, args=(DB_CONFIG, ttl), daemon=True)
    gen_thread.start()
    logging.info("Generation thread started.")

    api = build_api(DB_CONFIG)
    _extend_api_with_floor(api, DB_CONFIG)
    port = int(os.getenv("CLIENT_API_PORT", 8080))
    logging.info(f"Starting API on port {port}. Floor plan: http://localhost:{port}/floor/view")
    uvicorn.run(api, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
