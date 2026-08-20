import pytest
from domain.models import Project
from domain.composition import build_composition_plan

def test_composition_plan_coordinates_and_sizes():
    # Setup
    config = {
        'enable_mirror': True,
        'enable_overlay': True,
        'overlay_path': 'fake_overlay.png',
        'overlay_x': 10,
        'overlay_y': 20,
        'overlay_scale': 15,
        'extra_images': [
            {'path': 'fake_extra.png', 'scale': 50, 'pos_x': 25, 'pos_y': 75, 'opacity': 50}
        ],
        'texts': [
            {'content': 'Hello', 'size': 100, 'color': 'red', 'x': 30, 'y': 40, 'opacity': 90, 'shadow': False}
        ]
    }

    project = Project.from_dict(config)

    # Render for 1080x1920 (Export scenario)
    plan = build_composition_plan(project, 1080, 1920)

    assert plan.target_width == 1080
    assert plan.target_height == 1920
    assert plan.enable_mirror is True
    assert len(plan.elements) == 3

    # 1. Overlay
    ovl = plan.elements[0]
    assert ovl.type == "image"
    assert ovl.content == 'fake_overlay.png'
    assert ovl.x_pct == 0.1
    assert ovl.y_pct == 0.2
    assert ovl.image_width == int(1080 * 0.15) # 162

    # 2. Extra Image
    ext = plan.elements[1]
    assert ext.type == "image"
    assert ext.content == 'fake_extra.png'
    assert ext.x_pct == 0.25
    assert ext.y_pct == 0.75
    assert ext.opacity == 0.5
    assert ext.image_width == int(1080 * 0.50) # 540

    # 3. Text
    txt = plan.elements[2]
    assert txt.type == "text"
    assert txt.content == 'Hello'
    assert txt.x_pct == 0.3
    assert txt.y_pct == 0.4
    assert txt.opacity == 0.9
    # font_size = size * (target_width / 1080) -> 100 * (1080/1080) = 100
    assert txt.font_size == 100
    assert txt.color == 'red'
    assert txt.shadow is False

def test_composition_plan_for_preview():
    # Similar config, testing scaling down for UI (225x400)
    config = {
        'enable_mirror': False,
        'enable_overlay': False,
        'texts': [
            {'content': 'SmallText', 'size': 50, 'color': 'white', 'x': 0, 'y': 0}
        ]
    }
    project = Project.from_dict(config)
    plan = build_composition_plan(project, 225, 400)

    assert plan.target_width == 225
    assert len(plan.elements) == 1

    txt = plan.elements[0]
    # base font size is 50, target_width is 225 -> 50 * (225 / 1080.0) = ~10.4 -> 10
    assert txt.font_size == 10
