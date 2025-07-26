import os
import logging
import time
from typing import List
from statistics import mean, pstdev

from fastapi import FastAPI
from pydantic import BaseModel
from prometheus_client import Counter, Histogram, start_http_server

# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("ga-evaluator")

# ── Prometheus metrics ────────────────────────────────────────────────────────
eval_counter = Counter(
    'ga_evaluations_total', 'Total number of fitness evaluations'
)
eval_duration = Histogram(
    'ga_evaluation_seconds', 'Time taken per fitness evaluation (s)'
)

# Expose Prom metrics on port 5000
start_http_server(5000)

app = FastAPI()

# ── Request & response models ─────────────────────────────────────────────────
class EvalRequest(BaseModel):
    individual:        List[int]   # core assignments per task
    execution_times:   List[float] # task durations
    base_energy:       float       # energy per unit time when active
    idle_energy:       float       # energy per unit time when idle

class EvalResponse(BaseModel):
    fitness:     float
    core_times:  List[float]
    total_energy: float
    makespan:    float
    imbalance:   float

# ── Evaluation endpoint ───────────────────────────────────────────────────────
@app.post("/evaluate", response_model=EvalResponse)
def evaluate(req: EvalRequest):
    logger.debug(f"Eval request received: individual_len={len(req.individual)}")
    eval_counter.inc()
    start = time.time()

    # 1) Compute per-core times
    n_cores = max(req.individual) + 1
    core_times = [0.0] * n_cores
    for task_idx, core_id in enumerate(req.individual):
        core_times[core_id] += req.execution_times[task_idx]

    # 2) Makespan = max load
    makespan = max(core_times)

    # 3) Energy consumption
    active_energy = sum(ct * req.base_energy for ct in core_times)
    idle_energy   = sum((makespan - ct) * req.idle_energy for ct in core_times)
    total_energy  = active_energy + idle_energy

    # 4) Imbalance (stddev / mean)
    imbalance = pstdev(core_times) / (mean(core_times) or 1)

    duration = time.time() - start
    eval_duration.observe(duration)

    # 5) Fitness: you can adjust weights as needed
    fitness = (
        0.4 * (makespan / sum(req.execution_times)) +
        0.2 * (total_energy / sum(req.execution_times)) +
        0.4 * imbalance
    )

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
