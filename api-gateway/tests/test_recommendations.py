"""
Tests for AI recommendations generator (AI-03).

Tests:
- Schema validation
- Self-heal JSON logic
- List truncation (≤5 items)
- Russian language output
- Integration with ScoringService
"""

import json
from typing import Any

import pytest
from pydantic import ValidationError

from app.clients import GeminiClient, GeminiTransport
from app.schemas.recommendations import (
    DevelopmentAreaItem,
    RecommendationItem,
    RecommendationsInput,
    RecommendationsResponse,
    StrengthItem,
)
from app.services.recommendations import RecommendationsGenerator


# ===== Mock Transport =====


class MockTransport(GeminiTransport):
    """Mock transport for testing without network calls."""

    def __init__(self):
        self.requests: list[dict[str, Any]] = []
        self.responses: list[dict[str, Any] | Exception] = []
        self.call_count = 0

    def add_response(self, response: dict[str, Any] | Exception) -> None:
        """Queue a response (or exception) for next request."""
        self.responses.append(response)

    async def request(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
        timeout: float = 30.0,
    ) -> dict[str, Any]:
        """Record request and return queued response."""
        self.requests.append(
            {
                "method": method,
                "url": url,
                "headers": headers,
                "json": json,
                "timeout": timeout,
            }
        )
        self.call_count += 1

        if not self.responses:
            raise RuntimeError("No responses queued in MockTransport")

        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


# ===== Schema Tests =====


@pytest.mark.unit
def test_strength_item_validation():
    """Test StrengthItem validation."""
    # Valid item
    item = StrengthItem(
        title="Высокая коммуникабельность",
        metric_codes=["COMMUNICATION_CLARITY"],
        reason="Показатель значительно превышает средний уровень",
    )
    assert item.title == "Высокая коммуникабельность"
    assert item.metric_codes == ["COMMUNICATION_CLARITY"]

    # Test max_length validation
    with pytest.raises(ValidationError):
        StrengthItem(
            title="x" * 81,  # Exceeds max_length=80
            metric_codes=["CODE"],
            reason="Test",
        )

    # Test whitespace stripping
    item = StrengthItem(
        title="  Test  ",
        metric_codes=["CODE"],
        reason="  Reason  ",
    )
    assert item.title == "Test"
    assert item.reason == "Reason"


@pytest.mark.unit
def test_development_area_item_validation():
    """Test DevelopmentAreaItem validation."""
    # Valid item
    item = DevelopmentAreaItem(
        title="Планирование",
        metric_codes=["PLANNING_ACCURACY"],
        actions=["Пройти курс по тайм-менеджменту", "Практиковать постановку целей"],
    )
    assert item.title == "Планирование"
    assert len(item.actions) == 2

    # Test max actions (≤5)
    item = DevelopmentAreaItem(
        title="Test",
        metric_codes=["CODE"],
        actions=["Action 1", "Action 2", "Action 3", "Action 4", "Action 5"],
    )
    assert len(item.actions) == 5

    # Exceeds max_length should fail
    with pytest.raises(ValidationError):
        DevelopmentAreaItem(
            title="Test",
            metric_codes=["CODE"],
            actions=["1", "2", "3", "4", "5", "6"],  # 6 items > max_length=5
        )


@pytest.mark.unit
def test_recommendation_item_validation():
    """Test RecommendationItem validation."""
    # Valid item
    item = RecommendationItem(
        title="Развитие навыков продаж",
        skill_focus="Коммуникация и убеждение",
        development_advice="Практикуйте активное слушание и задавайте открытые вопросы",
        recommended_formats=["воркшоп", "наставничество"],
    )
    assert item.title == "Развитие навыков продаж"
    assert item.skill_focus == "Коммуникация и убеждение"
    assert len(item.recommended_formats) == 2

    # Test with empty recommended_formats
    item = RecommendationItem(
        title="Test",
        skill_focus="Test skill",
        development_advice="Test advice",
    )
    assert item.recommended_formats == []

    # Test max length constraints
    item = RecommendationItem(
        title="A" * 80,
        skill_focus="B" * 120,
        development_advice="C" * 240,
        recommended_formats=["D" * 80] * 5,
    )
    assert len(item.title) == 80
    assert len(item.skill_focus) == 120
    assert len(item.development_advice) == 240
    assert len(item.recommended_formats) == 5


