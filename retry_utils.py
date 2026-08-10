"""
retry_utils.py — Asynchronous Retry & Fault Tolerance Utility for Trevor AI.
Implements exponential backoff retries for external HTTP, Telegram, Gemini, and Scraper calls.
"""

import asyncio
import logging
import time

logger = logging.getLogger("trevor.retry")


async def async_retry(
    func,
    *args,
    retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,),
    stage_name: str = "Operation",
    **kwargs
):
    """
    Executes an async function or synchronous callable with automatic retries and exponential backoff.
    Retries: Attempt 1 (0s delay), Attempt 2 (1s delay), Attempt 3 (2s delay), Attempt 4 (4s delay).
    """
    delay = initial_delay
    last_exception = None

    for attempt in range(1, retries + 1):
        try:
            start_time = time.time()
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = await asyncio.to_thread(func, *args, **kwargs)

            elapsed = time.time() - start_time
            logger.info(f"[{stage_name}] Completed successfully on attempt {attempt} in {elapsed:.2f} sec")
            return result
        except exceptions as e:
            last_exception = e
            elapsed = time.time() - start_time
            if attempt < retries:
                logger.warning(
                    f"[{stage_name}] Attempt {attempt}/{retries} failed ({e}) after {elapsed:.2f} sec. "
                    f"Retrying in {delay:.1f} sec..."
                )
                await asyncio.sleep(delay)
                delay *= backoff_factor
            else:
                logger.error(
                    f"[{stage_name}] All {retries} attempts failed. Final error: {e}"
                )

    raise last_exception
