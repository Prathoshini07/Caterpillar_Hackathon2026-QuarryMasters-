"""
Two-Tier Anomaly Detection Pipeline — Fleet Operational Anomaly Scanner
========================================================================

Layer 1 — Deterministic Rule Engine (Instant Enforcement, <1ms):
  Flags hard operational boundary violations:
  · GHOST_IDLING             — Engine Hours = 0 while Idle Hours > 0 (phantom ignition)
  · CONSTRAINT_VIOLATION_HIGH_IER — Idle Hours >= Engine Hours (IER >= 50%)
  · UNASSIGNED_USAGE         — Active telemetry with Site ID = NULL
  · MISSING_OPERATOR         — Equipment operating with Operator ID = NULL

Layer 2 — Unsupervised One-Class SVM (RBF Kernel, Behavioral Outliers):
  Data passing through Layer 1 is evaluated by an OCSVM trained on healthy
  operating norms (records with normal IER, active engine hours, assigned site
  and operator). Catches:
  · BEHAVIORAL_OUTLIER — Contextual under-utilization & unusual duty cycles
                         that bypass static threshold rules.
"""

import numpy as np
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import RentalLog, Equipment, Site, Operator
from sklearn.svm import OneClassSVM
from sklearn.preprocessing import StandardScaler

router = APIRouter(prefix="/api/anomaly", tags=["Anomaly Detection"])

# ──────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ──────────────────────────────────────────────────────────────────────────────
IER_VIOLATION_THRESHOLD = 50.0   # IER (%) at which CONSTRAINT_VIOLATION triggers

SEVERITY_MAP = {
    "CRITICAL": {"color": "#A855F7", "priority": 0},
    "HIGH":     {"color": "#EF4444", "priority": 1},
    "MEDIUM":   {"color": "#F97316", "priority": 2},
    "LOW":      {"color": "#EAB308", "priority": 3},
    "CLEAN":    {"color": "#10B981", "priority": 4},
}

# ──────────────────────────────────────────────────────────────────────────────
# SYNTHETIC HEALTHY BASELINE GENERATOR
# Used to train the One-Class SVM on "normal" operational patterns.
# Healthy profile: engine hours 2.0-12.0h, idle hours 0.2-2.5h (warm-up/cool-down),
# IER < 45%, non-zero engine activity.
# ──────────────────────────────────────────────────────────────────────────────
def generate_healthy_baseline(n: int = 1000) -> np.ndarray:
    """
    Generates synthetic healthy fleet records for SVM training.
    Features per record: [engine_hours_per_day, idle_hours_per_day, ier_pct]

    Healthy operating norms:
      - Engine hours: 2.0 – 12.0 h/day (active productive work)
      - Idle hours:   0.2 – 2.5 h/day  (standard engine warm-up & cool-down range)
      - IER:          < 45% (idle hours strictly less than engine hours)
    """
    rng = np.random.default_rng(seed=42)
    engine_h = rng.uniform(2.0, 12.0, size=n)
    idle_h   = rng.uniform(0.2, 2.5,  size=n)
    # Ensure idle_h is strictly less than engine_h
    idle_h   = np.minimum(idle_h, engine_h * 0.45)
    total    = engine_h + idle_h
    ier_pct  = (idle_h / total) * 100.0
    return np.column_stack([engine_h, idle_h, ier_pct])