@pytest.mark.unit
def test_recommendations_response_validation():
    """Test RecommendationsResponse validation with constraints."""
    # Valid response
    response = RecommendationsResponse(
        strengths=[
            StrengthItem(title="Test 1", metric_codes=["CODE1"], reason="Reason 1"),
        ],
        dev_areas=[
            DevelopmentAreaItem(title="Test 2", metric_codes=["CODE2"], actions=["Action 1"]),
        ],
        recommendations=[
            RecommendationItem(title="Course 1", link_url="https://example.com", priority=1),
        ],
    )
    assert len(response.strengths) == 1
    assert len(response.dev_areas) == 1
    assert len(response.recommendations) == 1

    # Test max_length constraints (≤5 items per list)
    with pytest.raises(ValidationError):
        RecommendationsResponse(
            strengths=[
                StrengthItem(title=f"Test {i}", metric_codes=["CODE"], reason="Reason")
                for i in range(6)  # 6 items > max_length=5
            ],
            dev_areas=[],
            recommendations=[],
        )


@pytest.mark.unit
def test_recommendations_input_validation():
    """Test RecommendationsInput validation."""
    input_data = RecommendationsInput(
        context={
            "language": "ru",
            "prof_activity": {"code": "SALES", "name": "Продажи"},
            "weight_table": {"version": 1},
        },
        metrics=[
            {
                "code": "COMMUNICATION_CLARITY",
                "name": "Ясность речи",
                "unit": "балл",
                "value": 8.5,
                "weight": 0.15,
            }
        ],
        score_pct=78.4,
    )
    assert input_data.score_pct == 78.4
    assert len(input_data.metrics) == 1
    assert input_data.constraints["strengths_max"] == 5


@pytest.mark.unit
def test_recommendations_response_to_scoring_format():
    """Test conversion to ScoringResult JSONB format."""
    response = RecommendationsResponse(
        strengths=[
            StrengthItem(title="Test 1", metric_codes=["CODE1"], reason="Reason 1"),
        ],
        dev_areas=[
            DevelopmentAreaItem(title="Test 2", metric_codes=["CODE2"], actions=["Action 1"]),
        ],
        recommendations=[
            RecommendationItem(
                title="Развитие навыков",
                skill_focus="Коммуникация",
                development_advice="Практикуйте активное слушание",
                recommended_formats=["воркшоп"],
            ),
        ],
    )

    result = response.to_scoring_result_format()

    assert "strengths" in result
    assert "dev_areas" in result
    assert "recommendations" in result
    assert len(result["strengths"]) == 1
    assert result["strengths"][0]["title"] == "Test 1"
    assert result["recommendations"][0]["skill_focus"] == "Коммуникация"


# ===== Generator Tests =====


@pytest.mark.asyncio
@pytest.mark.unit
async def test_recommendations_generator_basic():
    """Test basic recommendations generation with mock transport."""
    # Create mock transport with valid JSON response
    mock_response = {
        "strengths": [
            {
                "title": "Высокая коммуникабельность",
                "metric_codes": ["COMMUNICATION_CLARITY"],
                "reason": "Значение 8.5 превышает средний уровень",
            }
        ],
        "dev_areas": [
            {
                "title": "Планирование",
                "metric_codes": ["PLANNING_ACCURACY"],
                "actions": ["Пройти курс по тайм-менеджменту"],
            }
        ],
        "recommendations": [
            {
                "title": "Развитие коммуникации",
                "skill_focus": "Устная коммуникация и презентации",
                "development_advice": "Практикуйте публичные выступления и работу с аудиторией",
                "recommended_formats": ["воркшоп", "наставничество"],
            }
        ],
    }

    transport = MockTransport()
    transport.add_response(
        {
            "candidates": [
                {
                    "content": {
                        "parts": [{"text": json.dumps(mock_response, ensure_ascii=False)}],
                    },
                }
            ]
        }
    )

    client = GeminiClient(api_key="test_key", transport=transport, offline=True)
    generator = RecommendationsGenerator(client)

    # Generate recommendations
    result = await generator.generate(
        metrics=[
            {
                "code": "COMMUNICATION_CLARITY",
                "name": "Ясность речи",
                "unit": "балл",
                "value": 8.5,
                "weight": 0.15,
            }
        ],
        score_pct=78.4,
        prof_activity_code="SALES",
        prof_activity_name="Продажи",
    )

    assert len(result.strengths) == 1
    assert result.strengths[0].title == "Высокая коммуникабельность"
    assert len(result.dev_areas) == 1
    assert len(result.recommendations) == 1


