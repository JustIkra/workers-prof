"""
Recommendations generator service using Gemini API (AI-03).

Implements:
- Structured prompt according to prompt-gemini-recommendations.md
- Self-heal JSON validation with retry
- Strict schema enforcement (≤5 items per section)
- Russian language output
"""

import json
import logging
from typing import Any, Union

from pydantic import ValidationError

from app.clients import GeminiClient, GeminiPoolClient
from app.clients.exceptions import GeminiClientError
from app.core.config import settings
from app.schemas.recommendations import (
    RecommendationsInput,
    RecommendationsResponse,
)

logger = logging.getLogger(__name__)


class RecommendationsGenerator:
    """
    Service for generating AI-powered recommendations using Gemini API.

    Features:
    - Structured prompts with JSON schema enforcement
    - Self-healing validation (retries on invalid JSON)
    - Automatic list truncation to ≤5 items per section
    - Russian language support
    """

    # System instructions for Gemini (from prompt-gemini-recommendations.md)
    SYSTEM_INSTRUCTIONS = """Ты эксперт по оценке компетенций и обучению взрослых.

Правила:
- Используй только переданные метрики, веса и итоговый процент.
- Не додумывай чисел; если данных не хватает — предложи нейтральные формулировки.
- Пиши по-русски, кратко и конкретно; избегай общих фраз.
- Строго верни ТОЛЬКО JSON по схеме; не добавляй текст вне JSON.
- Каждый список должен содержать максимум 5 элементов.
- Все названия и описания должны быть краткими (до 80 символов).
"""

    # JSON schema for response validation
    JSON_SCHEMA = {
        "type": "object",
        "required": ["strengths", "dev_areas", "recommendations"],
        "properties": {
            "strengths": {
                "type": "array",
                "maxItems": 5,
                "items": {
                    "type": "object",
                    "required": ["title", "metric_codes", "reason"],
                    "properties": {
                        "title": {"type": "string", "maxLength": 80},
                        "metric_codes": {
                            "type": "array",
                            "items": {"type": "string"},
                            "minItems": 1,
                        },
                        "reason": {"type": "string", "maxLength": 200},
                    },
                },
            },
            "dev_areas": {
                "type": "array",
                "maxItems": 5,
                "items": {
                    "type": "object",
                    "required": ["title", "metric_codes", "actions"],
                    "properties": {
                        "title": {"type": "string", "maxLength": 80},
                        "metric_codes": {
                            "type": "array",
                            "items": {"type": "string"},
                            "minItems": 1,
                        },
                        "actions": {
                            "type": "array",
                            "items": {"type": "string"},
                            "maxItems": 5,
                        },
                    },
                },
            },
            "recommendations": {
                "type": "array",
                "maxItems": 5,
                "items": {
                    "type": "object",
                    "required": ["title", "link_url", "priority"],
                    "properties": {
                        "title": {"type": "string", "maxLength": 80},
                        "link_url": {"type": "string", "maxLength": 500},
                        "priority": {"type": "integer", "minimum": 1, "maximum": 5},
                    },
                },
            },
        },
    }

    def __init__(self, gemini_client: Union[GeminiClient, GeminiPoolClient]):
        """
        Initialize recommendations generator.

        Args:
            gemini_client: Configured Gemini API client (single or pool)
        """
        self.client = gemini_client

    def _build_prompt(self, input_data: RecommendationsInput) -> str:
        """
        Build structured prompt for Gemini API.

        Args:
            input_data: Input data with metrics, score, and context

        Returns:
            Formatted prompt string
        """
        prof_activity_name = input_data.context.get("prof_activity", {}).get(
            "name", "не указано"
        )
        weight_table_version = input_data.context.get("weight_table", {}).get("version", "1")

        # Convert input to JSON string for inclusion in prompt
        input_dict = input_data.model_dump()
        input_json = json.dumps(input_dict, indent=2, ensure_ascii=False)

        prompt = f"""Ниже данные по метрикам и весам для профдеятельности "{prof_activity_name}" (версия весов {weight_table_version}). Сформируй рекомендации.

Инпут:
{input_json}

Верни только JSON по схеме:
{{
  "strengths": [
    {{"title": "string", "metric_codes": ["string"], "reason": "string"}}
  ],
  "dev_areas": [
    {{"title": "string", "metric_codes": ["string"], "actions": ["string"]}}
  ],
  "recommendations": [
    {{"title": "string", "link_url": "string", "priority": 1}}
  ]
}}

Требования:
- Каждый список: максимум 5 элементов
- title: максимум 80 символов
- reason: максимум 200 символов
- priority: 1 (высший) до 5 (низший)
- metric_codes: реальные коды из переданных метрик
- Пиши на русском языке
"""

        return prompt

    def _truncate_response(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Truncate lists to maximum 5 items and enforce length limits.

        This is a defensive measure if Gemini returns more than requested.

        Args:
            data: Raw JSON response from Gemini

        Returns:
            Truncated data
        """
        result = {}

        # Truncate strengths
        if "strengths" in data:
            result["strengths"] = [
                {
                    "title": str(item.get("title", ""))[:80],
                    "metric_codes": item.get("metric_codes", []),
                    "reason": str(item.get("reason", ""))[:200],
                }
                for item in data["strengths"][:5]
            ]

        # Truncate dev_areas
        if "dev_areas" in data:
            result["dev_areas"] = [
                {
                    "title": str(item.get("title", ""))[:80],
                    "metric_codes": item.get("metric_codes", []),
                    "actions": item.get("actions", [])[:5],
                }
                for item in data["dev_areas"][:5]
            ]

        # Truncate recommendations
        if "recommendations" in data:
            result["recommendations"] = [
                {
                    "title": str(item.get("title", ""))[:80],
                    "link_url": str(item.get("link_url", ""))[:500],
                    "priority": item.get("priority", 3),
                }
                for item in data["recommendations"][:5]
            ]

        return result

    async def generate(
        self,
        metrics: list[dict],
        score_pct: float,
        prof_activity_code: str,
        prof_activity_name: str,
        weight_table_version: int,
    ) -> RecommendationsResponse:
        """
        Generate recommendations using Gemini API.

        Args:
            metrics: List of metrics with code, name, value, weight
            score_pct: Overall score percentage (0-100)
            prof_activity_code: Professional activity code
            prof_activity_name: Professional activity name
            weight_table_version: Version of weight table used

        Returns:
            Validated recommendations response

        Raises:
            ValueError: If recommendations generation is disabled
            GeminiClientError: If API call fails after retries
            ValidationError: If response cannot be validated after self-heal attempts
        """
        # Check if recommendations are enabled
        if not settings.ai_recommendations_enabled:
            raise ValueError(
                "AI recommendations are disabled. "
                "Set AI_RECOMMENDATIONS_ENABLED=1 in .env to enable."
            )

        # Build input data
        input_data = RecommendationsInput(
            context={
                "language": "ru",
                "prof_activity": {
                    "code": prof_activity_code,
                    "name": prof_activity_name,
                },
                "weight_table": {"version": weight_table_version},
            },
            metrics=metrics,
            score_pct=score_pct,
        )

        # Build prompt
        prompt = self._build_prompt(input_data)

        logger.info(
            "recommendations_generation_start",
            extra={
                "prof_activity_code": prof_activity_code,
                "metrics_count": len(metrics),
                "score_pct": score_pct,
            },
        )

        # Try to generate with self-heal (max 2 attempts)
        max_attempts = 2
        last_error = None

        for attempt in range(1, max_attempts + 1):
            try:
                # Call Gemini API
                response = await self.client.generate_text(
                    prompt=prompt,
                    system_instructions=self.SYSTEM_INSTRUCTIONS,
                    response_mime_type="application/json",
                )

                # Extract text from response
                raw_text = self._extract_text_from_response(response)

                # Parse JSON
                try:
                    raw_json = json.loads(raw_text)
                except json.JSONDecodeError as e:
                    logger.warning(
                        "recommendations_json_parse_error",
                        extra={
                            "attempt": attempt,
                            "error": str(e),
                            "raw_text": raw_text[:200],
                        },
                    )

                    if attempt < max_attempts:
                        # Retry with self-heal prompt
                        prompt = self._build_self_heal_prompt(raw_text)
                        continue
                    else:
                        raise ValueError(f"Failed to parse JSON after {max_attempts} attempts") from e

                # Truncate if needed
                truncated_json = self._truncate_response(raw_json)

                # Validate with Pydantic
                recommendations = RecommendationsResponse(**truncated_json)

                logger.info(
                    "recommendations_generation_success",
                    extra={
                        "prof_activity_code": prof_activity_code,
                        "attempt": attempt,
                        "strengths_count": len(recommendations.strengths),
                        "dev_areas_count": len(recommendations.dev_areas),
                        "recommendations_count": len(recommendations.recommendations),
                    },
                )

                return recommendations

            except ValidationError as e:
                logger.warning(
                    "recommendations_validation_error",
                    extra={
                        "attempt": attempt,
                        "error": str(e),
                    },
                )

                last_error = e

                if attempt < max_attempts:
                    # Retry with more explicit instructions
                    prompt = self._build_self_heal_prompt(raw_text)
                    continue

            except GeminiClientError as e:
                logger.error(
                    "recommendations_api_error",
                    extra={
                        "attempt": attempt,
                        "error": str(e),
                    },
                )

                # Don't retry on API errors, let them bubble up
                raise

        # All attempts failed
        logger.error(
            "recommendations_generation_failed",
            extra={
                "prof_activity_code": prof_activity_code,
                "max_attempts": max_attempts,
            },
        )

        raise ValueError(
            f"Failed to generate valid recommendations after {max_attempts} attempts. "
            f"Last error: {last_error}"
        )

    def _extract_text_from_response(self, response: dict[str, Any]) -> str:
        """
        Extract text content from Gemini API response.

        Args:
            response: Raw API response

        Returns:
            Text content

        Raises:
            ValueError: If response format is unexpected
        """
        try:
            candidates = response.get("candidates", [])
            if not candidates:
                raise ValueError("No candidates in response")

            content = candidates[0].get("content", {})
            parts = content.get("parts", [])

            if not parts:
                raise ValueError("No parts in content")

            text = parts[0].get("text", "")

            if not text:
                raise ValueError("Empty text in response")

            return text

        except (KeyError, IndexError, TypeError) as e:
            raise ValueError(f"Unexpected response format: {e}") from e

    def _build_self_heal_prompt(self, invalid_json: str) -> str:
        """
        Build self-heal prompt for retry when JSON is invalid.

        Args:
            invalid_json: Invalid JSON response from previous attempt

        Returns:
            Self-heal prompt
        """
        return f"""Предыдущий ответ был невалидным JSON или не соответствовал схеме.

Невалидный ответ:
{invalid_json[:500]}

Пожалуйста, верни ТОЛЬКО валидный JSON строго по следующей схеме:
{{
  "strengths": [
    {{"title": "string (≤80 символов)", "metric_codes": ["CODE1"], "reason": "string (≤200 символов)"}}
  ],
  "dev_areas": [
    {{"title": "string (≤80 символов)", "metric_codes": ["CODE1"], "actions": ["action1", "action2"]}}
  ],
  "recommendations": [
    {{"title": "string (≤80 символов)", "link_url": "string (URL или пусто)", "priority": 1}}
  ]
}}

Требования:
- Каждый список: максимум 5 элементов
- Все тексты на русском языке
- Не добавляй ничего кроме JSON
- priority: от 1 (высший) до 5 (низший)
"""


async def generate_recommendations(
    gemini_client: Union[GeminiClient, GeminiPoolClient],
    metrics: list[dict],
    score_pct: float,
    prof_activity_code: str,
    prof_activity_name: str,
    weight_table_version: int,
) -> dict | None:
    """
    Convenience function to generate recommendations.

    Args:
        gemini_client: Configured Gemini API client
        metrics: List of metrics with code, name, value, weight
        score_pct: Overall score percentage (0-100)
        prof_activity_code: Professional activity code
        prof_activity_name: Professional activity name
        weight_table_version: Version of weight table used

    Returns:
        Dictionary with recommendations in ScoringResult format,
        or None if generation is disabled via AI_RECOMMENDATIONS_ENABLED=0

    Raises:
        ValueError: If API keys are not configured or response is invalid
        GeminiClientError: If Gemini API call fails after retries
    """
    if not settings.ai_recommendations_enabled:
        logger.info("recommendations_disabled")
        return None

    generator = RecommendationsGenerator(gemini_client)
    response = await generator.generate(
        metrics=metrics,
        score_pct=score_pct,
        prof_activity_code=prof_activity_code,
        prof_activity_name=prof_activity_name,
        weight_table_version=weight_table_version,
    )

    return response.to_scoring_result_format()
