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

# Logging setup
logger = logging.getLogger("passenger-service")
file_handler = logging.FileHandler("/tmp/web-ui.log")
formatter = jsonlogger.JsonFormatter('%(asctime)s %(name)s %(levelname)s %(message)s trace_id=%(trace_id)s span_id=%(span_id)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.setLevel(logging.INFO)

# Tracing setup
resource = Resource.create({"service.name": "passenger-service"})
provider = TracerProvider(resource=resource)
jaeger_exporter = JaegerExporter(
    collector_endpoint=os.getenv("JAEGER_COLLECTOR", "http://jaeger:14268/api/traces")
)
provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))
trace.set_tracer_provider(provider)

app = FastAPI()
FastAPIInstrumentor.instrument_app(app)

DB_HOST = os.getenv("DB_HOST", "db")
DB_NAME = os.getenv("DB_NAME", "taxi_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "postgres")

class RideRequest(BaseModel):
    passenger_id: int

def get_db_conn():
    return psycopg2.connect(host=DB_HOST, dbname=DB_NAME, user=DB_USER, password=DB_PASS)

def get_trace_context():
    span = trace.get_current_span()
    if span and span.get_span_context().trace_id != 0:
        trace_id = format(span.get_span_context().trace_id, '032x')
        span_id = format(span.get_span_context().span_id, '016x')
        return trace_id, span_id
    return None, None

@app.post("/request_ride")
def request_ride(ride_req: RideRequest):
    trace_id, span_id = get_trace_context()
    logger.info(f"Ride requested for passenger {ride_req.passenger_id}", extra={"trace_id": trace_id, "span_id": span_id})

    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO rides (passenger_id, status) VALUES (%s, 'pending') RETURNING id", (ride_req.passenger_id,))
    ride_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    logger.info(f"Created ride with id {ride_id}", extra={"trace_id": trace_id, "span_id": span_id})
    return {"ride_id": ride_id, "status": "pending"}

@app.get("/ride_status/{ride_id}")
def ride_status(ride_id: int):
    trace_id, span_id = get_trace_context()
    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM rides WHERE id=%s", (ride_id,))
    ride = cur.fetchone()
    cur.close()
    conn.close()
    if ride:
        logger.info(f"Ride status requested for id {ride_id}", extra={"trace_id": trace_id, "span_id": span_id})
        return ride
    else:
        logger.warning(f"Ride id {ride_id} not found", extra={"trace_id": trace_id, "span_id": span_id})
        raise HTTPException(status_code=404, detail="Ride not found")