@pytest.mark.asyncio
@pytest.mark.unit
async def test_recommendations_generator_truncation():
    """Test that generator truncates lists exceeding 5 items."""
    # Mock response with 6 items in each list (should be truncated to 5)
    mock_response = {
        "strengths": [
            {"title": f"Strength {i}", "metric_codes": [f"CODE{i}"], "reason": f"Reason {i}"}
            for i in range(6)
        ],
        "dev_areas": [
            {"title": f"Area {i}", "metric_codes": [f"CODE{i}"], "actions": [f"Action {i}"]}
            for i in range(6)
        ],
        "recommendations": [
            {
                "title": f"Rec {i}",
                "skill_focus": f"Skill {i}",
                "development_advice": f"Advice {i}",
                "recommended_formats": ["воркшоп"],
            }
            for i in range(6)
        ],
    }

    transport = MockTransport()
    transport.add_response(
        {
            "candidates": [
                {
                    "content": {
                        "parts": [{"text": json.dumps(mock_response, ensure_ascii=False)}],
                    },
                }
            ]
        }
    )

    client = GeminiClient(api_key="test_key", transport=transport, offline=True)
    generator = RecommendationsGenerator(client)

    result = await generator.generate(
        metrics=[{"code": "CODE1", "name": "Test", "unit": "балл", "value": 5.0, "weight": 1.0}],
        score_pct=50.0,
        prof_activity_code="TEST",
        prof_activity_name="Test Activity",
    )

    # Should be truncated to 5 items each
    assert len(result.strengths) == 5
    assert len(result.dev_areas) == 5
    assert len(result.recommendations) == 5


@pytest.mark.asyncio
@pytest.mark.unit
async def test_recommendations_generator_self_heal():
    """Test self-heal logic when JSON is invalid."""
    transport = MockTransport()

    # First attempt: invalid JSON
    transport.add_response(
        {
            "candidates": [
                {
                    "content": {
                        "parts": [{"text": "This is not valid JSON"}],
                    },
                }
            ]
        }
    )

    # Second attempt: valid JSON (self-heal succeeds)
    valid_response = {
        "strengths": [
            {"title": "Test", "metric_codes": ["CODE"], "reason": "Healed successfully"}
        ],
        "dev_areas": [{"title": "Test", "metric_codes": ["CODE"], "actions": ["Action"]}],
        "recommendations": [
            {
                "title": "Test",
                "skill_focus": "Test skill",
                "development_advice": "Test advice",
                "recommended_formats": [],
            }
        ],
    }
    transport.add_response(
        {
            "candidates": [
                {
                    "content": {
                        "parts": [{"text": json.dumps(valid_response, ensure_ascii=False)}],
                    },
                }
            ]
        }
    )

    client = GeminiClient(api_key="test_key", transport=transport, offline=True)
    generator = RecommendationsGenerator(client)

    result = await generator.generate(
        metrics=[{"code": "CODE", "name": "Test", "unit": "балл", "value": 5.0, "weight": 1.0}],
        score_pct=50.0,
        prof_activity_code="TEST",
        prof_activity_name="Test",
    )

    # Should succeed after self-heal
    assert len(result.strengths) == 1
    assert result.strengths[0].reason == "Healed successfully"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_recommendations_generator_fails_after_retries():
    """Test that generator fails after max retry attempts."""
    transport = MockTransport()

    # Both attempts return invalid JSON
    for _ in range(2):
        transport.add_response(
            {
                "candidates": [
                    {
                        "content": {
                            "parts": [{"text": "Invalid JSON"}],
                        },
                    }
                ]
            }
        )

    client = GeminiClient(api_key="test_key", transport=transport, offline=True)
    generator = RecommendationsGenerator(client)

    with pytest.raises(ValueError, match="Failed to parse JSON"):
        await generator.generate(
            metrics=[
                {"code": "CODE", "name": "Test", "unit": "балл", "value": 5.0, "weight": 1.0}
            ],
            score_pct=50.0,
            prof_activity_code="TEST",
            prof_activity_name="Test",
            )


@pytest.mark.asyncio
@pytest.mark.unit
async def test_recommendations_generator_convenience_function():
    """Test convenience function generate_recommendations."""
    from app.services.recommendations import generate_recommendations

    # Test with valid response
    mock_response = {
        "strengths": [
            {
                "title": "Test strength",
                "metric_codes": ["CODE1"],
                "reason": "Reason",
            }
        ],
        "dev_areas": [
            {
                "title": "Test area",
                "metric_codes": ["CODE2"],
                "actions": ["Action 1"],
            }
        ],
        "recommendations": [
            {
                "title": "Развитие навыков",
                "skill_focus": "Коммуникация",
                "development_advice": "Практикуйте активное слушание",
                "recommended_formats": ["воркшоп"],
            }
        ],
    }

    transport = MockTransport()
    transport.add_response(
        {
            "candidates": [
                {
                    "content": {
                        "parts": [{"text": json.dumps(mock_response, ensure_ascii=False)}],
                    },
                }
            ]
        }
    )

    client = GeminiClient(api_key="test_key", transport=transport, offline=True)

    result = await generate_recommendations(
        gemini_client=client,
        metrics=[{"code": "CODE", "name": "Test", "unit": "балл", "value": 5.0, "weight": 1.0}],
        score_pct=50.0,
        prof_activity_code="TEST",
        prof_activity_name="Test",
    )

    # Should return dict with three keys
    assert result is not None
    assert "strengths" in result
    assert "dev_areas" in result
    assert "recommendations" in result
    assert len(result["recommendations"]) == 1


