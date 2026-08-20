from dataclasses import dataclass, field
from typing import List, Dict, Any, ClassVar, Union


@dataclass
class VideoMetadata:
    """Metadados extraídos do vídeo."""
    width: int = 0
    height: int = 0
    duration: float = 0.0
    fps: float = 0.0
    codec: str = ""
    has_audio: bool = False
    audio_codec: str = ""
    rotation: int = 0


@dataclass
class Media:
    """Representa a lista de mídias/vídeos no projeto de edição."""
    paths: List[str] = field(default_factory=list)


@dataclass
class Composition:
    """Configurações da composição do projeto."""
    enable_mirror: bool = True


@dataclass
class OverlayLayer:
    """Camada de overlay principal."""
    enabled: bool = True
    path: str = ""
    pos_x: int = 0
    pos_y: int = 0
    scale: int = 15


@dataclass
class ImageLayer:
    """Camada de imagem extra."""
    path: str = ""
    scale: int = 15
    pos_x: int = 50
    pos_y: int = 50
    opacity: int = 100


@dataclass
class TextLayer:
    """Camada de texto."""
    content: str = ""
    size: int = 50
    color: str = "white"
    pos_x: int = 50
    pos_y: int = 50
    opacity: int = 100
    shadow: bool = True


@dataclass
class Layers:
    """Agrupador de camadas do projeto de edição."""
    overlay: OverlayLayer = field(default_factory=OverlayLayer)
    extra_images: List[ImageLayer] = field(default_factory=list)
    texts: List[TextLayer] = field(default_factory=list)


@dataclass
class ExportSettings:
    """Configurações de exportação do projeto."""
    MAX_GPU_WORKERS: ClassVar[int] = 2
    GPU_CODECS: ClassVar[set] = {"h264_nvenc", "h264_amf"}

    output_dir: str = ""
    bitrate: str = "Original"
    codec: str = "libx264"
    keep_fps: bool = True
    num_workers: int = 1

    @property
    def acceleration_type(self) -> str:
        """Retorna o tipo de aceleração de hardware associado ao codec."""
        if self.codec == "h264_nvenc":
            return "NVIDIA"
        elif self.codec == "h264_amf":
            return "AMD"
        return "CPU"

    def is_gpu_codec(self_or_codec: Union[str, "ExportSettings"] = None) -> bool:
        """Determina se o codec informado (ou da instância) utiliza aceleração de GPU."""
        if self_or_codec is None:
            return False
        if isinstance(self_or_codec, ExportSettings):
            return self_or_codec.codec in ExportSettings.GPU_CODECS
        if isinstance(self_or_codec, str):
            return self_or_codec in ExportSettings.GPU_CODECS
        return False


