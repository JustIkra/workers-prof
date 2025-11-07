"""
Scoring service for calculating professional fitness scores (S2-02, S2-03).

Implements:
- Formula: score_pct = Σ(value × weight) × 10
- Strengths/dev_areas generation (S2-03)

With Decimal precision and quantization to 0.01.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.metric import ExtractedMetricRepository
from app.repositories.prof_activity import ProfActivityRepository
from app.repositories.scoring_result import ScoringResultRepository


class ScoringService:
    """Service for calculating professional fitness scores."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.extracted_metric_repo = ExtractedMetricRepository(db)
        self.prof_activity_repo = ProfActivityRepository(db)
        self.scoring_result_repo = ScoringResultRepository(db)

    async def calculate_score(
        self,
        participant_id: UUID,
        prof_activity_code: str,
        report_ids: Optional[list[UUID]] = None,
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
                - weight_table_version: Version of the weight table used
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

        # 5. Get extracted metrics for the participant
        # TODO: Filter by report_ids if provided
        extracted_metrics = await self.extracted_metric_repo.get_by_participant(participant_id)

        # Create metric_code -> value mapping (using latest value if multiple)
        metrics_map = {}  # metric_code -> Decimal value
        for metric in extracted_metrics:
            metrics_map[metric.metric_def.code] = metric.value

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
                raise ValueError(
                    f"Metric '{metric_code}' value {value} is out of range [1..10]"
                )

            contribution = value * weight
            score_sum += contribution

            details.append({
                "metric_code": metric_code,
                "value": str(value),
                "weight": str(weight),
                "contribution": str(contribution.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            })

        # Final score as percentage: score × 10
        score_pct = (score_sum * Decimal("10")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # 8. Generate strengths and development areas (S2-03)
        strengths, dev_areas = self._generate_strengths_and_dev_areas(
            metrics_map=metrics_map,
            weights_map=weights_map,
            extracted_metrics=extracted_metrics,
        )

        # 9. Save scoring result to database
        scoring_result = await self.scoring_result_repo.create(
            participant_id=participant_id,
            weight_table_id=weight_table.id,
            score_pct=score_pct,
            strengths=strengths,
            dev_areas=dev_areas,
            compute_notes=f"Calculated using weight table version {weight_table.version}",
        )

        return {
            "scoring_result_id": str(scoring_result.id),
            "score_pct": score_pct,
            "details": details,
            "weight_table_version": weight_table.version,
            "missing_metrics": [],
            "prof_activity_id": str(prof_activity.id),
            "prof_activity_name": prof_activity.name,
            "strengths": strengths,
            "dev_areas": dev_areas,
        }

    def _generate_strengths_and_dev_areas(
        self,
        metrics_map: dict[str, Decimal],
        weights_map: dict[str, Decimal],
        extracted_metrics: list,
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
            extracted_metrics: List of ExtractedMetric objects with metric_def

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
        for metric in extracted_metrics:
            metric_code = metric.metric_def.code
            if metric_code in metrics_map:
                metric_items.append({
                    "metric_code": metric_code,
                    "metric_name": metric.metric_def.name,
                    "value": str(metrics_map[metric_code]),
                    "weight": str(weights_map.get(metric_code, Decimal("0"))),
                })

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

        # 5. Get extracted metrics with details (value, source, confidence)
        extracted_metrics = await self.extracted_metric_repo.get_by_participant(participant_id)

        # Create metric_code -> ExtractedMetric mapping
        metrics_map = {}
        for metric in extracted_metrics:
            metrics_map[metric.metric_def.code] = metric

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
                value = metric.value
                contribution = value * weight

                detailed_metrics.append({
                    "code": metric_code,
                    "name": metric.metric_def.name,
                    "value": value,
                    "unit": metric.metric_def.unit or "балл",
                    "weight": weight,
                    "contribution": contribution.quantize(Decimal("0.01")),
                    "source": metric.source,
                    "confidence": metric.confidence,
                })

        # Sort by code for consistency
        detailed_metrics.sort(key=lambda x: x["code"])

        # 8. Transform strengths to final report format
        strengths_items = []
        if scoring_result.strengths:
            for strength in scoring_result.strengths[:5]:  # Max 5
                strengths_items.append({
                    "title": strength["metric_name"],
                    "metric_codes": [strength["metric_code"]],
                    "reason": f"Высокое значение: {strength['value']} (вес {strength['weight']})",
                })

        # 9. Transform dev_areas to final report format
        dev_areas_items = []
        if scoring_result.dev_areas:
            for dev_area in scoring_result.dev_areas[:5]:  # Max 5
                dev_areas_items.append({
                    "title": dev_area["metric_name"],
                    "metric_codes": [dev_area["metric_code"]],
                    "actions": [
                        "Рекомендуется уделить внимание развитию данной компетенции",
                        "Обратитесь к специалисту за персональными рекомендациями",
                    ],
                })

        # 10. Calculate average confidence for notes
        confidences = [m.confidence for m in extracted_metrics if m.confidence is not None]
        avg_confidence = (
            sum(confidences) / len(confidences) if confidences else None
        )

        notes = f"OCR confidence средний: {avg_confidence:.2f}; " if avg_confidence else ""
        notes += f"Версия алгоритма расчета: weight_table v{weight_table.version}"
        if scoring_result.compute_notes:
            notes += f"; {scoring_result.compute_notes}"

        return {
            # Header
            "participant_id": participant_id,
            "participant_name": participant.full_name,
            "report_date": scoring_result.computed_at,
            "prof_activity_code": prof_activity_code,
            "prof_activity_name": prof_activity.name,
            "weight_table_version": weight_table.version,
            # Score
            "score_pct": scoring_result.score_pct,
            # Strengths and dev areas
            "strengths": strengths_items,
            "dev_areas": dev_areas_items,
            # Recommendations (placeholder for now, will be implemented in AI-03)
            "recommendations": scoring_result.recommendations or [],
            # Metrics
            "metrics": detailed_metrics,
            # Notes
            "notes": notes,
            # Template version
            "template_version": "1.0.0",
        }
