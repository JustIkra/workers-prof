"""
Service for rendering final report HTML templates (S2-04).

Uses Jinja2 for template rendering with versioning support.
"""

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape


# Template directory path
TEMPLATE_DIR = Path(__file__).parent.parent / "templates"


def get_jinja_env() -> Environment:
    """
    Get configured Jinja2 environment.

    Returns:
        Configured Jinja2 Environment instance
    """
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    return env


def render_final_report_html(report_data: dict[str, Any]) -> str:
    """
    Render final report as HTML.

    Args:
        report_data: Report data dictionary from ScoringService.generate_final_report()

    Returns:
        Rendered HTML string

    Template version: Embedded in report_data["template_version"]
    """
    env = get_jinja_env()

    # Get template version from data (default to 1.0.0)
    template_version = report_data.get("template_version", "1.0.0")

    # For now, we only have version 1.0.0
    # In future, could select template based on version
    template = env.get_template("final_report_v1.html")

    html = template.render(**report_data)
    return html
