"""
backend/ml/test_inference_api.py
=================================
Service-level smoke test suite for Demand Forecast Prediction Service and API Endpoints.
Uses direct service and router calls to avoid httpx / TestClient dependency issues.

Run with:
    python -m ml.test_inference_api
"""
import sys
import datetime
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from database import SessionLocal
from models import DemandForecast
from ml.prediction_service import prediction_service
from routers.forecast import (
    get_forecast_status,
    get_all_forecasts,
    get_site_forecasts,
    get_single_forecast,
    get_shortage_forecasts,
    generate_and_persist_forecasts,
)


def run_tests():
    print("=================================================================")
    print("  CATERPILLAR DEMAND FORECASTING - INFERENCE & API SMOKE TESTS  ")
    print("=================================================================\n")

    db = SessionLocal()
    try:
        initial_forecast_count = db.query(DemandForecast).count()
        print(f"[INITIAL DB STATE] DemandForecast table rows: {initial_forecast_count}\n")

        # ── Test 1: Model loads once & artifact verification ──────────
        print("--- Test 1: Artifact Verification & Single Loading ---")
        prediction_service.load_model()
        assert prediction_service.is_loaded is True, "Prediction service failed to load!"
        assert prediction_service.metadata["selected_model_type"] == "direct"
        assert prediction_service.metadata["feature_set"] == "Enhanced Features"
        assert len(prediction_service.metadata["all_features_ordered"]) == 39
        assert prediction_service.strategy["displayed_forecast"]["increase_threshold"] == 0.05
        assert prediction_service.strategy["displayed_forecast"]["decrease_threshold"] == 0.10
        assert prediction_service.strategy["shortage_alert"]["increase_threshold"] == 0.20
        print("[PASS] Test 1: Artifact verification & single loading passed.")

        # ── Test 2: GET /api/forecast/status ─────────────────────────
        print("\n--- Test 2: forecast.get_forecast_status(db) ---")
        data = get_forecast_status(db)
        assert data["model_loaded"] is True
        assert data["selected_model_type"] == "direct"
        assert data["number_of_sites"] == 10
        assert data["number_of_equipment_types"] == 6
        print(f"[PASS] Test 2: Status endpoint returned valid metadata: {data}")

        # ── Test 3: GET /api/forecast/all ────────────────────────────
        print("\n--- Test 3: forecast.get_all_forecasts(db) ---")
        all_forecasts = get_all_forecasts(db)
        assert len(all_forecasts) == 60, f"Expected 60 forecasts, got {len(all_forecasts)}"

        sites_set = set()
        eq_set = set()
        for f in all_forecasts:
            assert "site_id" in f and "equipment_type" in f
            assert isinstance(f["predicted_demand"], int) and f["predicted_demand"] >= 0
            assert isinstance(f["raw_model_prediction"], float) and f["raw_model_prediction"] >= 0.0
            assert isinstance(f["additional_units_needed"], int) and f["additional_units_needed"] >= 0
            assert isinstance(f["shortage_risk"], bool)
            assert f["shortage_risk_level"] in ("HIGH", "MEDIUM", "LOW")

            s_date = datetime.datetime.strptime(f["source_week"], "%Y-%m-%d").date()
            f_date = datetime.datetime.strptime(f["forecast_week"], "%Y-%m-%d").date()
            assert (f_date - s_date).days == 7, "forecast_week is not 7 days after source_week!"

            sites_set.add(f["site_id"])
            eq_set.add(f["equipment_type"])

        assert len(sites_set) == 10, f"Expected 10 unique sites, got {len(sites_set)}"
        assert len(eq_set) == 6, f"Expected 6 unique equipment types, got {len(eq_set)}"
        print(f"[PASS] Test 3: GET /all returned 60 valid forecasts across 10 sites and 6 equipment types.")

        # ── Test 4: GET /api/forecast/site/{site_id} ─────────────────
        print("\n--- Test 4: forecast.get_site_forecasts('S001', db) ---")
        site_forecasts = get_site_forecasts("S001", db)
        assert len(site_forecasts) == 6, f"Expected 6 equipment forecasts for site S001, got {len(site_forecasts)}"
        assert all(f["site_id"] == "S001" for f in site_forecasts)

        # Invalid site -> HTTPException 404
        try:
            get_site_forecasts("INVALID_SITE", db)
            assert False, "Expected 404 for invalid site!"
        except Exception as e:
            assert getattr(e, "status_code", None) == 404, f"Expected status_code 404, got {e}"
        print("[PASS] Test 4: GET /site/S001 returned 6 forecasts and invalid site raised 404.")

        # ── Test 5: GET /api/forecast/site/{site_id}/equipment/{equipment_type} ──
        print("\n--- Test 5: forecast.get_single_forecast('S001', 'Excavator', db) ---")
        single_f = get_single_forecast("S001", "Excavator", db)
        assert single_f["site_id"] == "S001"
        assert single_f["equipment_type"] == "Excavator"

        # Invalid equipment -> HTTPException 404
        try:
            get_single_forecast("S001", "InvalidEquip", db)
            assert False, "Expected 404 for invalid equipment!"
        except Exception as e:
            assert getattr(e, "status_code", None) == 404, f"Expected status_code 404, got {e}"
        print(f"[PASS] Test 5: Single forecast endpoint returned valid response: {single_f}")

        # ── Test 6: GET /api/forecast/shortages ──────────────────────
        print("\n--- Test 6: forecast.get_shortage_forecasts(db) ---")
        shortage_forecasts = get_shortage_forecasts(db)
        assert all(f["shortage_risk"] is True for f in shortage_forecasts)
        print(f"[PASS] Test 6: GET /shortages returned {len(shortage_forecasts)} shortage alert rows (all shortage_risk=True).")

        # ── Test 7: Verify GET endpoints performed NO DB mutations ───
        print("\n--- Test 7: Verify GET Endpoints DB Mutation Safety ---")
        post_get_count = db.query(DemandForecast).count()
        assert post_get_count == initial_forecast_count, (
            f"GET endpoints mutated DB! Initial count: {initial_forecast_count}, Current: {post_get_count}"
        )
        print("[PASS] Test 7: GET endpoints performed ZERO database mutations.")

        # ── Test 8: POST /api/forecast/generate (Idempotence Test) ───
        print("\n--- Test 8: forecast.generate_and_persist_forecasts(db) & Idempotence ---")

        # First call -> insert or update
        data_p1 = generate_and_persist_forecasts(db)
        assert data_p1["status"] == "success"
        print(f"  First POST generate call result: {data_p1}")

        first_total = data_p1["inserted_count"] + data_p1["updated_count"]
        assert first_total == 60, f"Expected 60 records processed, got {first_total}"

        count_after_p1 = db.query(DemandForecast).count()
        print(f"  DemandForecast table rows after first POST: {count_after_p1}")

        # Second call -> MUST be idempotent (inserted_count == 0, updated_count == 60)
        data_p2 = generate_and_persist_forecasts(db)
        assert data_p2["status"] == "success"
        print(f"  Second POST generate call result: {data_p2}")

        assert data_p2["inserted_count"] == 0, f"Expected 0 inserts on second call, got {data_p2['inserted_count']}"
        assert data_p2["updated_count"] == 60, f"Expected 60 updates on second call, got {data_p2['updated_count']}"
        count_after_p2 = db.query(DemandForecast).count()
        assert count_after_p2 == count_after_p1, "Row count changed on second POST call!"

        print("[PASS] Test 8: POST /api/forecast/generate is strictly idempotent.")

        print("\n=================================================================")
        print("  ALL 8 SERVICE-LEVEL SMOKE TESTS PASSED SUCCESSFULLY!          ")
        print("=================================================================")

    finally:
        db.close()


if __name__ == "__main__":
    run_tests()
