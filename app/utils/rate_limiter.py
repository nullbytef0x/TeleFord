import asyncio
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class RateLimiter:
    """
    Smart rate limiter to prevent Telegram restrictions and account bans.

    Telegram's flood limits (approximate):
    - Private messages: ~30 per second
    - Groups: ~20 per minute
    - Media: More restrictive, ~10-15 per minute
    - Bulk operations: Need longer delays
    """

    def __init__(self):
        self.message_count = 0
        self.media_count = 0
        self.start_time = datetime.now()
        self.last_message_time = datetime.now()

    async def wait_if_needed(self, is_media=False, is_bulk=False):
        """
        Calculate and apply appropriate delay based on message count and type.

        Args:
            is_media: Whether the message contains media (requires longer delays)
            is_bulk: Whether this is part of a bulk operation (requires more conservative delays)
        """
        self.message_count += 1
        if is_media:
            self.media_count += 1

        # Calculate time elapsed since start
        elapsed = (datetime.now() - self.start_time).total_seconds()

        # Base delays
        if is_bulk:
            if is_media:
                delay = self._calculate_bulk_media_delay()
            else:
                delay = self._calculate_bulk_text_delay()
        else:
            if is_media:
                delay = self._calculate_realtime_media_delay()
            else:
                delay = self._calculate_realtime_text_delay()

        # Add progressive delay if sending too fast
        if elapsed > 0:
            messages_per_second = self.message_count / elapsed
            if messages_per_second > 1:  # More than 1 message per second
                delay += 2  # Add extra 2 seconds
            if messages_per_second > 2:  # More than 2 messages per second
                delay += 3  # Add extra 3 seconds (total +5)

        # Log the delay
        logger.info(f"Rate limiter: Waiting {delay}s (Total: {self.message_count} msgs, {self.media_count} media, {elapsed:.1f}s elapsed)")

        await asyncio.sleep(delay)
        self.last_message_time = datetime.now()

        return delay

    def _calculate_bulk_media_delay(self):
        """Calculate delay for bulk media forwarding."""
        # Conservative delays for bulk media to avoid bans
        if self.media_count % 20 == 0:
            return 30  # 30 seconds every 20 media files
        elif self.media_count % 10 == 0:
            return 15  # 15 seconds every 10 media files
        elif self.media_count % 5 == 0:
            return 8   # 8 seconds every 5 media files
        else:
            return 3   # 3 seconds between each media file

    def _calculate_bulk_text_delay(self):
        """Calculate delay for bulk text forwarding."""
        if self.message_count % 30 == 0:
            return 10  # 10 seconds every 30 messages
        elif self.message_count % 15 == 0:
            return 5   # 5 seconds every 15 messages
        else:
            return 1   # 1 second between messages

    def _calculate_realtime_media_delay(self):
        """Calculate delay for real-time media forwarding."""
        # Less aggressive for real-time forwarding
        if self.media_count % 10 == 0:
            return 10  # 10 seconds every 10 media files
        elif self.media_count % 5 == 0:
            return 5   # 5 seconds every 5 media files
        else:
            return 2   # 2 seconds between media files

    def _calculate_realtime_text_delay(self):
        """Calculate delay for real-time text forwarding."""
        if self.message_count % 20 == 0:
            return 5   # 5 seconds every 20 messages
        else:
            return 0.5 # 0.5 seconds between messages

    def reset(self):
        """Reset the rate limiter counters."""
        self.message_count = 0
        self.media_count = 0
        self.start_time = datetime.now()
        self.last_message_time = datetime.now()
        logger.info("Rate limiter reset")

    def get_stats(self):
        """Get current rate limiter statistics."""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        return {
            "total_messages": self.message_count,
            "media_messages": self.media_count,
            "elapsed_seconds": elapsed,
            "messages_per_second": self.message_count / elapsed if elapsed > 0 else 0
        }
