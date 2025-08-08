import os
import logging
import time
from typing import List
from statistics import mean, pstdev

from fastapi import Response, FastAPI
from pydantic import BaseModel
from prometheus_client import Counter, Histogram, generate_latest, CollectorRegistry, CONTENT_TYPE_LATEST

########## LOGGING SETUP ################################
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("ga-evaluator")

############# PROMETHEUS METRICS ########################
POD      = os.getenv("POD_NAME", "unknown")
REGISTRY = CollectorRegistry(auto_describe=False)
eval_counter = Counter(
    'ga_evaluations_total', 'Total number of fitness evaluations', labelnames=['pod'], registry=REGISTRY
)
eval_duration = Histogram(
    'ga_evaluation_seconds', 'Time taken per fitness evaluation (s)', labelnames=['pod'], registry=REGISTRY
)

app = FastAPI()

######### HEALTH AND METRICS ENDPOINTS #########
@app.get("/healthz")
def healthz():
    return {"status": "ok"}

@app.get("/metrics")
def metrics():
    eval_counter.labels(pod=POD)
    eval_duration.labels(pod=POD)
    data = generate_latest(REGISTRY)
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)

############ REQUEST & RESPONSE #######################
class EvalRequest(BaseModel):
    individual:      List[int]
    execution_times: List[float]
    base_energy:     float
    idle_energy:     float

class EvalResponse(BaseModel):
    fitness:      float
    core_times:   List[float]
    total_energy: float
    makespan:     float
    imbalance:    float

########## EVALUATION ENDPOINT #####################
@app.post("/evaluate", response_model=EvalResponse)
def evaluate(req: EvalRequest):
    time.sleep(0.5)
    eval_counter.inc(labels={'pod': POD})
    start = time.time()

    # 1) Compute per-core times
    n_cores    = max(req.individual) + 1
    core_times = [0.0] * n_cores
    for idx, core_id in enumerate(req.individual):
        core_times[core_id] += req.execution_times[idx]

    # 2) Makespan
    makespan = max(core_times)

    # 3) Energy
    active_energy = sum(ct * req.base_energy for ct in core_times)
    idle_energy   = sum((makespan - ct) * req.idle_energy for ct in core_times)
    total_energy  = active_energy + idle_energy

    # 4) Imbalance
    imbalance = pstdev(core_times) / (mean(core_times) or 1)

    duration = time.time() - start
    eval_duration.observe(duration)

    # 5) Fitness (now matches monolithic GA normalization)
    # Compute global bounds
    TOTAL_EXEC   = sum(req.execution_times) 
    MAX_MAKESPAN = TOTAL_EXEC               
    MAX_ENERGY   = TOTAL_EXEC * req.base_energy \
                   + (n_cores - 1) * TOTAL_EXEC * req.idle_energy  

    # Normalize & cap each metric
    nm = min(makespan / MAX_MAKESPAN, 1.0)   
    ne = min(total_energy / MAX_ENERGY, 1.0) 
    ni = min(imbalance, 1.0)                

    # Weighted‐sum fitness
    fitness = 0.4 * nm + 0.2 * ne + 0.4 * ni  

    logger.info(
        f"Eval done: makespan={makespan:.2f}, energy={total_energy:.2f}, "
        f"imbalance={imbalance:.4f}, fitness={fitness:.4f}, took={duration:.4f}s"
    )

    return EvalResponse(
        fitness=fitness,
        core_times=core_times,
        total_energy=total_energy,
        makespan=makespan,
        imbalance=imbalance
    )