# ──────────────────────────────────────────────────────────────────────────────
# LAYER 1 — DETERMINISTIC RULE ENGINE
# ──────────────────────────────────────────────────────────────────────────────
def apply_rule_engine(log) -> list[dict]:
    """
    Evaluate hard operational boundaries for a single RentalLog record.
    Returns a list of rule violation dicts; empty list = no violations.
    """
    violations = []
    engine_h = log.engine_hours_per_day or 0.0
    idle_h   = log.idle_hours_per_day   or 0.0
    total    = engine_h + idle_h
    ier_pct  = round((idle_h / total * 100.0) if total > 0 else 0.0, 2)

    # ── Rule 1: Ghost / Phantom Idling ────────────────────────────────────────
    # Engine Hours = 0 while Idle Hours > 0  →  ignition on, engine NOT running
    if engine_h == 0.0 and idle_h > 0.0:
        violations.append({
            "flag":        "GHOST_IDLING",
            "severity":    "CRITICAL",
            "title":       "Ghost / Phantom Idling",
            "description": (
                f"Ignition is active (Idle = {idle_h}h) but Engine Hours = 0. "
                "Engine is NOT running — indicates phantom ignition or telematics fault. "
                "Possible unauthorized/unlogged use."
            ),
            "detected_value": f"Engine: 0h | Idle: {idle_h}h",
            "boundary":       "Engine Hours must be > 0 when Idle Hours > 0",
        })

    # ── Rule 2: Constraint Violation — High IER ────────────────────────────────
    # Idle Hours >= Engine Hours  →  IER >= 50%
    if idle_h >= engine_h and engine_h > 0.0:
        violations.append({
            "flag":        "CONSTRAINT_VIOLATION_HIGH_IER",
            "severity":    "HIGH",
            "title":       "Constraint Violation — High Idle-to-Engine Ratio",
            "description": (
                f"Idle Hours ({idle_h}h) ≥ Engine Hours ({engine_h}h). "
                f"IER = {ier_pct}% — indicates excessive key-on idling, "
                "wasted fuel, and inefficient site operations."
            ),
            "detected_value": f"IER: {ier_pct}% (Idle {idle_h}h ≥ Engine {engine_h}h)",
            "boundary":       "Idle Hours must be < Engine Hours (IER < 50%)",
        })

    # ── Rule 3: Unassigned Asset Usage ────────────────────────────────────────
    # Active telemetry (engine or idle > 0) while Site ID = NULL
    if (engine_h > 0.0 or idle_h > 0.0) and log.site_id is None:
        violations.append({
            "flag":        "UNASSIGNED_USAGE",
            "severity":    "CRITICAL",
            "title":       "Unassigned Asset Usage — No Site",
            "description": (
                f"Equipment shows active telemetry (Engine: {engine_h}h, Idle: {idle_h}h) "
                "but Site ID is NULL. Asset is operating without a valid site assignment. "
                "Security and accountability risk."
            ),
            "detected_value": "Site ID = NULL with active engine/idle telemetry",
            "boundary":       "All active equipment must have a valid Site ID",
        })

    # ── Rule 4: Missing Operator ───────────────────────────────────────────────
    # Equipment operating (engine > 0 OR idle > 0) with Operator ID = NULL
    if (engine_h > 0.0 or idle_h > 0.0) and log.operator_id is None:
        violations.append({
            "flag":        "MISSING_OPERATOR",
            "severity":    "CRITICAL",
            "title":       "Missing Operator Assignment",
            "description": (
                f"Equipment shows active telemetry (Engine: {engine_h}h, Idle: {idle_h}h) "
                "but Operator ID is NULL. No licensed operator is assigned. "
                "Operational safety and insurance compliance risk."
            ),
            "detected_value": "Operator ID = NULL with active engine/idle telemetry",
            "boundary":       "All active equipment must have an assigned Operator",
        })

    return violations


# ──────────────────────────────────────────────────────────────────────────────
# LAYER 2 SVM OUTLIER EXPLAINER — Data-Driven Feature Diagnosis
# ──────────────────────────────────────────────────────────────────────────────
def explain_svm_outlier(engine_h: float, idle_h: float, ier_pct: float, eq_type: str) -> dict:
    """
    Analyzes telemetry parameters to generate a specific human-readable explanation
    for why the One-Class SVM flagged a record as a behavioral outlier.
    """
    if engine_h > 0 and idle_h == 0:
        return {
            "reason": "Insufficient Engine Warm-up / Cool-down Time (0.0h Idle)",
            "description": (
                f"{eq_type} operated for {engine_h}h active engine hours with 0.0h recorded idle time. "
                "Standard operating procedure requires 0.2h to 2.5h daily idle for engine warm-up, cool-down, and thermal stabilization. "
                "Operating without warm-up/cool-down risks engine wear or indicates telematics idle sensor bypass."
            )
        }
    elif idle_h > 2.5:
        return {
            "reason": f"Excessive Idling Beyond Healthy Range ({idle_h}h Idle > 2.5h Limit)",
            "description": (
                f"Recorded idle time of {idle_h}h exceeds the normal daily warm-up/cool-down allowance (0.2h to 2.5h). "
                f"With IER at {ier_pct}%, this represents unproductive key-on idling, wasted fuel, and site inefficiency."
            )
        }
    elif engine_h < 2.0 and idle_h > 0:
        return {
            "reason": "Low-Engine High-Ratio Duty Cycle",
            "description": (
                f"Only {engine_h}h active engine work logged with {idle_h}h idle time. "
                "Low active runtime combined with high proportional idle creates an anomalous duty cycle signature."
            )
        }
    elif engine_h > 12.0:
        return {
            "reason": "Unusual Heavy Duty Cycle (>12h Engine)",
            "description": (
                f"Active engine hours of {engine_h}h/day significantly exceed normal single-shift operating norms (2-12h/day). "
                "Indicates continuous high-intensity shift usage outside baseline operational profile."
            )
        }
    else:
        return {
            "reason": "Non-Linear Multi-Dimensional Behavioral Outlier",
            "description": (
                f"Statistical outlier in 3D feature space (Engine: {engine_h}h, Idle: {idle_h}h, IER: {ier_pct}%). "
                f"{eq_type} operating pattern deviates from the cluster of healthy baseline equipment norms."
            )
        }


