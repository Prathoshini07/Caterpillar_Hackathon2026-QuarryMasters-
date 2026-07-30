"""
backend/routers/forecast.py
============================
FastAPI Router for Caterpillar Demand Forecasting API.
Prefix: /api/forecast
"""
import datetime
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import DemandForecast
from ml.prediction_service import prediction_service

router = APIRouter(
    prefix="/api/forecast",
    tags=["Demand Forecast"]
)


@router.get("/status")
def get_forecast_status(db: Session = Depends(get_db)):
    """Returns ML demand forecasting service and model loading status."""
    try:
        status_info = prediction_service.get_status(db)
        if not status_info.get("model_loaded"):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Demand forecasting model not loaded: {status_info.get('error', 'Unknown error')}"
            )
        return status_info
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve forecast status: {str(e)}"
        )


@router.get("/all")
def get_all_forecasts(db: Session = Depends(get_db)):
    """Returns demand forecasts for all site and equipment combinations (60 series)."""
    try:
        return prediction_service.predict_all_sites(db)
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate forecasts: {str(e)}"
        )


@router.get("/shortages")
def get_shortage_forecasts(db: Session = Depends(get_db)):
    """Returns demand forecasts where shortage_risk is True."""
    try:
        return prediction_service.get_shortages(db)
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve shortage forecasts: {str(e)}"
        )


@router.get("/site/{site_id}")
def get_site_forecasts(site_id: str, db: Session = Depends(get_db)):
    """Returns demand forecasts for all equipment types at a specific site."""
    try:
        return prediction_service.predict_site(site_id, db)
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e).strip("'\"")
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve site forecasts: {str(e)}"
        )


@router.get("/site/{site_id}/equipment/{equipment_type}")
def get_single_forecast(site_id: str, equipment_type: str, db: Session = Depends(get_db)):
    """Returns single demand forecast for specific site and equipment type."""
    try:
        return prediction_service.predict_single(site_id, equipment_type, db)
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e).strip("'\"")
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve forecast: {str(e)}"
        )


@router.post("/generate")
def generate_and_persist_forecasts(db: Session = Depends(get_db)):
    """Generates demand forecasts and performs idempotent upsert into demand_forecasts DB table."""
    try:
        forecasts = prediction_service.predict_all_sites(db)
        if not forecasts:
            return {
                "status": "success",
                "inserted_count": 0,
                "updated_count": 0,
                "forecast_date": ""
            }

        forecast_week_str = forecasts[0]["forecast_week"]
        target_date = datetime.datetime.strptime(forecast_week_str, "%Y-%m-%d").date()

        # Query existing forecasts for target date
        existing_records = db.query(DemandForecast).filter(
            DemandForecast.forecast_date == target_date
        ).all()
        existing_map = {(dfc.site_id, dfc.equipment_type): dfc for dfc in existing_records}

        inserted_count = 0
        updated_count = 0

        for item in forecasts:
            s_id = item["site_id"]
            eq_type = item["equipment_type"]
            pred_demand = item["predicted_demand"]

            key = (s_id, eq_type)
            if key in existing_map:
                existing_map[key].predicted_demand = pred_demand
                updated_count += 1
            else:
                fcast_id = f"FCAST_{s_id}_{eq_type}_{forecast_week_str}"
                new_dfc = DemandForecast(
                    forecast_id=fcast_id,
                    site_id=s_id,
                    equipment_type=eq_type,
                    predicted_demand=pred_demand,
                    forecast_date=target_date
                )
                db.add(new_dfc)
                inserted_count += 1

        db.commit()

        return {
            "status": "success",
            "inserted_count": inserted_count,
            "updated_count": updated_count,
            "forecast_date": forecast_week_str
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate and persist forecasts: {str(e)}"
        )
