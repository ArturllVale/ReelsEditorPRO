import os
from pathlib import Path
import numpy as np
from moviepy import VideoFileClip
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QGridLayout, 
                               QAbstractItemView, QPushButton, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem)
from PySide6.QtCore import Qt, Signal, QUrl, QSizeF
from PySide6.QtGui import QImage, QPixmap, QPainter, QColor, QFont
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QGraphicsVideoItem

def get_thumbnail(path):
    try:
        with VideoFileClip(path) as clip:
            frame = clip.get_frame(0.0)
            height, width, channel = frame.shape
            frame = np.copy(frame)
            bytesPerLine = 3 * width
            qImg = QImage(frame.data, width, height, bytesPerLine, QImage.Format_RGB888)
            return QPixmap.fromImage(qImg)
    except Exception as e:
        print(f"Erro thumbnail: {e}")
        return QPixmap()

class VideoPlayerCard(QWidget):
    def __init__(self, video_path):
        super().__init__()
        self.video_path = video_path
        # Tamanho total do card acomodando o video 9:16 + controles embaxio
        self.setFixedSize(225, 450) 
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # 1. Usar QGraphicsView para evitar problemas de Z-order com vídeos no Windows
        self.view = QGraphicsView(self)
        self.view.setFixedSize(225, 400) # Proporção exata 9:16
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.view.setStyleSheet("background-color: black; border: none;")
        
        self.scene = QGraphicsScene(0, 0, 225, 400)
        self.view.setScene(self.scene)
        
        # Camada 1: Vídeo
        self.video_item = QGraphicsVideoItem()
        self.video_item.setSize(QSizeF(225, 400))
        self.video_item.setAspectRatioMode(Qt.KeepAspectRatio)
        self.scene.addItem(self.video_item)
        
        self.player = QMediaPlayer()
        self.audio = QAudioOutput()
        self.player.setAudioOutput(self.audio)
        self.player.setVideoOutput(self.video_item)
        self.player.setSource(QUrl.fromLocalFile(video_path))
        
        # Camada 2: Thumbnail (Fica por cima do vídeo quando pausado/parado)
        self.thumbnail_item = QGraphicsPixmapItem()
        self.thumbnail_item.setZValue(1)
        self.scene.addItem(self.thumbnail_item)
        
        # Camada 3: Overlay (Textos e Imagens, sempre no topo)
        self.overlay_item = QGraphicsPixmapItem()
        self.overlay_item.setZValue(2)
        self.scene.addItem(self.overlay_item)
        
        self.controls_layout = QHBoxLayout()
        self.btn_play = QPushButton("▶")
        self.btn_play.setMaximumWidth(40)
        self.btn_play.clicked.connect(self.toggle_play)
        
        self.lbl_name = QLabel(Path(video_path).name)
        self.lbl_name.setStyleSheet("font-size: 8pt; color: #8A8AA0;")
        
        self.lbl_status = QLabel("Aguardando")
        self.lbl_status.setStyleSheet("font-size: 8pt; color: #E0E0E0;")
        
        self.controls_layout.addWidget(self.btn_play)
        self.controls_layout.addWidget(self.lbl_name)
        self.controls_layout.addStretch()
        self.controls_layout.addWidget(self.lbl_status)
        
        self.layout.addWidget(self.view)
        self.layout.addLayout(self.controls_layout)
        
        self.base_pixmap = get_thumbnail(video_path)
        if not self.base_pixmap.isNull():
            scaled_pix = self.base_pixmap.scaled(225, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.thumbnail_item.setPixmap(scaled_pix)
            self.thumbnail_item.setPos((225 - scaled_pix.width()) / 2, (400 - scaled_pix.height()) / 2)

        self.current_config = {}

    def toggle_play(self):
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
            self.btn_play.setText("▶")
        else:
            self.thumbnail_item.hide()
            self.player.play()
            self.btn_play.setText("⏸")

    def stop_playback(self):
        self.player.stop()
        self.btn_play.setText("▶")
        self.thumbnail_item.show()

    def update_status(self, status):
        self.lbl_status.setText(status)
        if status == "Concluído":
            self.lbl_status.setStyleSheet("font-size: 8pt; color: #00FFAA;")
        elif status == "Falha":
            self.lbl_status.setStyleSheet("font-size: 8pt; color: #FF4466;")
        else:
            self.lbl_status.setStyleSheet("font-size: 8pt; color: #E0E0E0;")

    def apply_preview(self, config):
        """Atualiza a camada de overlay transparente para bater com a exportação"""
        if hasattr(config, 'to_config_dict'):
            config = config.to_config_dict()
        self.current_config = config
        
        # Limpar overlay atual
        pix = QPixmap(225, 400)
        pix.fill(Qt.transparent)
        painter = QPainter(pix)
        
        # Mirror da Thumbnail
        if config.get("enable_mirror", False):
            if not self.base_pixmap.isNull():
                img = self.base_pixmap.toImage().mirrored(True, False)
                scaled_pix = QPixmap.fromImage(img).scaled(225, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.thumbnail_item.setPixmap(scaled_pix)
                self.thumbnail_item.setPos((225 - scaled_pix.width()) / 2, (400 - scaled_pix.height()) / 2)
        else:
             if not self.base_pixmap.isNull():
                scaled_pix = self.base_pixmap.scaled(225, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.thumbnail_item.setPixmap(scaled_pix)
                self.thumbnail_item.setPos((225 - scaled_pix.width()) / 2, (400 - scaled_pix.height()) / 2)

        # Precisamos descobrir a dimensão real do vídeo renderizado no card (KeepAspectRatio)
        # Assumindo que o QGraphicsVideoItem e QGraphicsPixmapItem centralizam
        vid_w = 225
        vid_h = 400
        margin = 10 # Margem visual menor para o preview
        # Desenho unificado para imagens
        def draw_img(painter, ip, scale_pct, pos_x, pos_y, opacity=100):
            if not ip or not os.path.exists(ip): return
            img = QPixmap(ip)
            if img.isNull(): return
            w = max(1, int(vid_w * (scale_pct / 100.0)))
            img = img.scaledToWidth(w, Qt.SmoothTransformation)
            x = int((vid_w - img.width()) * (pos_x / 100.0))
            y = int((vid_h - img.height()) * (pos_y / 100.0))
            painter.setOpacity(opacity / 100.0)
            painter.drawPixmap(x, y, img)
            painter.setOpacity(1.0)

        # Draw Overlay Principal
        if config.get("enable_overlay", False) and config.get("overlay_path"):
            draw_img(painter, config.get("overlay_path"), config.get("overlay_scale", 15), config.get("overlay_x", 0), config.get("overlay_y", 0))
            
        # Draw Imagens Extras
        for e in config.get("extra_images", []):
            draw_img(painter, e["path"], e["scale"], e.get("pos_x", 0), e.get("pos_y", 0), e.get("opacity", 100))
            
        # Draw Textos
        for t in config.get("texts", []):
            txt = t.get("content", "")
            if not txt: continue
            
            f_size = max(8, int(t.get("size", 50) * (vid_w / 1080.0))) 
            font = QFont("Arial", f_size, QFont.Bold)
            painter.setFont(font)
            
            # Calcular boundingRect
            fm = painter.fontMetrics()
            br = fm.boundingRect(txt)
            tw, th = br.width(), br.height()
            
            pos_x = t.get("x", 50)
            pos_y = t.get("y", 50)
            x = int((vid_w - tw) * (pos_x / 100.0))
            y = int((vid_h - th) * (pos_y / 100.0)) + th
            
            # Opacidade
            opacity = t.get("opacity", 100) / 100.0
            painter.setOpacity(opacity)
            
            if t.get("shadow", True):
                painter.setPen(QColor("black"))
                painter.drawText(x+1, y+1, txt)
                painter.drawText(x-1, y-1, txt)
                
            painter.setPen(QColor(t.get("color", "white")))
            painter.drawText(x, y, txt)
            
            painter.setOpacity(1.0)

        painter.end()
        self.overlay_item.setPixmap(pix)


class VideoGridArea(QScrollArea):
    files_dropped = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setWidgetResizable(True)
        self.container = QWidget()
        self.grid = QGridLayout(self.container)
        self.setWidget(self.container)
        
        # Flow Layout manual usando Grid
        self.columns = 3
        self.cards = []
        
    def add_videos(self, paths):
        for p in paths:
            card = VideoPlayerCard(p)
            self.cards.append(card)
        self._refresh_layout()

    def clear_videos(self):
        for card in self.cards:
            card.stop_playback()
            self.grid.removeWidget(card)
            card.deleteLater()
        self.cards.clear()
        
    def _refresh_layout(self):
        # Remove old
        for i in reversed(range(self.grid.count())): 
            self.grid.itemAt(i).widget().setParent(None)
            
        # Re-add
        row, col = 0, 0
        for card in self.cards:
            self.grid.addWidget(card, row, col)
            col += 1
            if col >= self.columns:
                col = 0
                row += 1

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Adaptar numero de colunas ao resize
        new_cols = max(1, self.width() // 250)
        if new_cols != self.columns:
            self.columns = new_cols
            self._refresh_layout()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls(): event.accept()
        else: event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls(): event.accept()
        else: event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.CopyAction)
            event.accept()
            links = []
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    p = url.toLocalFile()
                    ext = Path(p).suffix.lower()
                    if ext in [".mp4", ".mov", ".avi", ".mkv"]:
                        links.append(p)
            if links:
                self.files_dropped.emit(links)
        else:
            event.ignore()
