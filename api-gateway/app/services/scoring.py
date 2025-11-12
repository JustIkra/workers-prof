"""
Scoring service for calculating professional fitness scores (S2-02, S2-03, AI-03).

Implements:
- Formula: score_pct = Σ(value × weight) × 10
- Strengths/dev_areas generation (S2-03)
- AI recommendations generation (AI-03)

With Decimal precision and quantization to 0.01.
"""

from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Union
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.clients import GeminiClient, GeminiPoolClient
from app.repositories.metric import ExtractedMetricRepository
from app.repositories.participant_metric import ParticipantMetricRepository
from app.repositories.prof_activity import ProfActivityRepository
from app.repositories.scoring_result import ScoringResultRepository


class ScoringService:
    """Service for calculating professional fitness scores."""

    def __init__(
        self, db: AsyncSession, gemini_client: Union[GeminiClient, GeminiPoolClient, None] = None
    ):
        self.db = db
        self.gemini_client = gemini_client
        self.extracted_metric_repo = ExtractedMetricRepository(db)  # Legacy, for backward compatibility
        self.participant_metric_repo = ParticipantMetricRepository(db)  # S2-08: New storage
        self.prof_activity_repo = ProfActivityRepository(db)
        self.scoring_result_repo = ScoringResultRepository(db)

    async def calculate_score(
        self,
        participant_id: UUID,
        prof_activity_code: str,
        report_ids: list[UUID] | None = None,
    ) -> dict:
        """
        Calculate professional fitness score for a participant.

        Args:
            participant_id: UUID of the participant
            prof_activity_code: Code of the professional activity
            report_ids: Optional list of report IDs to use for metrics.
                       If None, uses all reports for the participant.

        Returns:
            Dictionary with:
                - score_pct: Decimal score as percentage (0-100), quantized to 0.01
                - details: List of metric contributions
                - missing_metrics: List of metrics without extracted values

        Raises:
            ValueError: If no active weight table or required metrics are missing
        """
        # 1. Get professional activity
        prof_activity = await self.prof_activity_repo.get_by_code(prof_activity_code)
        if not prof_activity:
            raise ValueError(f"Professional activity '{prof_activity_code}' not found")

        # 2. Get active weight table
        weight_table = await self.prof_activity_repo.get_active_weight_table(prof_activity.id)
        if not weight_table:
            raise ValueError(f"No active weight table for activity '{prof_activity_code}'")

        # 3. Parse weights from JSONB
        weights_map = {}  # metric_code -> weight
        for weight_entry in weight_table.weights:
            metric_code = weight_entry["metric_code"]
            weight = Decimal(weight_entry["weight"])
            weights_map[metric_code] = weight

        # 4. Validate sum of weights == 1.0
        total_weight = sum(weights_map.values())
        if total_weight != Decimal("1.0"):
            raise ValueError(f"Sum of weights must equal 1.0, got {total_weight}")

        # 5. Get participant metrics (S2-08: from participant_metric table)
        metrics_map = await self.participant_metric_repo.get_metrics_dict(participant_id)

        # 5b. Load MetricDef for names (needed for strengths/dev_areas/recommendations)
        from app.repositories.metric import MetricDefRepository

        metric_def_repo = MetricDefRepository(self.db)
        metric_defs = await metric_def_repo.list_all(active_only=True)
        metric_def_by_code = {m.code: m for m in metric_defs}

        # 6. Check for missing required metrics
        missing_metrics = []
        for metric_code in weights_map.keys():
            if metric_code not in metrics_map:
                missing_metrics.append(metric_code)

        if missing_metrics:
            raise ValueError(
                f"Missing extracted metrics for: {', '.join(missing_metrics)}. "
                f"Please ensure all reports are processed and metrics are extracted."
            )

        # 7. Calculate score: Σ(value × weight) × 10
        score_sum = Decimal("0")
        details = []

        for metric_code, weight in weights_map.items():
            value = metrics_map[metric_code]

            # Validate value is in range [1..10]
            if not (Decimal("1") <= value <= Decimal("10")):
                raise ValueError(f"Metric '{metric_code}' value {value} is out of range [1..10]")

            contribution = value * weight
            score_sum += contribution

            details.append(
                {
                    "metric_code": metric_code,
                    "value": str(value),
                    "weight": str(weight),
                    "contribution": str(
                        contribution.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                    ),
                }
            )

        # Final score as percentage: score × 10
        score_pct = (score_sum * Decimal("10")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # 8. Generate strengths and development areas (S2-03)
        strengths, dev_areas = self._generate_strengths_and_dev_areas(
            metrics_map=metrics_map,
            weights_map=weights_map,
            metric_def_by_code=metric_def_by_code,
        )

        # 9. Generate AI recommendations (AI-08) - async via Celery
        # Save scoring result first, then trigger async recommendations generation
        recommendations = None
        recommendations_status = "pending"
        if not settings.ai_recommendations_enabled or self.gemini_client is None:
            recommendations_status = "disabled"

        # 10. Save scoring result to database (without recommendations initially)
        scoring_result = await self.scoring_result_repo.create(
            participant_id=participant_id,
            weight_table_id=weight_table.id,
            score_pct=score_pct,
            strengths=strengths,
            dev_areas=dev_areas,
            recommendations=None,  # Will be updated by Celery task
            compute_notes="Score calculated using current weight table",
            recommendations_status=recommendations_status,
        )

        # 11. Trigger async recommendations generation (AI-08)
        if recommendations_status == "pending":
            from app.tasks.recommendations import generate_report_recommendations

            # Launch Celery task
            task = generate_report_recommendations.delay(
                scoring_result_id=str(scoring_result.id),
            )

            # In eager mode (tests/CI), wait for result synchronously
            if settings.celery_task_always_eager:
                try:
                    task.get(timeout=30)
                    # Refresh scoring_result from DB to get updated recommendations
                    await self.db.refresh(scoring_result)
                    recommendations = scoring_result.recommendations
                    recommendations_status = scoring_result.recommendations_status
                except Exception as e:
                    # Log error but don't fail scoring calculation
                    import logging

                    logger = logging.getLogger(__name__)
                    logger.warning(
                        f"Recommendations generation failed in eager mode: {e}",
                        exc_info=True,
                    )
                    recommendations_status = "error"
                    scoring_result.recommendations_status = "error"
                    scoring_result.recommendations_error = str(e)
                    await self.db.commit()
                    await self.db.refresh(scoring_result)
                    recommendations = scoring_result.recommendations

        return {
            "scoring_result_id": str(scoring_result.id),
            "score_pct": score_pct,
            "details": details,
            "weight_table_id": str(weight_table.id),
            "missing_metrics": [],
            "prof_activity_id": str(prof_activity.id),
            "prof_activity_name": prof_activity.name,
            "strengths": strengths,
            "dev_areas": dev_areas,
            "recommendations": recommendations,
            "recommendations_status": recommendations_status,
            "recommendations_error": scoring_result.recommendations_error,
        }

    def _generate_strengths_and_dev_areas(
        self,
        metrics_map: dict[str, Decimal],
        weights_map: dict[str, Decimal],
        metric_def_by_code: dict[str, Any],
    ) -> tuple[list[dict], list[dict]]:
        """
        Generate strengths and development areas from metrics (S2-03).

        Logic:
        - Strengths: Top-5 metrics with highest values
        - Dev areas: Top-5 metrics with lowest values
        - Stable sorting: primary by value, secondary by metric_code

        Args:
            metrics_map: Mapping of metric_code -> value
            weights_map: Mapping of metric_code -> weight (for reference)
            metric_def_by_code: Mapping of metric_code -> MetricDef

        Returns:
            Tuple of (strengths, dev_areas) as JSONB-compatible lists

        AC:
        - Each list has ≤5 elements
        - Stable sorting by value then code
        - No duplicates
        - Deterministic/reproducible
        """
        # Build list of metric items with all necessary data
        metric_items = []
        for metric_code, value in metrics_map.items():
            metric_def = metric_def_by_code.get(metric_code)
            if metric_def and metric_code in weights_map:
                metric_items.append(
                    {
                        "metric_code": metric_code,
                        "metric_name": metric_def.name,
                        "value": str(value),
                        "weight": str(weights_map[metric_code]),
                    }
                )

        # Sort for strengths: highest value first, then by code (ascending) for stability
        strengths_sorted = sorted(
            metric_items,
            key=lambda x: (-Decimal(x["value"]), x["metric_code"]),
        )
        strengths = strengths_sorted[:5]

        # Sort for dev_areas: lowest value first, then by code (ascending) for stability
        dev_areas_sorted = sorted(
            metric_items,
            key=lambda x: (Decimal(x["value"]), x["metric_code"]),
        )
        dev_areas = dev_areas_sorted[:5]

        return strengths, dev_areas

    async def generate_final_report(
        self,
        participant_id: UUID,
        prof_activity_code: str,
    ) -> dict:
        """
        Generate final report data for a participant (S2-04).

        Args:
            participant_id: UUID of the participant
            prof_activity_code: Code of the professional activity

        Returns:
            Dictionary with final report data ready for JSON/HTML rendering

        Raises:
            ValueError: If no scoring result found or required data is missing
        """
        from app.repositories.participant import ParticipantRepository

        # 1. Get professional activity
        prof_activity = await self.prof_activity_repo.get_by_code(prof_activity_code)
        if not prof_activity:
            raise ValueError(f"Professional activity '{prof_activity_code}' not found")

        # 2. Get active weight table
        weight_table = await self.prof_activity_repo.get_active_weight_table(prof_activity.id)
        if not weight_table:
            raise ValueError(f"No active weight table for activity '{prof_activity_code}'")

        # 3. Get latest scoring result
        scoring_result = await self.scoring_result_repo.get_latest_by_participant_and_weight_table(
            participant_id=participant_id,
            weight_table_id=weight_table.id,
        )
        if not scoring_result:
            raise ValueError(
                f"No scoring result found for participant {participant_id} and activity '{prof_activity_code}'. "
                f"Please calculate score first."
            )

        # 4. Get participant details
        participant_repo = ParticipantRepository(self.db)
        participant = await participant_repo.get_by_id(participant_id)
        if not participant:
            raise ValueError(f"Participant {participant_id} not found")

        # 5. Get participant metrics with details (value, confidence) - S2-08
        participant_metrics = await self.participant_metric_repo.list_by_participant(participant_id)

        # Create metric_code -> ParticipantMetric mapping
        metrics_map = {}
        for metric in participant_metrics:
            metrics_map[metric.metric_code] = metric

        # 5b. Load MetricDef for names and units
        from app.repositories.metric import MetricDefRepository

        metric_def_repo = MetricDefRepository(self.db)
        metric_defs = await metric_def_repo.list_all(active_only=True)
        metric_def_by_code = {m.code: m for m in metric_defs}

        # 6. Parse weights from weight table
        weights_map = {}
        for weight_entry in weight_table.weights:
            metric_code = weight_entry["metric_code"]
            weight = Decimal(weight_entry["weight"])
            weights_map[metric_code] = weight

        # 7. Build detailed metrics list
        detailed_metrics = []
        for metric_code, weight in weights_map.items():
            if metric_code in metrics_map:
                metric = metrics_map[metric_code]
                metric_def = metric_def_by_code.get(metric_code)
                value = metric.value
                contribution = value * weight

                detailed_metrics.append(
                    {
                        "code": metric_code,
                        "name": metric_def.name if metric_def else metric_code,
                        "value": value,
                        "unit": metric_def.unit if metric_def else "балл",
                        "weight": weight,
                        "contribution": contribution.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
                        "source": "LLM",  # Default source (S2-08: not stored in participant_metric)
                        "confidence": metric.confidence,
                    }
                )

        # Sort by code for consistency
        detailed_metrics.sort(key=lambda x: x["code"])

        # 8. Transform strengths to final report format
        strengths_items = []
        if scoring_result.strengths:
            for strength in scoring_result.strengths[:5]:  # Max 5
                metric_code = strength.get("metric_code")
                # Get metric name from MetricDef if not present or if it's a code
                metric_name = strength.get("metric_name")
                if not metric_name or metric_name == metric_code:
                    metric_def = metric_def_by_code.get(metric_code) if metric_code else None
                    metric_name = metric_def.name if metric_def else (metric_code or "Неизвестная метрика")
                
                strengths_items.append(
                    {
                        "title": metric_name,
                        "metric_codes": [metric_code] if metric_code else [],
                        "reason": f"Высокое значение: {strength['value']} (вес {strength['weight']})",
                    }
                )

        # 9. Transform dev_areas to final report format
        dev_areas_items = []
        if scoring_result.dev_areas:
            for dev_area in scoring_result.dev_areas[:5]:  # Max 5
                metric_code = dev_area.get("metric_code")
                # Get metric name from MetricDef if not present or if it's a code
                metric_name = dev_area.get("metric_name")
                if not metric_name or metric_name == metric_code:
                    metric_def = metric_def_by_code.get(metric_code) if metric_code else None
                    metric_name = metric_def.name if metric_def else (metric_code or "Неизвестная метрика")
                
                dev_areas_items.append(
                    {
                        "title": metric_name,
                        "metric_codes": [metric_code] if metric_code else [],
                        "actions": [
                            "Рекомендуется уделить внимание развитию данной компетенции",
                            "Обратитесь к специалисту за персональными рекомендациями",
                        ],
                    }
                )

        # 10. Calculate average confidence for notes (S2-08: from participant_metrics)
        confidences = [m.confidence for m in participant_metrics if m.confidence is not None]
        avg_confidence = sum(confidences) / len(confidences) if confidences else None

        notes = f"OCR confidence средний: {avg_confidence:.2f}; " if avg_confidence else ""
        notes += f"Версия алгоритма расчета: weight_table {weight_table.id}"
        if scoring_result.compute_notes:
            notes += f"; {scoring_result.compute_notes}"

        recommendations_list = scoring_result.recommendations or []

        return {
            # Header
            "participant_id": participant_id,
            "participant_name": participant.full_name,
            "report_date": scoring_result.computed_at,
            "prof_activity_code": prof_activity_code,
            "prof_activity_name": prof_activity.name,
            "weight_table_id": str(weight_table.id),
            # Score
            "score_pct": scoring_result.score_pct,
            # Strengths and dev areas
            "strengths": strengths_items,
            "dev_areas": dev_areas_items,
            # Recommendations (AI-generated when available)
            "recommendations": recommendations_list,
            "recommendations_status": scoring_result.recommendations_status,
            "recommendations_error": scoring_result.recommendations_error,
            # Metrics
            "metrics": detailed_metrics,
            # Notes
            "notes": notes,
            # Template version
            "template_version": "1.0.0",
        }
