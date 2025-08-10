from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
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

logger = logging.getLogger("web-ui")
file_handler = logging.FileHandler("/tmp/web-ui.log")
formatter = jsonlogger.JsonFormatter('%(asctime)s %(name)s %(levelname)s %(message)s trace_id=%(trace_id)s span_id=%(span_id)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.setLevel(logging.INFO)

resource = Resource.create({"service.name": "web-ui"})
provider = TracerProvider(resource=resource)
jaeger_exporter = JaegerExporter(collector_endpoint=os.getenv("JAEGER_COLLECTOR", "http://jaeger:14268/api/traces"))
provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))
trace.set_tracer_provider(provider)

app = FastAPI()
FastAPIInstrumentor.instrument_app(app)

templates = Jinja2Templates(directory="templates")

PASSENGER_API = os.getenv("PASSENGER_API", "http://passenger-service:8001")

def get_trace_context():
    span = trace.get_current_span()
    if span and span.get_span_context().trace_id != 0:
        return (format(span.get_span_context().trace_id, '032x'), format(span.get_span_context().span_id, '016x'))
    return (None, None)

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "ride_status": None})

@app.post("/request_ride", response_class=HTMLResponse)
async def request_ride(request: Request, passenger_id: int = Form(...)):
    trace_id, span_id = get_trace_context()
    logger.info(f"Ride request form submitted for passenger {passenger_id}", extra={"trace_id": trace_id, "span_id": span_id})

    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{PASSENGER_API}/request_ride", json={"passenger_id": passenger_id})
        print(f"Response status: {resp.status_code}")
        print(f"Response text: {resp.text}")
        data = resp.json()
        logger.info(f"Received ride response {data}", extra={"trace_id": trace_id, "span_id": span_id})
        return templates.TemplateResponse("index.html", {"request": request, "ride_status": data})

@app.post("/ride_status", response_class=HTMLResponse)
async def ride_status(request: Request, ride_id: int = Form(...)):
    trace_id, span_id = get_trace_context()
    logger.info(f"Ride status form submitted for ride id {ride_id}", extra={"trace_id": trace_id, "span_id": span_id})

    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{PASSENGER_API}/ride_status/{ride_id}")
        if resp.status_code == 200:
            data = resp.json()
        else:
            data = {"error": "Ride not found"}
        logger.info(f"Received ride status response {data}", extra={"trace_id": trace_id, "span_id": span_id})
        return templates.TemplateResponse("index.html", {"request": request, "ride_status": data})
