import time
import requests
from typing import Dict, Any, Optional
from wire_check.config import TYPESAFE_API_KEY, TYPESAFE_API_URL, JEV_MODEL
from wire_check.utils.logger import get_logger

logger = get_logger("typesafe_client")

class TypeSafeClient:
    def __init__(self, api_key: Optional[str] = None, api_url: Optional[str] = None):
        self.api_key = api_key or TYPESAFE_API_KEY
        self.api_url = api_url or TYPESAFE_API_URL
        self.model = JEV_MODEL

    def system_one(self, state: Dict[str, Any], questions: Dict[str, Any]) -> tuple[Dict[str, Any], float, Dict[str, int]]:
        """Calls TypeSafe Jev System One API with timeout, retry, and latency tracking."""
        if not self.api_key or self.api_key == "your_typesafe_api_key_here":
            raise ValueError("TypeSafe API key is not configured.")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "state": state,
            "questions": questions
        }

        start_time = time.time()
        max_retries = 3
        backoff = 0.5

        for attempt in range(max_retries):
            try:
                response = requests.post(self.api_url, json=payload, headers=headers, timeout=5)
                latency_ms = (time.time() - start_time) * 1000.0

                if response.status_code == 200:
                    data = response.json()
                    answers = data.get("answers", data)
                    tokens = data.get("usage", {"prompt_tokens": 120, "completion_tokens": 45, "total_tokens": 165})
                    logger.info(f"TypeSafe Jev API call successful in {latency_ms:.1f}ms")
                    return answers, latency_ms, tokens
                else:
                    logger.warning(f"TypeSafe API returned status {response.status_code}: {response.text}")
            except Exception as e:
                logger.warning(f"TypeSafe API attempt {attempt + 1} failed: {e}")

            if attempt < max_retries - 1:
                time.sleep(backoff)
                backoff *= 2.0

        raise RuntimeError("TypeSafe Jev API calls failed after max retries.")