# ──────────────────────────────────────────────────────────────────────────────
# SEVERITY RESOLVER — combines Layer 1 + Layer 2 into final label
# ──────────────────────────────────────────────────────────────────────────────
def resolve_severity(rule_violations: list, svm_outlier: bool) -> str:
    if not rule_violations and not svm_outlier:
        return "CLEAN"

    flags = {v["flag"] for v in rule_violations}
    severities = {v["severity"] for v in rule_violations}

    # Any CRITICAL rule (GHOST_IDLING, UNASSIGNED_USAGE, MISSING_OPERATOR) → CRITICAL
    if "CRITICAL" in severities:
        return "CRITICAL"

    # CONSTRAINT_VIOLATION + SVM outlier together → HIGH
    if "CONSTRAINT_VIOLATION_HIGH_IER" in flags and svm_outlier:
        return "HIGH"

    if "HIGH" in severities:
        return "HIGH"

    # SVM outlier alone (no rule violation) → MEDIUM behavioral anomaly
    if svm_outlier:
        return "MEDIUM"

    return "LOW"


# ──────────────────────────────────────────────────────────────────────────────
# SCAN ENDPOINT
# ──────────────────────────────────────────────────────────────────────────────
@router.get("/scan")
def run_anomaly_scan(db: Session = Depends(get_db)):
    """
    Scan all rental_logs records through the two-tier anomaly detection pipeline.

    Returns per-record results with Layer 1 rule flags and Layer 2 SVM outlier
    classification, combined severity, and full diagnostic breakdown.
    """
    logs = db.query(RentalLog).all()

    if not logs:
        return {
            "summary": {
                "total_scanned": 0, "anomaly_count": 0,
                "rule_violation_count": 0, "svm_outlier_count": 0, "clean_count": 0,
            },
            "anomalies": [],
            "severity_breakdown": {},
            "pipeline_config": {},
        }

    # ── Build feature matrix from real DB records ────────────────────────────
    # Features: [engine_hours_per_day, idle_hours_per_day, ier_pct]
    feature_matrix = []
    for log in logs:
        engine_h = log.engine_hours_per_day or 0.0
        idle_h   = log.idle_hours_per_day   or 0.0
        total    = engine_h + idle_h
        ier_pct  = (idle_h / total * 100.0) if total > 0 else 0.0
        feature_matrix.append([engine_h, idle_h, ier_pct])
    X_real = np.array(feature_matrix)

    # ── Train One-Class SVM on synthetic healthy baseline ────────────────────
    X_train = generate_healthy_baseline(600)
    scaler  = StandardScaler()
    scaler.fit(X_train)

    X_train_scaled = scaler.transform(X_train)
    X_real_scaled  = scaler.transform(X_real)

    svm = OneClassSVM(kernel="rbf", nu=0.05, gamma="scale")
    svm.fit(X_train_scaled)

    svm_predictions = svm.predict(X_real_scaled)          # +1 = normal, -1 = outlier
    svm_scores      = svm.decision_function(X_real_scaled) # signed distance from boundary

    # ── Process every record ─────────────────────────────────────────────────
    results = []
    rule_violation_count = 0
    svm_outlier_count    = 0
    severity_breakdown   = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "CLEAN": 0}

    for i, log in enumerate(logs):
        engine_h = log.engine_hours_per_day or 0.0
        idle_h   = log.idle_hours_per_day   or 0.0
        total    = engine_h + idle_h
        ier_pct  = round((idle_h / total * 100.0) if total > 0 else 0.0, 2)

        # Enrich with FK lookups
        eq   = db.query(Equipment).filter(Equipment.equipment_id == log.equipment_id).first()
        site = db.query(Site).filter(Site.site_id == log.site_id).first() if log.site_id else None
        op   = db.query(Operator).filter(Operator.operator_id == log.operator_id).first() if log.operator_id else None

        # Layer 1
        rule_violations    = apply_rule_engine(log)
        has_rule_violation = len(rule_violations) > 0
        if has_rule_violation:
            rule_violation_count += 1

        # Layer 2
        is_svm_outlier = int(svm_predictions[i]) == -1
        
        # Override: 0.2h to 2.5h of idle time is standard warm-up/cool-down, never an outlier
        if 0.2 <= idle_h <= 2.5 and engine_h >= 2.0 and ier_pct < 50.0:
            is_svm_outlier = False
        # Override: idle_h == 0.0 with active engine is always flagged (insufficient warm-up/cool-down)
        elif idle_h == 0.0 and engine_h > 0.0:
            is_svm_outlier = True
            
        svm_score      = round(float(svm_scores[i]), 4)
        svm_explanation = explain_svm_outlier(engine_h, idle_h, ier_pct, eq.type if eq else "Equipment") if is_svm_outlier else None
        if is_svm_outlier:
            svm_outlier_count += 1

        # Combined severity
        severity = resolve_severity(rule_violations, is_svm_outlier)
        severity_breakdown[severity] = severity_breakdown.get(severity, 0) + 1

        # Build flag list for frontend display
        flags = [v["flag"] for v in rule_violations]
        if is_svm_outlier:
            flags.append("BEHAVIORAL_OUTLIER")

        results.append({
            "rental_id":        log.rental_id,
            "equipment_id":     log.equipment_id,
            "equipment_type":   eq.type if eq else "Unknown",
            "site_id":          log.site_id,
            "site_name":        site.site_name if site else "UNASSIGNED",
            "location":         site.location  if site else "N/A",
            "operator_id":      log.operator_id,
            "operator_name":    op.name         if op   else "UNASSIGNED",
            "operator_contact": op.contact_info if op   else "N/A",
            "check_in_date":    str(log.check_in_date),
            "check_out_date":   str(log.check_out_date),
            "rental_days":      log.rental_days,
            # Telemetry metrics
            "engine_hours_per_day": engine_h,
            "idle_hours_per_day":   idle_h,
            "ier_pct":              ier_pct,
            # Layer 1
            "layer1_violations":  rule_violations,
            "has_rule_violation": has_rule_violation,
            # Layer 2
            "layer2_svm_outlier":  is_svm_outlier,
            "svm_decision_score":  svm_score,
            "svm_reason":          svm_explanation["reason"] if svm_explanation else None,
            "svm_description":     svm_explanation["description"] if svm_explanation else None,
            # Combined
            "flags":          flags,
            "severity":       severity,
            "severity_color": SEVERITY_MAP.get(severity, {}).get("color", "#64748b"),
            "is_anomaly":     severity != "CLEAN",
        })

    # Sort: CRITICAL first, CLEAN last
    severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "CLEAN": 4}
    results.sort(key=lambda x: severity_order.get(x["severity"], 99))

    clean_count   = severity_breakdown.get("CLEAN", 0)
    anomaly_count = len(logs) - clean_count

    return {
        "summary": {
            "total_scanned":       len(logs),
            "anomaly_count":       anomaly_count,
            "rule_violation_count": rule_violation_count,
            "svm_outlier_count":   svm_outlier_count,
            "clean_count":         clean_count,
        },
        "severity_breakdown": severity_breakdown,
        "pipeline_config": {
            "layer1_rules": [
                "GHOST_IDLING (Engine=0 & Idle>0)",
                "CONSTRAINT_VIOLATION_HIGH_IER (Idle >= Engine, IER >= 50%)",
                "UNASSIGNED_USAGE (Active telemetry + Site ID=NULL)",
                "MISSING_OPERATOR (Active telemetry + Operator ID=NULL)",
            ],
            "layer2_svm": {
                "kernel":           "rbf",
                "nu":               0.05,
                "gamma":            "scale",
                "training_samples": 600,
                "features":         ["engine_hours_per_day", "idle_hours_per_day", "ier_pct"],
                "training_source":  "Synthetic healthy baseline (IER < 40%, engine 4-12h/day)",
            },
            "ier_violation_threshold_pct": IER_VIOLATION_THRESHOLD,
        },
        "anomalies": results,
    }
