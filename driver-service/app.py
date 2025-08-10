# driver-service/app.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import logging
from pythonjsonlogger import jsonlogger
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter

SERVICE_NAME = "driver-service"
logger = logging.getLogger(SERVICE_NAME)
log_path = f"/tmp/{SERVICE_NAME}.log"
file_handler = logging.FileHandler(log_path)
formatter = jsonlogger.JsonFormatter('%(asctime)s %(name)s %(levelname)s %(message)s trace_id=%(trace_id)s span_id=%(span_id)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)

resource = Resource.create({"service.name": SERVICE_NAME})
provider = TracerProvider(resource=resource)
jaeger_exporter = JaegerExporter(collector_endpoint=os.getenv("JAEGER_COLLECTOR", "http://jaeger:14268/api/traces"))
provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))
trace.set_tracer_provider(provider)

app = FastAPI()
FastAPIInstrumentor.instrument_app(app)

DB_HOST = os.getenv("DB_HOST", "db")
DB_NAME = os.getenv("DB_NAME", "taxi_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "postgres")

class Driver(BaseModel):
    name: str

def get_db_conn():
    return psycopg2.connect(host=DB_HOST, dbname=DB_NAME, user=DB_USER, password=DB_PASS)

def get_trace_context():
    span = trace.get_current_span()
    if span and span.get_span_context().trace_id != 0:
        return (format(span.get_span_context().trace_id, '032x'), format(span.get_span_context().span_id, '016x'))
    return (None, None)

@app.post("/drivers")
def create_driver(d: Driver):
    trace_id, span_id = get_trace_context()
    logger.info(f"Creating driver {d.name}", extra={"trace_id": trace_id, "span_id": span_id})
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO drivers (name, available) VALUES (%s, TRUE) RETURNING id", (d.name,))
    driver_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    logger.info(f"Created driver id={driver_id}", extra={"trace_id": trace_id, "span_id": span_id})
    return {"driver_id": driver_id, "name": d.name}

@app.get("/available_rides")
def available_rides():
    trace_id, span_id = get_trace_context()
    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT id, passenger_id, status FROM rides WHERE status='pending'")
    rides = cur.fetchall()
    cur.close()
    conn.close()
    logger.info(f"Fetched {len(rides)} available rides", extra={"trace_id": trace_id, "span_id": span_id})
    return rides

@app.post("/accept_ride/{ride_id}")
def accept_ride(ride_id: int, driver_id: int):
    trace_id, span_id = get_trace_context()
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute("SELECT status FROM rides WHERE id=%s", (ride_id,))
    row = cur.fetchone()
    if not row or row[0] != 'pending':
        cur.close()
        conn.close()
        logger.warning(f"Ride {ride_id} not available", extra={"trace_id": trace_id, "span_id": span_id})
        raise HTTPException(status_code=400, detail="Ride not available")
    # assign driver
    cur.execute("UPDATE rides SET driver_id=%s, status='accepted', accepted_at=NOW() WHERE id=%s", (driver_id, ride_id))
    cur.execute("UPDATE drivers SET available=FALSE WHERE id=%s", (driver_id,))
    conn.commit()
    cur.close()
    conn.close()
    logger.info(f"Ride {ride_id} accepted by driver {driver_id}", extra={"trace_id": trace_id, "span_id": span_id})
    return {"ride_id": ride_id, "driver_id": driver_id, "status": "accepted"}

@app.post("/complete_ride/{ride_id}")
def complete_ride(ride_id: int, driver_id: int):
    trace_id, span_id = get_trace_context()
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute("SELECT status, driver_id FROM rides WHERE id=%s", (ride_id,))
    row = cur.fetchone()
    if not row or row[0] != 'accepted' or row[1] != driver_id:
        cur.close()
        conn.close()
        logger.warning(f"Ride {ride_id} not accepted by driver {driver_id}", extra={"trace_id": trace_id, "span_id": span_id})
        raise HTTPException(status_code=400, detail="Ride not accepted by driver")
    cur.execute("UPDATE rides SET status='completed', completed_at=NOW() WHERE id=%s", (ride_id,))
    cur.execute("UPDATE drivers SET available=TRUE WHERE id=%s", (driver_id,))
    conn.commit()
    cur.close()
    conn.close()
    logger.info(f"Ride {ride_id} completed by driver {driver_id}", extra={"trace_id": trace_id, "span_id": span_id})
    return {"ride_id": ride_id, "driver_id": driver_id, "status": "completed"}
