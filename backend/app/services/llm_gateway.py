import hashlib
import json
import logging
from typing import Any

import redis.asyncio as aioredis
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import settings

logger = logging.getLogger(__name__)

JD_CACHE_PREFIX = "jd_parse:"
JD_CACHE_TTL = 86400 * 7  # 7 days


class LLMGateway:
    """Groq LLM gateway with caching, retries, and fallback."""

    def __init__(self) -> None:
        self._client = AsyncOpenAI(
            api_key=settings.groq_api_key or "dummy",
            base_url="https://api.groq.com/openai/v1",
        )
        self._redis: aioredis.Redis | None = None
        self._available = bool(settings.groq_api_key)

    async def _get_redis(self) -> aioredis.Redis | None:
        if self._redis is None:
            try:
                self._redis = aioredis.from_url(settings.redis_url, decode_responses=True)
                await self._redis.ping()
            except Exception as e:
                logger.warning("Redis unavailable for LLM cache: %s", e)
                self._redis = None
        return self._redis

    @staticmethod
    def jd_hash(text: str) -> str:
        return hashlib.sha256(text.strip().encode()).hexdigest()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def chat_json(
        self,
        system: str,
        user: str,
        model: str | None = None,
        cache_key: str | None = None,
    ) -> dict[str, Any]:
        if cache_key:
            cached = await self._cache_get(cache_key)
            if cached is not None:
                return cached

        if not self._available:
            return self._mock_response(system, user)

        model = model or settings.groq_model_primary
        try:
            response = await self._client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
            )
            content = response.choices[0].message.content or "{}"
            result = json.loads(content)
            if cache_key:
                await self._cache_set(cache_key, result)
            return result
        except Exception as e:
            logger.warning("Primary model failed (%s), trying fast fallback", e)
            if model != settings.groq_model_fast:
                return await self.chat_json(system, user, settings.groq_model_fast, cache_key)
            raise

    async def chat_text(
        self,
        system: str,
        user: str,
        model: str | None = None,
    ) -> str:
        if not self._available:
            return "LLM unavailable — using Stage-5 ranking only."

        model = model or settings.groq_model_primary
        response = await self._client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
        )
        return response.choices[0].message.content or ""

    async def _cache_get(self, key: str) -> dict | None:
        redis = await self._get_redis()
        if not redis:
            return None
        try:
            val = await redis.get(JD_CACHE_PREFIX + key)
            return json.loads(val) if val else None
        except Exception:
            return None

    async def _cache_set(self, key: str, data: dict) -> None:
        redis = await self._get_redis()
        if not redis:
            return
        try:
            await redis.setex(JD_CACHE_PREFIX + key, JD_CACHE_TTL, json.dumps(data))
        except Exception:
            pass

    @staticmethod
    def _mock_response(system: str, user: str) -> dict[str, Any]:
        """Deterministic fallback when no API key is configured."""
        text = user.lower()
        skills = []
        for skill in ["python", "react", "vue", "java", "aws", "kubernetes", "sql", "typescript", "node"]:
            if skill in text:
                skills.append(skill)
        return {
            "must_have_skills": skills[:5] or ["python", "sql"],
            "nice_to_have_skills": ["docker", "git"],
            "implied_skills": ["communication", "problem-solving"],
            "seniority_level": "senior" if "senior" in text else "mid",
            "years_experience_range": [4, 7],
            "domain_context": "technology",
            "soft_requirements": ["team collaboration"],
            "deal_breakers": [],
            "culture_signals": ["fast-paced"] if "startup" in text or "ambiguity" in text else [],
            "location": None,
            "work_authorization": None,
        }


llm_gateway = LLMGateway()
