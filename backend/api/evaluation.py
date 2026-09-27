"""SELORA Evaluation API (metrics re-retrieval endpoints)"""
from fastapi import APIRouter
router = APIRouter()
# Metrics are served via /api/registration/{id}/metrics in registration.py
# This module can be extended for batch evaluation endpoints
