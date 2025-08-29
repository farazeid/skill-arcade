import asyncio
import io
import logging
import os
import os.path as osp
import sys
from abc import ABC, abstractmethod

import aiofiles
import aiohttp
import numpy as np
import xxhash
from dotenv import load_dotenv
from gcloud.aio.storage import Blob, Storage
from google.api_core.exceptions import GoogleAPICallError
from sqlmodel.ext.asyncio.session import AsyncSession

from src.db import Transition

load_dotenv()

GCP_BUCKET_NAME = os.getenv("GCP_BUCKET_NAME")
UPLOADER_NUM_WORKERS = int(os.getenv("UPLOADER_NUM_WORKERS", "1"))

STORAGE_PATH = osp.join(".", "storage", "obs")


class Uploader(ABC):
    """Abstract base class for uploaders."""

    @abstractmethod
    def __init__(self, engine) -> None:
        self.engine = engine

    @abstractmethod
    def start(self) -> None:
        """Starts the background worker tasks."""
        pass

    @abstractmethod
    def put(
        self,
        transition: Transition,
        obs: np.ndarray,
        next_obs: np.ndarray | None,
    ) -> None:
        """Add an observation to the upload queue (non-blocking)."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Stops the background worker tasks gracefully."""
        pass


class CloudUploader(Uploader):
    """Multi-worker asynchronous queue for real-time uploading of observations to Google Cloud Storage"""

    def __init__(self, engine) -> None:
        self.engine = engine
        self.gcp_session = aiohttp.ClientSession()
        storage = Storage(session=self.gcp_session)
        try:
            gcp_bucket = storage.get_bucket(GCP_BUCKET_NAME)

        except GoogleAPICallError as e:
            logging.error(f"GCS: GoogleAPICallError with {GCP_BUCKET_NAME}; error: {e}")
            sys.exit("Failed initialisation of GCS bucket")

        self._queue: asyncio.Queue = asyncio.Queue()
        self._worker_tasks: list[asyncio.Task] = []
        self._num_workers = UPLOADER_NUM_WORKERS
        self.gcp_bucket = gcp_bucket

        self.start()

    def start(self) -> None:
        """Starts the background worker tasks."""
        if not self._worker_tasks:
            for i in range(self._num_workers):
                task = asyncio.create_task(self._worker(), name=f"uploader_worker_{i}")
                self._worker_tasks.append(task)

            logging.info(f"Uploader started with {self._num_workers} worker tasks.")

    async def close(self) -> None:
        """Stops the background worker tasks gracefully."""
        if self._worker_tasks:
            logging.info("Uploader: Stopping workers...")

            await self.gcp_session.close()

            await self._queue.join()

            for task in self._worker_tasks:
                task.cancel()
            await asyncio.gather(*self._worker_tasks, return_exceptions=True)
            self._worker_tasks = []

            logging.info("Uploader: All workers stopped.")

    def put(
        self,
        transition: Transition,
        obs: np.ndarray,
        next_obs: np.ndarray | None,
    ) -> None:
        """Add an observation to the upload queue (non-blocking)."""
        try:
            self._queue.put_nowait((transition, obs, next_obs))

        except asyncio.QueueFull:
            logging.warning("Uploader: Upload queue is full; dropping frame.")

    async def _worker(self) -> None:
        """The background task that continuously uploads items from the queue."""
        logging.info("Uploader worker started.")
        while True:
            try:
                transition, obs, next_obs = await self._queue.get()
                try:
                    buffer = io.BytesIO()
                    np.savez_compressed(buffer, obs=obs)  # .npz
                    obs_data = buffer.getvalue()
                    obs_data_hash = xxhash.xxh3_128_hexdigest(obs_data)
                    await self._upload_obs(obs_data, obs_data_hash)
                    transition.obs_key = obs_data_hash

                    if next_obs is not None:
                        buffer = io.BytesIO()
                        np.savez_compressed(buffer, obs=next_obs)  # .npz
                        next_obs_data = buffer.getvalue()
                        next_obs_data_hash = xxhash.xxh3_128_hexdigest(next_obs_data)
                        await self._upload_obs(next_obs_data, next_obs_data_hash)
                        transition.next_obs_key = next_obs_data_hash

                    async with AsyncSession(
                        self.engine,
                        expire_on_commit=False,
                    ) as session:
                        session.add(transition)
                        await session.commit()

                except Exception as e:
                    logging.error(f"Uploader: Error during upload or DB update: {e}")

                finally:
                    self._queue.task_done()

            except asyncio.CancelledError:
                logging.info("Uploader worker cancelled.")
                break

            except Exception as e:
                logging.error(f"Uploader: Unexpected error in worker: {e}")

    async def _upload_obs(
        self,
        data: bytes,
        data_hash: str,
    ) -> str:
        assert self.gcp_bucket, (
            "GCP bucket not initialised by lifespan manager"
            f"; gcp_bucket: {self.gcp_bucket}"
        )

        blob_name = f"obs/{data_hash}.npz"
        try:
            if await self.gcp_bucket.blob_exists(blob_name):
                logging.info(f"GCS: {blob_name} exists; skipping upload")
            else:
                logging.info(f"GCS: {blob_name} new; uploading")

                blob: Blob = self.gcp_bucket.new_blob(blob_name)
                await blob.upload(
                    data,
                    content_type="application/octet-stream",
                )

                logging.info(f"GCS: {blob_name} uploaded")

        except GoogleAPICallError as e:
            logging.error(f"GCS: GoogleAPICallError with {blob_name}; error: {e}")
            raise

        except Exception as e:
            logging.error(f"GCS: Unexpected error with {blob_name}; error: {e}")
            raise

        return data_hash


