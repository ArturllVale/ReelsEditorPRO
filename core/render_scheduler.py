import concurrent.futures
from pathlib import Path
from core.video_processor import editar_video

class RenderScheduler:
    def __init__(self):
        self.executor = None
        self.futures = []

    def start(self, videos, output_dir, config, queue, num_workers):
        self.executor = concurrent.futures.ProcessPoolExecutor(max_workers=num_workers)
        self.futures = []
        for video_path in videos:
            future = self.executor.submit(editar_video, video_path, output_dir, config, queue)
            self.futures.append(future)

    def cancel(self):
        if self.executor:
            # Terminar os processos
            for proc in self.executor._processes.values():
                proc.terminate()
            self.executor.shutdown(wait=False, cancel_futures=True)
            self.executor = None
            self.futures = []

    def is_finished(self):
        if not self.futures:
            return True
        return all(future.done() for future in self.futures)

    def get_results(self):
        results = []
        for future in self.futures:
            if future.done():
                try:
                    results.append(future.result())
                except Exception as e:
                    results.append({"status": "error", "error": str(e)})
        return results
