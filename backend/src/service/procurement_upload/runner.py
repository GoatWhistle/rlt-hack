import asyncio
import logging
from collections.abc import Sequence
from uuid import UUID

from src.models.lot_result import LotResult
from src.models.upload import PendingLot
from src.service.procurement_upload.protocols import Clock, LotProcessing, UploadStore
from src.service.procurement_upload.settings import UploadSettings

logger = logging.getLogger(__name__)


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
            if pending:
                logger.info("resuming unfinished lots", extra={"lots": len(pending)})
            self.submit(pending)
            return

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
        for attempt in range(1, attempts + 1):
            try:
                return await self._processor.process(job.lot)
            except Exception:
                logger.warning(
                    "lot processing failed",
                    extra={"upload_id": str(job.upload_id), "attempt": attempt},
                    exc_info=True,
                )
                if attempt < attempts:
                    await asyncio.sleep(self._settings.retry_delay_seconds * attempt)
        return LotResult.failure(job.lot.lot_id, self._clock.now())

    async def _save(self, job: PendingLot, result: LotResult) -> None:
        attempts = self._settings.attempts
        for attempt in range(1, attempts + 1):
            try:
                await self._store.save_result(job.upload_id, result)
            except Exception:
                logger.warning(
                    "lot result was not saved",
                    extra={"upload_id": str(job.upload_id), "attempt": attempt},
                    exc_info=True,
                )
                await asyncio.sleep(self._settings.retry_delay_seconds * attempt)
            else:
                return
