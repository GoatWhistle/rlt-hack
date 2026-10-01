import asyncio
import logging
import random
from collections.abc import Sequence
from uuid import UUID

from src.models.lot_result import LotResult
from src.models.upload import PendingLot
from src.service.procurement_upload.protocols import Clock, LotProcessing, UploadStore
from src.service.procurement_upload.settings import UploadSettings

logger = logging.getLogger(__name__)

DEFINITE_ERRORS = (ValueError, TypeError, LookupError, ArithmeticError, AttributeError)
TIMEOUT_ATTEMPTS = 2


class LotRunner:
    def __init__(
        self,
        processor: LotProcessing,
        store: UploadStore,
        clock: Clock,
        settings: UploadSettings,
    ) -> None:
        self._processor = processor
        self._store = store
        self._clock = clock
        self._settings = settings
        self._queue: asyncio.Queue[PendingLot] = asyncio.Queue()
        self._known: set[tuple[UUID, str]] = set()
        self._tasks: list[asyncio.Task[None]] = []

    @property
    def running(self) -> bool:
        return bool(self._tasks)

    async def start(self) -> None:
        if self._tasks:
            return
        workers = [
            asyncio.create_task(self._work(), name=f"lot-worker-{number}")
            for number in range(self._settings.concurrency)
        ]
        self._tasks = [*workers, asyncio.create_task(self._resume(), name="lot-resume")]

    async def stop(self) -> None:
        tasks, self._tasks = self._tasks, []
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    async def drain(self) -> None:
        await self._queue.join()

    def submit(self, lots: Sequence[PendingLot]) -> None:
        for lot in lots:
            if lot.key not in self._known:
                self._known.add(lot.key)
                self._queue.put_nowait(lot)

    async def _resume(self) -> None:
        while True:
            try:
                pending = await self._store.pending()
            except Exception:
                logger.warning("unfinished lots could not be loaded", exc_info=True)
                await asyncio.sleep(self._settings.resume_delay_seconds)
                continue
            fresh = [lot for lot in pending if lot.key not in self._known]
            if fresh:
                logger.info("resuming unfinished lots", extra={"lots": len(fresh)})
            self.submit(fresh)
            await asyncio.sleep(self._settings.resume_interval_seconds)

    async def _work(self) -> None:
        while True:
            job = await self._queue.get()
            try:
                result = await self._attempt(job)
                await self._save(job, result)
            finally:
                self._known.discard(job.key)
                self._queue.task_done()

    async def _attempt(self, job: PendingLot) -> LotResult:
        attempts = self._settings.attempts
        timeouts = 0
        for attempt in range(1, attempts + 1):
            try:
                return await self._processor.process(job.lot)
            except DEFINITE_ERRORS:
                _warn("lot cannot be processed", job, attempt)
                break
            except TimeoutError:
                _warn("lot processing timed out", job, attempt)
                timeouts += 1
                if timeouts >= TIMEOUT_ATTEMPTS:
                    break
            except Exception:
                _warn("lot processing failed", job, attempt)
            if attempt < attempts:
                await asyncio.sleep(self._pause(attempt))
        return LotResult.failure(job.lot.lot_id, self._clock.now())

    async def _save(self, job: PendingLot, result: LotResult) -> None:
        attempts = self._settings.attempts
        for attempt in range(1, attempts + 1):
            try:
                await self._store.save_result(job.upload_id, result)
            except Exception:
                _warn("lot result was not saved", job, attempt)
                if attempt < attempts:
                    await asyncio.sleep(self._pause(attempt))
            else:
                return
        logger.error(
            "lot result was not saved and will be resumed",
            extra={"upload_id": str(job.upload_id), "lot_id": job.lot.lot_id},
        )

    def _pause(self, attempt: int) -> float:
        delay = self._settings.retry_delay_seconds
        return delay * attempt + random.uniform(0, delay)


def _warn(message: str, job: PendingLot, attempt: int) -> None:
    logger.warning(
        message,
        extra={"upload_id": str(job.upload_id), "lot_id": job.lot.lot_id, "attempt": attempt},
        exc_info=True,
    )
