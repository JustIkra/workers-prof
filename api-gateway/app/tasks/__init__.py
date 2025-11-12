"""
Celery tasks for background processing.
"""

# Import tasks to register with Celery
from app.tasks.extraction import extract_images_from_report  # noqa: F401
from app.tasks.recommendations import generate_report_recommendations  # noqa: F401

__all__ = ["extract_images_from_report", "generate_report_recommendations"]