@pytest.mark.asyncio
@pytest.mark.unit
async def test_recommendations_generator_prompt_building():
    """Test that prompt is built correctly."""
    transport = MockTransport()
    transport.add_response(
        {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": json.dumps(
                                    {
                                        "strengths": [],
                                        "dev_areas": [],
                                        "recommendations": [],
                                    }
                                )
                            }
                        ],
                    },
                }
            ]
        }
    )

    client = GeminiClient(api_key="test_key", transport=transport, offline=True)
    generator = RecommendationsGenerator(client)

    input_data = RecommendationsInput(
        context={
            "language": "ru",
            "prof_activity": {"code": "SALES", "name": "Продажи"},
            "weight_table": {"version": 3},
        },
        metrics=[
            {
                "code": "COMMUNICATION_CLARITY",
                "name": "Ясность речи",
                "unit": "балл",
                "value": 8.5,
                "weight": 0.15,
            }
        ],
        score_pct=78.4,
    )

    prompt = generator._build_prompt(input_data)

    # Verify prompt contains key elements
    assert "Продажи" in prompt
    assert "COMMUNICATION_CLARITY" in prompt
    assert "78.4" in prompt
    assert "JSON" in prompt
    assert "strengths" in prompt
    assert "dev_areas" in prompt
    assert "recommendations" in prompt
    # Version is in JSON context, not in text
    assert '"version": 3' in prompt


# ===== Integration Tests (AI-08) =====


@pytest.mark.asyncio
@pytest.mark.integration
async def test_generate_report_recommendations_task(db_session):
    """Test Celery task for generating recommendations (AI-08)."""
    from datetime import date
    from decimal import Decimal

    from app.clients import GeminiClient, GeminiTransport
    from app.core.config import settings
    from app.repositories.metric import MetricDefRepository
    from app.repositories.participant import ParticipantRepository
    from app.repositories.participant_metric import ParticipantMetricRepository
    from app.repositories.prof_activity import ProfActivityRepository
    from app.repositories.scoring_result import ScoringResultRepository
    from app.tasks.recommendations import generate_report_recommendations

    # 1. Setup test data - Create participant
    participant_repo = ParticipantRepository(db_session)
    participant = await participant_repo.create(
        full_name="Test Participant",
        birth_date=date(1985, 1, 1),
        external_id="TEST_RECOMMENDATIONS",
    )

    # Get or create prof activity
    prof_activity_repo = ProfActivityRepository(db_session)
    prof_activities = await prof_activity_repo.list_all()
    if not prof_activities:
        pytest.skip("No professional activities in test database")
    prof_activity = prof_activities[0]

    weight_table = await prof_activity_repo.get_active_weight_table(prof_activity.id)
    if not weight_table:
        pytest.skip("No active weight table for test")


    # 2. Create participant metrics for all required metrics
    metric_def_repo = MetricDefRepository(db_session)
    metric_defs = await metric_def_repo.list_all(active_only=True)

    participant_metric_repo = ParticipantMetricRepository(db_session)

    for weight_entry in weight_table.weights:
        metric_code = weight_entry["metric_code"]
        await participant_metric_repo.upsert(
            participant_id=participant.id,
            metric_code=metric_code,
            value=Decimal("7.5"),  # Mid-range value
            confidence=0.9,
            source_report_id=None,
        )

    await db_session.commit()

    # 3. Create scoring result
    scoring_result_repo = ScoringResultRepository(db_session)
    scoring_result = await scoring_result_repo.create(
        participant_id=participant.id,
        weight_table_id=weight_table.id,
        score_pct=Decimal("75.00"),
        strengths=[{"metric_code": "TEST", "metric_name": "Test", "value": "8.0", "weight": "0.2"}],
        dev_areas=[
            {"metric_code": "TEST2", "metric_name": "Test 2", "value": "6.0", "weight": "0.1"}
        ],
        recommendations=None,  # Will be updated by task
        compute_notes="Test scoring",
    )
    await db_session.commit()

    # 4. Mock Gemini response
    mock_recommendations = {
        "strengths": [
            {
                "title": "Отличная коммуникация",
                "metric_codes": ["COMMUNICATION_CLARITY"],
                "reason": "Высокий балл по ясности речи",
            }
        ],
        "dev_areas": [
            {
                "title": "Улучшение планирования",
                "metric_codes": ["PLANNING_ACCURACY"],
                "actions": ["Изучить методики планирования", "Практиковать ежедневное планирование"],
            }
        ],
        "recommendations": [
            {
                "title": "Развитие педагогических навыков",
                "skill_focus": "Методика преподавания",
                "development_advice": "Изучите современные методики обучения и практикуйте их применение",
                "recommended_formats": ["воркшоп", "практикум"],
            },
            {
                "title": "Улучшение коммуникации",
                "skill_focus": "Устная коммуникация",
                "development_advice": "Практикуйте публичные выступления и работу с аудиторией",
                "recommended_formats": ["тренинг", "наставничество"],
            },
        ],
    }

    # Mock transport
    class MockTransport(GeminiTransport):
        async def request(
            self,
            method: str,
            url: str,
            headers: dict[str, Any] | None = None,
            json: dict[str, Any] | None = None,
            timeout: float = 30.0,
        ) -> dict[str, Any]:
            return {
                "candidates": [
                    {
                        "content": {
                            "parts": [{"text": json.dumps(mock_recommendations, ensure_ascii=False)}],
                        },
                    }
                ]
            }

    # Temporarily patch Gemini client creation
    import app.core.gemini_factory
    from unittest.mock import patch

    mock_client = GeminiClient(api_key="test_key", transport=MockTransport(), offline=True)

    with patch.object(
        app.core.gemini_factory, "create_gemini_client", return_value=mock_client
    ):
        # 5. Run Celery task (synchronous in eager mode)
        result = generate_report_recommendations(
            scoring_result_id=str(scoring_result.id),
            request_id="test_request",
        )

        assert result["status"] == "success"
        assert result["recommendations_count"] == 2

    # 6. Verify recommendations were saved
    await db_session.refresh(scoring_result)

    assert scoring_result.recommendations is not None
    assert len(scoring_result.recommendations) == 2
    assert scoring_result.recommendations[0]["title"] == "Развитие педагогических навыков"
    assert scoring_result.recommendations[0]["skill_focus"] == "Методика преподавания"
    assert scoring_result.recommendations[1]["skill_focus"] == "Устная коммуникация"
    assert scoring_result.recommendations_status == "ready"
    assert scoring_result.recommendations_error is None


