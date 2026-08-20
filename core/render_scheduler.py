import concurrent.futures
import uuid
import multiprocessing
import threading
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any
from pathlib import Path
from core.video_processor import editar_video

class JobStatus(Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

@dataclass
class Job:
    id: str
    input_path: str
    output_path: str
    status: JobStatus = JobStatus.QUEUED
    progress: int = 0
    error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None

class RenderScheduler:
    def __init__(self):
        self.executor = None
        self.futures = {}
        self.jobs = {}
        self.manager = None
        self.queue = None
        self.cancel_events = {}

    def start(self, videos, output_dir, config, num_workers):
        gpu_accel = config.get("export", {}).get("use_gpu_acceleration", False)
        # Handle concurrency: limit for GPU if needed
        max_workers = num_workers
        if gpu_accel:
            max_workers = min(max_workers, 2) # Example: limit GPU concurrency to 2

        if self.executor is not None:
            self.executor.shutdown(wait=True)
        if self.manager is not None:
            self.manager.shutdown()

        self.manager = multiprocessing.Manager()
        self.executor = concurrent.futures.ProcessPoolExecutor(max_workers=max_workers)
        self.futures = {}
        self.jobs = {}
        self.cancel_events = {}
        self.queue = self.manager.Queue()

        for video_path in videos:
            job_id = str(uuid.uuid4())
            name = Path(video_path).name
            output_path = str(Path(output_dir) / f"edited_{name}")

            job = Job(id=job_id, input_path=video_path, output_path=output_path, status=JobStatus.QUEUED)
            self.jobs[name] = job

            cancel_event = self.manager.Event()
            self.cancel_events[name] = cancel_event

            future = self.executor.submit(editar_video, video_path, output_dir, config, self.queue, cancel_event)
            self.futures[future] = name

    def _process_queue(self):
        updated_jobs = []
        if self.queue:
            try:
                while not self.queue.empty():
                    try:
                        vid_name, pct = self.queue.get_nowait()
                        if vid_name in self.jobs:
                            job = self.jobs[vid_name]
                            if job.status == JobStatus.QUEUED or job.status == JobStatus.PROCESSING:
                                job.status = JobStatus.PROCESSING
                                job.progress = pct
                                updated_jobs.append(job)
                    except Exception:
                        break
            except Exception:
                # E.g. BrokenPipeError if manager was shut down but queue ref remained
                pass
        return updated_jobs

    def get_progress_updates(self):
        # First process queue messages
        updated_jobs = self._process_queue()

        # Also check for completed/failed futures
        done_futures = [f for f in self.futures if f.done()]
        for future in done_futures:
            vid_name = self.futures.pop(future)
            if vid_name in self.jobs:
                job = self.jobs[vid_name]
                # Only update if not already terminal
                if job.status not in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
                    try:
                        result = future.result()
                        job.status = JobStatus.COMPLETED
                        job.progress = 100
                        job.result = result
                    except concurrent.futures.CancelledError:
                        job.status = JobStatus.CANCELLED
                    except Exception as e:
                        job.status = JobStatus.FAILED
                        job.error = str(e)
                    updated_jobs.append(job)

        if not self.futures and self.executor is not None:
            self.executor.shutdown(wait=True)
            self.executor = None
            self.queue = None
            if self.manager is not None:
                self.manager.shutdown()
                self.manager = None

        return updated_jobs

    def cancel(self):
        if self.executor:
            # Signal cancel to all jobs
            for cancel_event in self.cancel_events.values():
                cancel_event.set()

            # Cancel futures (prevents queued ones from starting)
            for future, vid_name in self.futures.items():
                if not future.done():
                    future.cancel()
                    if vid_name in self.jobs:
                        job = self.jobs[vid_name]
                        if job.status not in (JobStatus.COMPLETED, JobStatus.FAILED):
                            job.status = JobStatus.CANCELLED

            # Shutdown in background to prevent UI block
            def _cleanup(executor, manager):
                try:
                    executor.shutdown(wait=True, cancel_futures=True)
                except Exception:
                    pass
                try:
                    if manager is not None:
                        manager.shutdown()
                except Exception:
                    pass

            threading.Thread(target=_cleanup, args=(self.executor, self.manager), daemon=True).start()

            self.executor = None
            self.manager = None
            self.futures = {}
            self.queue = None

            # Clean up outputs for cancelled or processing jobs
            import os
            for name, job in self.jobs.items():
                if job.status in [JobStatus.QUEUED, JobStatus.PROCESSING, JobStatus.CANCELLED]:
                    job.status = JobStatus.CANCELLED
                    if os.path.exists(job.output_path):
                        try:
                            os.remove(job.output_path)
                        except Exception:
                            pass

    def is_finished(self):
        if not self.futures:
            return True
        return len(self.futures) == 0

    def get_results(self):
        # We can just return the jobs list
        return list(self.jobs.values())
