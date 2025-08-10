# web-ui/app.py
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import httpx
import os
import logging
from pythonjsonlogger import jsonlogger
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter

SERVICE_NAME = "web-ui"
logger = logging.getLogger(SERVICE_NAME)
log_dir = os.getenv("LOG_DIR", "/app/logs")
os.makedirs(log_dir, exist_ok=True)
log_path = os.path.join(log_dir, "web-ui.log")
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
templates = Jinja2Templates(directory="templates")

PASSENGER_API = os.getenv("PASSENGER_API", "http://passenger-service:8001")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "result": None})

@app.post("/register", response_class=HTMLResponse)
async def register(request: Request, name: str = Form(...)):
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{PASSENGER_API}/passengers", json={"name": name}, timeout=10)
    if r.status_code != 200:
        logger.error("Failed to register passenger: %s", r.text)
        raise HTTPException(status_code=502, detail="Upstream passenger service error")
    data = r.json()
    return templates.TemplateResponse("index.html", {"request": request, "result": {"type":"registered", "data": data}})

@app.post("/request_ride", response_class=HTMLResponse)
async def request_ride(request: Request, passenger_id: int = Form(...)):
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{PASSENGER_API}/request_ride", json={"passenger_id": passenger_id}, timeout=10)
    if r.status_code != 200:
        logger.error("Failed to request ride: %s", r.text)
        return templates.TemplateResponse("index.html", {"request": request, "result": {"type":"error", "data": r.text}})
    data = r.json()
    return templates.TemplateResponse("index.html", {"request": request, "result": {"type":"ride", "data": data}})

@app.post("/ride_status", response_class=HTMLResponse)
async def ride_status(request: Request, ride_id: int = Form(...)):
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{PASSENGER_API}/ride_status/{ride_id}", timeout=10)
    if r.status_code != 200:
        return templates.TemplateResponse("index.html", {"request": request, "result": {"type":"error", "data": r.text}})
    data = r.json()
    return templates.TemplateResponse("index.html", {"request": request, "result": {"type":"status", "data": data}})
