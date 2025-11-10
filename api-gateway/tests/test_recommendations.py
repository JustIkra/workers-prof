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
        title="Онлайн курс по продажам",
        link_url="https://example.com/course",
        priority=1,
    )
    assert item.title == "Онлайн курс по продажам"
    assert item.priority == 1

    # Test priority range [1..5]
    with pytest.raises(ValidationError):
        RecommendationItem(title="Test", link_url="", priority=0)

    with pytest.raises(ValidationError):
        RecommendationItem(title="Test", link_url="", priority=6)

    # Valid priorities
    for priority in [1, 2, 3, 4, 5]:
        item = RecommendationItem(title="Test", link_url="", priority=priority)
        assert item.priority == priority


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
            RecommendationItem(title="Course 1", link_url="https://example.com", priority=1),
        ],
    )

    result = response.to_scoring_result_format()

    assert "strengths" in result
    assert "dev_areas" in result
    assert "recommendations" in result
    assert len(result["strengths"]) == 1
    assert result["strengths"][0]["title"] == "Test 1"
    assert result["recommendations"][0]["priority"] == 1


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
                "title": "Курс по коммуникации",
                "link_url": "https://example.com/course",
                "priority": 1,
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
        weight_table_version=1,
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
            {"title": f"Rec {i}", "link_url": "", "priority": 1} for i in range(6)
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
        weight_table_version=1,
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
        "recommendations": [{"title": "Test", "link_url": "", "priority": 1}],
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
        weight_table_version=1,
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
            weight_table_version=1,
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
                "title": "Course 1",
                "link_url": "https://example.com",
                "priority": 1,
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
        weight_table_version=1,
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
    assert "версия весов 3" in prompt
    assert "COMMUNICATION_CLARITY" in prompt
    assert "78.4" in prompt
    assert "JSON" in prompt
    assert "strengths" in prompt
    assert "dev_areas" in prompt
    assert "recommendations" in prompt