@dataclass
class Project:
    """Modelo principal do projeto de edição de vídeo."""
    media: Media = field(default_factory=Media)
    composition: Composition = field(default_factory=Composition)
    layers: Layers = field(default_factory=Layers)
    export_settings: ExportSettings = field(default_factory=ExportSettings)

    def to_config_dict(self) -> Dict[str, Any]:
        """Converte o Project para a estrutura de dicionário utilizada pelo processamento atual."""
        return {
            "enable_mirror": self.composition.enable_mirror,
            "enable_overlay": self.layers.overlay.enabled,
            "overlay_path": self.layers.overlay.path,
            "overlay_x": self.layers.overlay.pos_x,
            "overlay_y": self.layers.overlay.pos_y,
            "overlay_scale": self.layers.overlay.scale,
            "bitrate": self.export_settings.bitrate,
            "keep_fps": self.export_settings.keep_fps,
            "codec": self.export_settings.codec,
            "output_dir": self.export_settings.output_dir,
            "num_workers": self.export_settings.num_workers,
            "extra_images": [
                {
                    "path": img.path,
                    "scale": img.scale,
                    "pos_x": img.pos_x,
                    "pos_y": img.pos_y,
                    "opacity": img.opacity,
                }
                for img in self.layers.extra_images
            ],
            "texts": [
                {
                    "content": txt.content,
                    "size": txt.size,
                    "color": txt.color,
                    "x": txt.pos_x,
                    "y": txt.pos_y,
                    "opacity": txt.opacity,
                    "shadow": txt.shadow,
                }
                for txt in self.layers.texts
            ],
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Project":
        """Cria uma instância de Project a partir de um dicionário de configurações legado."""
        if not isinstance(d, dict):
            d = {}

        overlay = OverlayLayer(
            enabled=d.get("enable_overlay", True),
            path=d.get("overlay_path", ""),
            pos_x=d.get("overlay_x", 0),
            pos_y=d.get("overlay_y", 0),
            scale=d.get("overlay_scale", 15),
        )

        extra_images = []
        for img in d.get("extra_images", []):
            if isinstance(img, dict):
                extra_images.append(
                    ImageLayer(
                        path=img.get("path", ""),
                        scale=img.get("scale", 15),
                        pos_x=img.get("pos_x", 50),
                        pos_y=img.get("pos_y", 50),
                        opacity=img.get("opacity", 100),
                    )
                )

        texts = []
        for t in d.get("texts", []):
            if isinstance(t, dict):
                texts.append(
                    TextLayer(
                        content=t.get("content", ""),
                        size=t.get("size", 50),
                        color=t.get("color", "white"),
                        pos_x=t.get("x", t.get("pos_x", 50)),
                        pos_y=t.get("y", t.get("pos_y", 50)),
                        opacity=t.get("opacity", 100),
                        shadow=t.get("shadow", True),
                    )
                )

        layers = Layers(
            overlay=overlay,
            extra_images=extra_images,
            texts=texts,
        )

        composition = Composition(
            enable_mirror=d.get("enable_mirror", True)
        )

        media = Media(
            paths=list(d.get("media_paths", d.get("videos", [])))
        )

        export_settings = ExportSettings(
            output_dir=d.get("output_dir", ""),
            bitrate=d.get("bitrate", "Original"),
            codec=d.get("codec", "libx264"),
            keep_fps=d.get("keep_fps", True),
            num_workers=d.get("num_workers", 1),
        )

        return cls(
            media=media,
            composition=composition,
            layers=layers,
            export_settings=export_settings,
        )

    @classmethod
    def from_ui(cls, ui) -> "Project":
        """Converte o estado atual da interface gráfica em um objeto Project."""
        codec_map = {
            "CPU (libx264)": "libx264",
            "GPU NVIDIA (h264_nvenc)": "h264_nvenc",
            "GPU AMD (h264_amf)": "h264_amf",
        }

        extra_imgs = []
        if hasattr(ui, "table_extra_imgs"):
            for row in range(ui.table_extra_imgs.rowCount()):
                path_item = ui.table_extra_imgs.item(row, 0)
                path = path_item.text() if path_item else ""
                scale = ui.table_extra_imgs.cellWidget(row, 1).value() if ui.table_extra_imgs.cellWidget(row, 1) else 15
                pos_x = ui.table_extra_imgs.cellWidget(row, 2).value() if ui.table_extra_imgs.cellWidget(row, 2) else 50
                pos_y = ui.table_extra_imgs.cellWidget(row, 3).value() if ui.table_extra_imgs.cellWidget(row, 3) else 50
                opacity_widget = ui.table_extra_imgs.cellWidget(row, 4)
                opacity = opacity_widget.value() if opacity_widget else 100

                extra_imgs.append(
                    ImageLayer(
                        path=path,
                        scale=scale,
                        pos_x=pos_x,
                        pos_y=pos_y,
                        opacity=opacity,
                    )
                )

        texts = []
        if hasattr(ui, "table_texts"):
            for row in range(ui.table_texts.rowCount()):
                txt_widget = ui.table_texts.cellWidget(row, 0)
                content = txt_widget.text() if txt_widget else ""
                size_widget = ui.table_texts.cellWidget(row, 1)
                size = size_widget.value() if size_widget else 50
                color_widget = ui.table_texts.cellWidget(row, 2)
                color = color_widget.text() if color_widget else "white"
                x_widget = ui.table_texts.cellWidget(row, 3)
                pos_x = x_widget.value() if x_widget else 50
                y_widget = ui.table_texts.cellWidget(row, 4)
                pos_y = y_widget.value() if y_widget else 50
                opac_widget = ui.table_texts.cellWidget(row, 5)
                opacity = opac_widget.value() if opac_widget else 100

                shadow_container = ui.table_texts.cellWidget(row, 6)
                shadow = True
                if shadow_container and shadow_container.layout() and shadow_container.layout().count() > 0:
                    chk = shadow_container.layout().itemAt(0).widget()
                    if chk:
                        shadow = chk.isChecked()

                texts.append(
                    TextLayer(
                        content=content,
                        size=size,
                        color=color,
                        pos_x=pos_x,
                        pos_y=pos_y,
                        opacity=opacity,
                        shadow=shadow,
                    )
                )

        overlay = OverlayLayer(
            enabled=ui.chk_overlay.isChecked() if hasattr(ui, "chk_overlay") else True,
            path=ui.txt_overlay_path.text() if hasattr(ui, "txt_overlay_path") else "",
            pos_x=ui.spin_overlay_x.value() if hasattr(ui, "spin_overlay_x") else 0,
            pos_y=ui.spin_overlay_y.value() if hasattr(ui, "spin_overlay_y") else 0,
            scale=ui.spin_scale.value() if hasattr(ui, "spin_scale") else 15,
        )

        layers = Layers(
            overlay=overlay,
            extra_images=extra_imgs,
            texts=texts,
        )

        composition = Composition(
            enable_mirror=ui.chk_mirror.isChecked() if hasattr(ui, "chk_mirror") else True
        )

        media_paths = []
        if hasattr(ui, "grid_area") and hasattr(ui.grid_area, "cards"):
            media_paths = [card.video_path for card in ui.grid_area.cards]

        export_settings = ExportSettings(
            output_dir=ui.txt_out_dir.text() if hasattr(ui, "txt_out_dir") else "",
            bitrate=ui.cmb_bitrate.currentText() if hasattr(ui, "cmb_bitrate") else "Original",
            codec=codec_map.get(ui.cmb_codec.currentText(), "libx264") if hasattr(ui, "cmb_codec") else "libx264",
            keep_fps=ui.chk_fps.isChecked() if hasattr(ui, "chk_fps") else True,
            num_workers=ui.spin_workers.value() if hasattr(ui, "spin_workers") else 1,
        )

        return cls(
            media=Media(paths=media_paths),
            composition=composition,
            layers=layers,
            export_settings=export_settings,
        )
