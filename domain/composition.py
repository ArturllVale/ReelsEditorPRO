from dataclasses import dataclass
from typing import List
from domain.models import Project

@dataclass
class RenderElement:
    type: str  # "image" or "text"
    content: str
    x_pct: float
    y_pct: float
    opacity: float

    # Calculated dimensions based on target_width
    image_width: int = 0
    font_size: int = 0

    # Text properties
    color: str = "white"
    shadow: bool = False

@dataclass
class CompositionPlan:
    target_width: int
    target_height: int
    enable_mirror: bool
    elements: List[RenderElement]


def build_composition_plan(project: Project, target_width: int, target_height: int) -> CompositionPlan:
    """
    Computes all absolute sizes and normalized coordinates so that both
    Preview (Qt) and Export (FFmpeg) use exactly the same business rules.
    """
    elements = []

    # 1. Overlay (Always rendered first if enabled)
    overlay = project.layers.overlay
    if overlay.enabled and overlay.path:
        elements.append(RenderElement(
            type="image",
            content=overlay.path,
            x_pct=overlay.pos_x / 100.0,
            y_pct=overlay.pos_y / 100.0,
            opacity=1.0,
            image_width=max(1, int(target_width * (overlay.scale / 100.0)))
        ))

    # 2. Extra Images
    for img in project.layers.extra_images:
        if img.path:
            elements.append(RenderElement(
                type="image",
                content=img.path,
                x_pct=img.pos_x / 100.0,
                y_pct=img.pos_y / 100.0,
                opacity=img.opacity / 100.0,
                image_width=max(1, int(target_width * (img.scale / 100.0)))
            ))

    # 3. Texts
    for txt in project.layers.texts:
        if txt.content:
            # Base width for texts is assumed to be 1080
            calculated_font_size = max(8, int(txt.size * (target_width / 1080.0)))
            elements.append(RenderElement(
                type="text",
                content=txt.content,
                x_pct=txt.pos_x / 100.0,
                y_pct=txt.pos_y / 100.0,
                opacity=txt.opacity / 100.0,
                font_size=calculated_font_size,
                color=txt.color,
                shadow=txt.shadow
            ))

    return CompositionPlan(
        target_width=target_width,
        target_height=target_height,
        enable_mirror=project.composition.enable_mirror,
        elements=elements
    )
