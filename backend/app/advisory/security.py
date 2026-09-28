from __future__ import annotations
import os

def status() -> dict:
    origins=os.getenv("CORS_ORIGINS", "*")
    return {"cors_configured":origins != "*","cors_origins":origins.split(","),
            "production_ready":origins != "*","notes":["Set CORS_ORIGINS to explicit frontend origins before production.","Protect ingestion/admin routes with authentication and RBAC before deployment.","Never place API keys in source control."]}
