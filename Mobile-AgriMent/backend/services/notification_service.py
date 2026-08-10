import json
import logging
from typing import Any

import httpx

from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

EXPO_PUSH_API_URL = "https://exp.host/--/api/v2/push/send"
EXPO_PUSH_BATCH_URL = "https://exp.host/--/api/v2/push/sendMultiple"


class NotificationService:
    """Sends push notifications via the Expo Push API.

    The frontend registers Expo Push Tokens (ExponentPushToken[xxx]).
    These tokens are NOT FCM tokens and cannot be sent through Firebase.
    The Expo Push API accepts Expo Push Tokens directly.
    """

    async def send_push_notification(
        self,
        device_tokens: list[str],
        title: str,
        body: str,
        data: dict[str, Any] | None = None,
    ) -> int:
        if not device_tokens:
            logger.info("No device tokens provided, skipping push notification")
            return 0

        valid_tokens = [t for t in device_tokens if t and t.strip()]
        if not valid_tokens:
            logger.info(
                "No valid device tokens after filtering, skipping push notification"
            )
            return 0

        logger.info(f"Sending push notification to {len(valid_tokens)} device(s)")

        messages = [
            {
                "to": token,
                "title": title,
                "body": body,
                "data": data or {},
                "sound": "default",
                "priority": "high",
                "channelId": "pest_alerts",
                "badge": 1,
            }
            for token in valid_tokens
        ]

        sent_count = 0
        batch_size = 100

        for i in range(0, len(messages), batch_size):
            batch = messages[i : i + batch_size]
            try:
                sent_count += await self._send_batch(batch)
            except Exception as e:
                logger.error(f"Expo Push API batch error: {e}")

        logger.info(f"Sent {sent_count}/{len(valid_tokens)} push notifications")
        return sent_count

    async def _send_batch(self, messages: list[dict]) -> int:
        """Send a batch of messages via Expo Push API.

        For single messages uses /push/send, for multiple uses /push/sendMultiple.
        """
        url = EXPO_PUSH_BATCH_URL if len(messages) > 1 else EXPO_PUSH_API_URL
        payload = messages if len(messages) > 1 else messages[0]

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                url,
                json=payload,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
            )

            if response.status_code != 200:
                logger.error(
                    f"Expo Push API returned {response.status_code}: {response.text}"
                )
                return 0

            result = response.json()
            return self._parse_response(result, len(messages))

    def _parse_response(self, result: dict, expected_count: int) -> int:
        """Parse Expo Push API response and count successful sends.

        Single message response: { data: { status: "ok", id: "..." } }
        Batch response: { data: [{ status: "ok", id: "..." }, ...] }
        """
        sent = 0

        data = result.get("data")
        if data is None:
            logger.warning(f"Unexpected Expo Push API response: {json.dumps(result)}")
            return 0

        if isinstance(data, dict):
            # Single message response
            if data.get("status") == "ok":
                sent = 1
            else:
                logger.warning(
                    f"Push failed: {data.get('message', data.get('status', 'unknown'))}"
                )
        elif isinstance(data, list):
            # Batch response
            for i, item in enumerate(data):
                if item.get("status") == "ok":
                    sent += 1
                else:
                    error_msg = item.get("message", item.get("status", "unknown"))
                    logger.warning(f"Push to device {i} failed: {error_msg}")
        else:
            logger.warning(
                f"Unexpected data format in Expo Push API response: {type(data)}"
            )

        return sent
