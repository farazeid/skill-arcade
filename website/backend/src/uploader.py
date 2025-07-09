import asyncio
import io
import logging
import os
import sys
import uuid

import aiohttp
import numpy as np
import xxhash
from dotenv import load_dotenv
from gcloud.aio.storage import Blob, Storage
from google.api_core.exceptions import GoogleAPICallError
from sqlmodel import Session

from src.db import Transition, engine

load_dotenv()

GCP_BUCKET_NAME = os.getenv("GCP_BUCKET_NAME")
UPLOADER_NUM_WORKERS = int(os.getenv("UPLOADER_NUM_WORKERS", "1"))


class Uploader:
    """Multi-worker asynchronous queue for real-time uploading of observations to Google Cloud Storage"""

    def __init__(self) -> None:
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
        self, obs: np.ndarray, transition_id: uuid.UUID, key_to_update: str
    ) -> None:
        """Add an observation to the upload queue (non-blocking)."""
        try:
            self._queue.put_nowait((obs, transition_id, key_to_update))

        except asyncio.QueueFull:
            logging.warning("Uploader: Upload queue is full; dropping frame.")

    async def _worker(self) -> None:
        """The background task that continuously uploads items from the queue."""
        logging.info("Uploader worker started.")
        while True:
            try:
                obs, transition_id, key_to_update = await self._queue.get()
                try:
                    buffer = io.BytesIO()
                    np.savez_compressed(buffer, obs=obs)  # .npz
                    data = buffer.getvalue()
                    data_hash = xxhash.xxh3_128_hexdigest(data)

                    if key_to_update == "obs_key":
                        await self._upload_obs(data, data_hash)
                    self._update_db(transition_id, key_to_update, data_hash)

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

    def _update_db(
        self,
        transition_id: uuid.UUID,
        key_to_update: str,
        data_hash: str,
    ) -> None:
        with Session(self.engine) as session:
            transition = session.get(Transition, transition_id)
            if transition:
                setattr(transition, key_to_update, data_hash)
                session.add(transition)
                session.commit()

                logging.info(
                    f"Uploader: Updated transition {transition_id} with {key_to_update}={data_hash}"
                )
            else:
                logging.warning(
                    f"Uploader: Transition {transition_id} not found in DB."
                )
