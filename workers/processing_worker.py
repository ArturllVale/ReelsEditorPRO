import concurrent.futures
from PySide6.QtCore import QThread, Signal
from core.video_processor import editar_video

class ProcessingWorker(QThread):
    # Signals para atualizar a UI
    log_signal = Signal(str, str)  # mensagem, level (info, success, error, warning)
    progress_signal = Signal(int, int)  # atual, total
    video_status_signal = Signal(str, str)  # arquivo, status (Sucesso, Falha)
    finished_signal = Signal()

    def __init__(self, videos_list, output_dir, config, num_workers):
        super().__init__()
        self.videos_list = videos_list # lista de caminhos (strings)
        self.output_dir = output_dir
        self.config = config
        self.num_workers = num_workers
        self._cancelar = False

    def run(self):
        self.log_signal.emit(f"Iniciando processamento de {len(self.videos_list)} vídeo(s) com {self.num_workers} worker(s)...", "info")
        
        total = len(self.videos_list)
        processados = 0
        
        # Usamos ProcessPoolExecutor para contornar o GIL e processar pesadamente usando os núcleos do PC.
        with concurrent.futures.ProcessPoolExecutor(max_workers=self.num_workers) as executor:
            # Submete todas as tarefas
            futures = {
                executor.submit(editar_video, video, self.output_dir, self.config): video
                for video in self.videos_list
            }
            
            for future in concurrent.futures.as_completed(futures):
                if self._cancelar:
                    self.log_signal.emit("Cancelamento solicitado. Interrompendo...", "warning")
                    executor.shutdown(wait=False, cancel_futures=True)
                    break
                
                try:
                    resultado = future.result()
                    processados += 1
                    self.progress_signal.emit(processados, total)
                    
                    if resultado["status"] == "success":
                        self.log_signal.emit(f"[{processados}/{total}] Sucesso: {resultado['file']}", "success")
                        self.video_status_signal.emit(resultado['file'], "Concluído")
                    else:
                        self.log_signal.emit(f"[{processados}/{total}] Falha: {resultado['file']} - {resultado.get('error', 'Erro Desconhecido')}", "error")
                        self.video_status_signal.emit(resultado['file'], "Falha")
                except Exception as e:
                    processados += 1
                    self.progress_signal.emit(processados, total)
                    video_path = futures[future]
                    self.log_signal.emit(f"[{processados}/{total}] Erro Crítico no processamento de {video_path}: {str(e)}", "error")
        
        if self._cancelar:
            self.log_signal.emit("Processamento cancelado pelo usuário.", "warning")
        else:
            self.log_signal.emit("Processamento finalizado com sucesso!", "success")
            
        self.finished_signal.emit()

    def cancelar(self):
        self._cancelar = True