class LocalUploader(Uploader):
    """Multi-worker asynchronous queue for ..."""

    def __init__(self, engine, batch_size: int = 1, max_wait: float = 5.0) -> None:
        self.engine = engine

        self._queue: asyncio.Queue = asyncio.Queue()
        self._worker_tasks: list[asyncio.Task] = []
        self._num_workers = UPLOADER_NUM_WORKERS

        self._batch_size = batch_size
        self._max_wait = max_wait

        os.makedirs(STORAGE_PATH, exist_ok=True)

        self.start()

    def start(self) -> None:
        """Starts the background worker tasks."""
        if not self._worker_tasks:
            for i in range(self._num_workers):
                task = asyncio.create_task(self._worker(), name=f"uploader_worker_{i}")
                self._worker_tasks.append(task)

            logging.info(
                f"Uploader started with {self._num_workers} worker tasks "
                f"(batch_size={self._batch_size}, max_wait={self._max_wait}s)."
            )

    async def close(self) -> None:
        """Stops the background worker tasks gracefully."""
        if self._worker_tasks:
            logging.info("Uploader: Stopping workers...")

            await self._queue.join()

            for task in self._worker_tasks:
                task.cancel()
            await asyncio.gather(*self._worker_tasks, return_exceptions=True)
            self._worker_tasks = []

            logging.info("Uploader: All workers stopped.")

    def put(
        self,
        transition: Transition,
        obs: np.ndarray,
        next_obs: np.ndarray | None,
    ) -> None:
        """Add an observation to the upload queue (non-blocking)."""
        try:
            self._queue.put_nowait((transition, obs, next_obs))

        except asyncio.QueueFull:
            logging.warning("Uploader: Upload queue is full; dropping frame.")

    async def _worker(self) -> None:
        """Background task that continuously uploads items in batches."""
        logging.info("Uploader worker started.")
        while True:
            try:
                items = []
                start = asyncio.get_event_loop().time()

                # Always block until at least one item is available
                transition, obs, next_obs = await self._queue.get()
                items.append((transition, obs, next_obs))

                # Try to fill batch until size or timeout reached
                while len(items) < self._batch_size:
                    timeout = self._max_wait - (asyncio.get_event_loop().time() - start)
                    if timeout <= 0:
                        break
                    try:
                        item = await asyncio.wait_for(
                            self._queue.get(), timeout=timeout
                        )
                        items.append(item)
                    except TimeoutError:
                        break

                # Process the batch
                await self._process_batch(items)

                # Mark tasks done
                for _ in items:
                    self._queue.task_done()

            except asyncio.CancelledError:
                logging.info("Uploader worker cancelled.")
                break

            except Exception as e:
                logging.error(f"Uploader: Unexpected error in worker: {e}")

    async def _process_batch(
        self, items: list[tuple[Transition, np.ndarray, np.ndarray | None]]
    ) -> None:
        """Process a batch of transitions & observations."""
        try:
            for transition, obs, next_obs in items:
                # Save obs
                buffer = io.BytesIO()
                np.savez_compressed(buffer, obs=obs)
                obs_data = buffer.getvalue()
                obs_data_hash = xxhash.xxh3_128_hexdigest(obs_data)
                await self._upload_obs(obs_data, obs_data_hash)
                transition.obs_key = obs_data_hash

                # Save next_obs if present
                if next_obs is not None:
                    buffer = io.BytesIO()
                    np.savez_compressed(buffer, obs=next_obs)
                    next_obs_data = buffer.getvalue()
                    next_obs_data_hash = xxhash.xxh3_128_hexdigest(next_obs_data)
                    await self._upload_obs(next_obs_data, next_obs_data_hash)
                    transition.next_obs_key = next_obs_data_hash

            # Commit all transitions in one DB session
            async with AsyncSession(self.engine, expire_on_commit=False) as session:
                session.add_all([t for t, _, _ in items])
                await session.commit()
        except Exception as e:
            logging.error(f"Uploader: Error during batch upload or DB update: {e}")

    async def _upload_obs(
        self,
        data: bytes,
        data_hash: str,
    ) -> str:
        blob_name = f"{data_hash}.npz"
        file_path = osp.join(STORAGE_PATH, blob_name)
        try:
            if osp.exists(file_path):
                logging.info(f"Local Storage: {blob_name} exists; skipping upload")
            else:
                logging.info(f"Local Storage: {blob_name} new; uploading")

                async with aiofiles.open(file_path, "wb") as file:
                    await file.write(data)

                logging.info(f"Local Storage: {blob_name} uploaded")

        except Exception as e:
            logging.error(
                f"Local Storage: Unexpected error with {blob_name}; error: {e}"
            )
            raise

        return data_hash
