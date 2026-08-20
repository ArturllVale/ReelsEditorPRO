import os
from pathlib import Path
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QGroupBox, QCheckBox, QLineEdit, QPushButton, QComboBox, 
                             QSpinBox, QProgressBar, QTextEdit, QLabel, QFileDialog, 
                             QHeaderView, QTableWidgetItem, QMessageBox, QGridLayout, QScrollArea, QTableWidget, QAbstractItemView)
from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QAction, QIcon

from domain.models import Project
from ui.custom_widgets import VideoGridArea
from utils.config_manager import ConfigManager
from core.render_service import RenderService
from core.video_processor import editar_video

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ReelsEditorPRO - Cyberpunk Edition")
        self.setMinimumSize(1200, 800)
        self.config_manager = ConfigManager()
        self.render_service = RenderService()
        self.video_progress = {}

        self._create_menu()
        self._setup_ui()
        self._load_settings()
        self._connect_signals()

    def _create_menu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("Arquivo")
        
        add_action = QAction("Adicionar Vídeos...", self)
        add_action.triggered.connect(self._add_videos)
        file_menu.addAction(add_action)
        
        clear_action = QAction("Limpar Lista", self)
        clear_action.triggered.connect(self._clear_videos)
        file_menu.addAction(clear_action)
        
        out_action = QAction("Selecionar Pasta de Saída...", self)
        out_action.triggered.connect(self._select_output_dir)
        file_menu.addAction(out_action)
        
        help_menu = menubar.addMenu("Ajuda")
        about_action = QAction("Sobre", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        top_layout = QHBoxLayout()
        
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        self.grid_area = VideoGridArea()
        self.grid_area.files_dropped.connect(self._add_videos_from_paths)
        
        left_layout.addWidget(QLabel("Lista de Vídeos (Arraste e solte arquivos aqui)"))
        left_layout.addWidget(self.grid_area)
        top_layout.addWidget(left_panel, stretch=75)
        
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setFrameShape(QScrollArea.NoFrame)
        right_scroll.setStyleSheet("QScrollArea { background-color: transparent; }")
        right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        right_scroll.setMinimumWidth(400)
        
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 0, 10, 0)
        
        group_fx = QGroupBox("Efeitos Base")
        fx_layout = QVBoxLayout(group_fx)
        self.chk_mirror = QCheckBox("Ativar Espelhamento Horizontal")
        self.chk_overlay = QCheckBox("Ativar Overlay Principal")
        
        overlay_path_layout = QHBoxLayout()
        self.txt_overlay_path = QLineEdit()
        self.txt_overlay_path.setPlaceholderText("Caminho (PNG)...")
        btn_browse_overlay = QPushButton("...")
        btn_browse_overlay.setMaximumWidth(40)
        btn_browse_overlay.clicked.connect(self._browse_overlay)
        overlay_path_layout.addWidget(self.txt_overlay_path)
        overlay_path_layout.addWidget(btn_browse_overlay)
        
        overlay_settings_layout = QGridLayout()
        overlay_settings_layout.addWidget(QLabel("Pos X(%):"), 0, 0)
        self.spin_overlay_x = QSpinBox()
        self.spin_overlay_x.setRange(0, 100)
        overlay_settings_layout.addWidget(self.spin_overlay_x, 0, 1)
        
        overlay_settings_layout.addWidget(QLabel("Pos Y(%):"), 1, 0)
        self.spin_overlay_y = QSpinBox()
        self.spin_overlay_y.setRange(0, 100)
        overlay_settings_layout.addWidget(self.spin_overlay_y, 1, 1)
        
        overlay_settings_layout.addWidget(QLabel("Escala (%):"), 2, 0)
        self.spin_scale = QSpinBox()
        self.spin_scale.setRange(5, 100)
        overlay_settings_layout.addWidget(self.spin_scale, 2, 1)
        
        fx_layout.addWidget(self.chk_mirror)
        fx_layout.addWidget(self.chk_overlay)
        fx_layout.addLayout(overlay_path_layout)
        fx_layout.addLayout(overlay_settings_layout)
        right_layout.addWidget(group_fx)

        # 1B. Grupo Imagens Extras
        group_extra_imgs = QGroupBox("Imagens Extras")
        extra_img_layout = QVBoxLayout(group_extra_imgs)
        self.table_extra_imgs = QTableWidget(0, 5)
        self.table_extra_imgs.setHorizontalHeaderLabels(["Caminho", "Esc.(%)", "X(%)", "Y(%)", "Opac"])
        h_img = self.table_extra_imgs.horizontalHeader()
        h_img.setSectionResizeMode(0, QHeaderView.Interactive)
        self.table_extra_imgs.setColumnWidth(0, 150)
        h_img.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        h_img.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        h_img.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        h_img.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table_extra_imgs.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_extra_imgs.setMinimumHeight(180)
        self.table_extra_imgs.verticalHeader().setDefaultSectionSize(40)
        
        img_btns_layout = QHBoxLayout()
        btn_add_img = QPushButton("+ Adicionar Imagem")
        btn_add_img.clicked.connect(self._add_extra_image)
        btn_rem_img = QPushButton("- Remover Selecionada")
        btn_rem_img.clicked.connect(self._remove_extra_image)
        img_btns_layout.addWidget(btn_add_img)
        img_btns_layout.addWidget(btn_rem_img)
        
        extra_img_layout.addWidget(self.table_extra_imgs)
        extra_img_layout.addLayout(img_btns_layout)
        right_layout.addWidget(group_extra_imgs)

        group_text = QGroupBox("Textos")
        text_layout = QVBoxLayout(group_text)
        
        self.table_texts = QTableWidget(0, 7)
        self.table_texts.setHorizontalHeaderLabels(["Texto", "Tam", "Cor", "X(%)", "Y(%)", "Opac", "Som."])
        h_txt = self.table_texts.horizontalHeader()
        h_txt.setSectionResizeMode(0, QHeaderView.Interactive)
        self.table_texts.setColumnWidth(0, 150)
        for i in range(1, 7):
            h_txt.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        self.table_texts.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_texts.setMinimumHeight(180)
        self.table_texts.verticalHeader().setDefaultSectionSize(40)
        
        txt_btns_layout = QHBoxLayout()
        btn_add_txt = QPushButton("+ Adicionar Texto")
        btn_add_txt.clicked.connect(self._add_text)
        btn_rem_txt = QPushButton("- Remover Selecionado")
        btn_rem_txt.clicked.connect(self._remove_text)
        txt_btns_layout.addWidget(btn_add_txt)
        txt_btns_layout.addWidget(btn_rem_txt)
        
        text_layout.addWidget(self.table_texts)
        text_layout.addLayout(txt_btns_layout)
        right_layout.addWidget(group_text)
        
        group_export = QGroupBox("Exportação")
        export_layout = QGridLayout(group_export)
        
        export_layout.addWidget(QLabel("Pasta de Saída:"), 0, 0)
        out_dir_layout = QHBoxLayout()
        self.txt_out_dir = QLineEdit()
        btn_browse_out = QPushButton("...")
        btn_browse_out.setMaximumWidth(40)
        btn_browse_out.clicked.connect(self._select_output_dir)
        out_dir_layout.addWidget(self.txt_out_dir)
        out_dir_layout.addWidget(btn_browse_out)
        export_layout.addLayout(out_dir_layout, 0, 1)
        
        export_layout.addWidget(QLabel("Bitrate:"), 1, 0)
        self.cmb_bitrate = QComboBox()
        self.cmb_bitrate.addItems(["Original", "3000k", "5000k", "8000k"])
        export_layout.addWidget(self.cmb_bitrate, 1, 1)
        
        export_layout.addWidget(QLabel("Workers:"), 2, 0)
        self.spin_workers = QSpinBox()
        self.spin_workers.setRange(1, os.cpu_count())
        self.spin_workers.setValue(max(1, os.cpu_count() - 1))
        export_layout.addWidget(self.spin_workers, 2, 1)
        
        export_layout.addWidget(QLabel("Aceleração / Codec:"), 3, 0)
        self.cmb_codec = QComboBox()
        self.cmb_codec.addItems(["CPU (libx264)", "GPU NVIDIA (h264_nvenc)", "GPU AMD (h264_amf)"])
        export_layout.addWidget(self.cmb_codec, 3, 1)
        
        self.chk_fps = QCheckBox("Manter FPS")
        export_layout.addWidget(self.chk_fps, 4, 0)
        
        right_layout.addWidget(group_export)
        
        self.txt_log = QTextEdit()
        self.txt_log.hide() # Ocultado a pedido do usuario
        right_layout.addWidget(self.txt_log)
        
        self.btn_start = QPushButton("🚀 INICIAR")
        self.btn_start.setObjectName("btn_start")
        self.btn_start.clicked.connect(self._start_processing)
        
        self.btn_cancel = QPushButton("⏹️ CANCELAR")
        self.btn_cancel.setObjectName("btn_cancel")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self._cancel_processing)
        
        right_layout.addWidget(self.btn_start)
        right_layout.addWidget(self.btn_cancel)
        
        right_layout.addStretch()
        right_scroll.setWidget(right_panel)
        top_layout.addWidget(right_scroll, stretch=25)
        
        main_layout.addLayout(top_layout, stretch=7)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        main_layout.addWidget(self.progress_bar)

    def _connect_signals(self):
        self.chk_mirror.stateChanged.connect(self._update_previews)
        self.chk_overlay.stateChanged.connect(self._update_previews)
        self.spin_overlay_x.valueChanged.connect(self._update_previews)
        self.spin_overlay_y.valueChanged.connect(self._update_previews)
        self.spin_scale.valueChanged.connect(self._update_previews)

        self.render_service.progress_updated.connect(self._on_progress_updated)
        self.render_service.log_updated.connect(self._update_log_display)
        self.render_service.video_status_updated.connect(self._on_video_status_updated)
        self.render_service.processing_finished.connect(self._on_processing_finished)
        self.render_service.processing_cancelled.connect(self._on_processing_cancelled)

    def _get_current_project(self) -> Project:
        return Project.from_ui(self)

    def _get_current_config(self):
        return self._get_current_project().to_config_dict()

    def _update_previews(self):
        project = self._get_current_project()
        for card in self.grid_area.cards:
            card.apply_preview(project)

    def _add_extra_image(self):
        f, _ = QFileDialog.getOpenFileName(self, "Selecionar Imagem Extra", "", "Imagens (*.png *.jpg *.jpeg)")
        if f:
            row = self.table_extra_imgs.rowCount()
            self.table_extra_imgs.insertRow(row)
            self.table_extra_imgs.setItem(row, 0, QTableWidgetItem(f))
            for col in range(1, 5):
                spin = QSpinBox()
                spin.setRange(0, 100)
                spin.setValue(15 if col == 1 else (100 if col == 4 else 50))
                spin.valueChanged.connect(self._update_previews)
                self.table_extra_imgs.setCellWidget(row, col, spin)
            self._update_previews()

    def _add_text(self):
        row = self.table_texts.rowCount()
        self.table_texts.insertRow(row)
        txt_edit = QLineEdit("Novo Texto")
        txt_edit.textChanged.connect(self._update_previews)
        self.table_texts.setCellWidget(row, 0, txt_edit)
        
        spin_sz = QSpinBox()
        spin_sz.setRange(10, 200)
        spin_sz.setValue(50)
        spin_sz.valueChanged.connect(self._update_previews)
        self.table_texts.setCellWidget(row, 1, spin_sz)
        
        txt_color = QLineEdit("white")
        txt_color.textChanged.connect(self._update_previews)
        self.table_texts.setCellWidget(row, 2, txt_color)
        
        for i in range(3, 6):
            spin = QSpinBox()
            spin.setRange(0, 100 if i != 3 else 100)
            spin.setValue(50 if i < 5 else 100)
            spin.valueChanged.connect(self._update_previews)
            self.table_texts.setCellWidget(row, i, spin)
            
        chk_sh = QCheckBox()
        chk_sh.setChecked(True)
        chk_sh.stateChanged.connect(self._update_previews)
        chk_widget = QWidget()
        chk_layout = QHBoxLayout(chk_widget)
        chk_layout.addWidget(chk_sh)
        chk_layout.setContentsMargins(0,0,0,0)
        self.table_texts.setCellWidget(row, 6, chk_widget)
        self._update_previews()

    def _remove_text(self):
        row = self.table_texts.currentRow()
        if row >= 0: self.table_texts.removeRow(row); self._update_previews()

    def _remove_extra_image(self):
        row = self.table_extra_imgs.currentRow()
        if row >= 0: self.table_extra_imgs.removeRow(row); self._update_previews()

    def _load_settings(self):
        self.txt_out_dir.setText(self.config_manager.get("output_dir", ""))
        self.chk_mirror.setChecked(self.config_manager.get("enable_mirror", True))
        # ... (simplified loader for brevity)

    def _save_settings(self):
        cfg = self._get_current_config()
        cfg["output_dir"] = self.txt_out_dir.text()
        for k, v in cfg.items(): self.config_manager.set(k, v)
        self.config_manager.save()

    def closeEvent(self, event):
        self._save_settings()
        self._cancel_processing()
        event.accept()

    def _add_videos(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Selecionar Vídeos", "", "Vídeos (*.mp4 *.mov *.avi *.mkv)")
        if files: self._add_videos_from_paths(files)

    def _add_videos_from_paths(self, paths):
        self.grid_area.add_videos(paths)
        self._update_previews()

    def _clear_videos(self): self.grid_area.clear_videos()

    def _select_output_dir(self):
        d = QFileDialog.getExistingDirectory(self, "Selecionar Pasta de Saída")
        if d: self.txt_out_dir.setText(d)

    def _browse_overlay(self):
        f, _ = QFileDialog.getOpenFileName(self, "Selecionar Overlay")
        if f: self.txt_overlay_path.setText(f); self._update_previews()

    def _show_about(self): QMessageBox.about(self, "Sobre", "ReelsEditorPRO - Cyberpunk Edition")

    def _start_processing(self):
        videos = [c.video_path for c in self.grid_area.cards]
        output_dir = self.txt_out_dir.text()
        if not videos or not output_dir: return
        
        self.btn_start.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.video_progress.clear()
        
        num_workers = self.spin_workers.value()
        config = self._get_current_config()
        
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat(f"Iniciando {len(videos)} vídeos...")
        
        self.render_service.start_processing(videos, output_dir, config, num_workers)



    def _on_progress_updated(self, vid_name, pct):
        self.video_progress[vid_name] = pct

    def _update_log_display(self, progress_dict=None):
        if progress_dict is not None:
            self.video_progress = progress_dict

        total = len(self.video_progress)
        if total == 0: return
        
        completed = sum(1 for pct in self.video_progress.values() if pct >= 100)
        avg_pct = int(sum(self.video_progress.values()) / total)
        
        current_vid = min(completed + 1, total)
        self.progress_bar.setValue(avg_pct)
        self.progress_bar.setFormat(f"Convertendo vídeo {current_vid}/{total} - %p%")

    def _on_video_status_updated(self, vid_name, status):
        for card in self.grid_area.cards:
            if Path(card.video_path).name == vid_name:
                card.update_status(status)

    def _on_processing_finished(self):
        self.btn_start.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.progress_bar.setFormat(f"Processamento Concluído! - 100%")

    def _on_processing_cancelled(self):
        self.progress_bar.setFormat(f"Processamento CANCELADO!")
        self.btn_start.setEnabled(True)
        self.btn_cancel.setEnabled(False)

    def _cancel_processing(self):
        self.render_service.cancel_processing()