@pytest.mark.asyncio
@pytest.mark.integration
async def test_generate_recommendations_task_when_disabled(db_session):
    """Test task skips generation when AI_RECOMMENDATIONS_ENABLED=0."""
    from datetime import date
    from decimal import Decimal
    from unittest.mock import patch

    from app.core.config import Settings
    from app.repositories.participant import ParticipantRepository
    from app.repositories.prof_activity import ProfActivityRepository
    from app.repositories.scoring_result import ScoringResultRepository
    from app.tasks.recommendations import generate_report_recommendations

    # Setup test data - Create participant
    participant_repo = ParticipantRepository(db_session)
    participant = await participant_repo.create(
        full_name="Test Participant 2",
        birth_date=date(1985, 1, 1),
        external_id="TEST_DISABLED",
    )

    # Get prof activity
    prof_activity_repo = ProfActivityRepository(db_session)
    prof_activities = await prof_activity_repo.list_all()
    if not prof_activities:
        pytest.skip("No professional activities in test database")
    prof_activity = prof_activities[0]

    weight_table = await prof_activity_repo.get_active_weight_table(prof_activity.id)
    if not weight_table:
        pytest.skip("No active weight table for test")

    scoring_result_repo = ScoringResultRepository(db_session)
    scoring_result = await scoring_result_repo.create(
        participant_id=participant.id,
        weight_table_id=weight_table.id,
        score_pct=Decimal("75.00"),
        strengths=[],
        dev_areas=[],
        recommendations=None,
        compute_notes="Test",
    )
    await db_session.commit()

    # Patch settings to disable recommendations
    mock_settings = Settings()
    mock_settings.ai_recommendations_enabled = False

    with patch("app.tasks.recommendations.settings", mock_settings):
        result = generate_report_recommendations(
            scoring_result_id=str(scoring_result.id),
        )

        assert result["status"] == "skipped"
        assert result["reason"] == "AI recommendations are disabled"
        await db_session.refresh(scoring_result)
        assert scoring_result.recommendations_status == "disabled"
        assert scoring_result.recommendations_error is None
