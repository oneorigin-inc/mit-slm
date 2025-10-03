import random
from typing import Dict, Any

def _rand_hex():
    return "#" + "".join(random.choice("0123456789ABCDEF") for _ in range(6))

def _pick_palette_color(palette):
    if random.random() < 0.7 and palette:
        return random.choice(palette)
    return _rand_hex()

def calculate_font_size(text: str, base_size: int) -> int:
    """Calculate font size based on text length within spec limits"""
    if not text:
        return base_size
    
    # Scale down for longer text, stay within 40-50 range
    if len(text) > 30:
        return max(base_size - 8, 40)
    elif len(text) > 20:
        return max(base_size - 4, 40)
    
    return min(base_size, 50)

def generate_badge_config(
    meta: dict,
    seed: int | None = None,
    logo_path: str = "assets/logos/wgu_logo.png",
):
    """Generate text-based badge configuration following spec"""
    if seed is not None:
        random.seed(seed)

    warm = ["#FF6F61", "#FF8C42", "#FFB703", "#FB8500", "#E76F51", "#D9544D"]
    cool = ["#118AB2", "#06D6A0", "#26547C", "#2A9D8F", "#457B9D", "#00B4D8"]
    neutrals = ["#000000", "#222222", "#333333", "#555555", "#777777", "#999999"]

    # Fixed canvas per spec
    canvas = {"width": 600, "height": 600}

    # Background layer (z: 0-9)
    background_layer = {
        "type": "BackgroundLayer",
        "mode": "solid",
        "color": "#FFFFFF00",
        "z": 0,
    }

    # Shape layer (z: 10-19)
    shape = random.choice(["hexagon", "circle", "rounded_rect"])
    
    fill_mode = random.choice(["solid", "gradient"])
    if fill_mode == "solid":
        fill = {
            "mode": "solid",
            "color": _pick_palette_color(warm + cool),
        }
    else:
        start = _pick_palette_color(warm)
        end = _pick_palette_color(cool if random.random() < 0.6 else warm)
        if end == start:
            end = _rand_hex()
        fill = {
            "mode": "gradient",
            "start_color": start,
            "end_color": end,
            "vertical": True,
        }

    # Border (optional per spec)
    if random.random() < 0.6:
        border = {
            "color": _pick_palette_color(neutrals + cool + warm),
            "width": random.randint(1, 6),
        }
    else:
        border = {
            "color": None,
            "width": 0
        }

    # Shape-specific params per spec
    if shape == "hexagon":
        params = {"radius": 250}
    elif shape == "circle":
        params = {"radius": 250}
    else:  # rounded_rect
        params = {
            "radius": random.randint(0, 100),
            "width": 450,
            "height": 450,
        }

    shape_layer = {
        "type": "ShapeLayer",
        "shape": shape,
        "fill": fill,
        "border": border,
        "params": params,
        "z": random.randint(10, 19),
    }

    # Logo layer (z: 20-29)
    logo_layer = {
        "type": "LogoLayer",
        "path": logo_path,
        "size": {"dynamic": True},
        "position": {"x": "center", "y": "dynamic"},
        "z": random.randint(20, 29),
    }

    # Smart text processing - always include subtitle for text layouts
    def _clip_smart(s, max_len=40):
        if not s:
            return ""
        s = str(s).strip()
        if len(s) <= max_len:
            return s
        return s[:max_len-1] + "…"

    title = _clip_smart(meta.get("badge_title") or "Badge Title")
    subtitle = _clip_smart(meta.get("subtitle") or "Certified Achievement")
    extra = _clip_smart(meta.get("extra_text") or "")

    # For text layouts, always include at least title + subtitle
    texts = [title, subtitle]
    if extra and len(title) <= 20 and len(subtitle) <= 20:  # Add third only if others are short
        texts.append(extra)

    # Text layers (z: 30-39)
    text_layers = []
    z_values = sorted(random.sample(range(30, 40), len(texts)))
    
    for idx, txt in enumerate(texts):
        if not txt:
            continue
            
        # Font size within spec (40-50)
        base_size = 48 if idx == 0 else 44 if idx == 1 else 40
        font_size = calculate_font_size(txt, base_size)
        
        color = _pick_palette_color(neutrals if idx == 0 else neutrals + cool + warm)
        
        # Line gap within spec (4-7)
        line_gap = random.randint(4, 7)
        
        text_layer = {
            "type": "TextLayer",
            "text": txt,
            "font": {
                "path": "assets/fonts/ArialBold.ttf" if idx == 0 else "assets/fonts/Arial.ttf",
                "size": font_size,
            },
            "color": color,
            "align": {"x": "center", "y": "dynamic"},
            "wrap": {
                "dynamic": True,
                "line_gap": line_gap,
            },
            "z": z_values[idx],
        }
        text_layers.append(text_layer)

    config = {
        "canvas": canvas,
        "layers": [
            # background_layer, added this layer in image-generation backend so no need to pass here
            shape_layer,
            logo_layer,
            *text_layers,
        ],
    }

    return config

def generate_badge_image_config(
    meta: dict,
    seed: int | None = None,
    icon_dir: str = "assets/icons/",
    suggested_icon: str | None = None,
):
    """Generate icon-based badge configuration"""
    if seed is not None:
        random.seed(seed)

    warm = ["#FF6F61", "#FF8C42", "#FFB703", "#FB8500", "#E76F51", "#D9544D"]
    cool = ["#118AB2", "#06D6A0", "#26547C", "#2A9D8F", "#457B9D", "#00B4D8"]
    neutrals = ["#000000", "#222222", "#333333", "#555555", "#777777", "#999999"]

    if suggested_icon:
        icon_file = suggested_icon
    else:
        icon_file = random.choice(["trophy.png", "goal.png", "solution.png", "diamond.png"])
    
    final_icon_path = icon_dir.rstrip("/") + "/" + icon_file

    canvas = {"width": 600, "height": 600}

    background_layer = {
        "type": "BackgroundLayer",
        "mode": "solid",
        "color": "#FFFFFF",
        "z": 0,
    }

    shape = random.choice(["hexagon", "circle", "rounded_rect"])
    z_shape = random.randint(10, 19)

    fill_mode = random.choice(["solid", "gradient"])
    if fill_mode == "solid":
        fill = {
            "mode": "solid",
            "color": _pick_palette_color(warm + cool)
        }
    else:
        start = _pick_palette_color(warm)
        end = _pick_palette_color(cool if random.random() < 0.6 else warm)
        if end == start:
            end = _rand_hex()
        fill = {
            "mode": "gradient",
            "start_color": start,
            "end_color": end,
            "vertical": True,
        }

    if random.random() < 0.6:
        border = {
            "color": _pick_palette_color(neutrals + cool + warm),
            "width": random.randint(1, 6),
        }
    else:
        border = {"color": None, "width": 0}

    if shape in ("hexagon", "circle"):
        params = {"radius": 250}
    else:
        params = {"radius": random.randint(0, 100), "width": 450, "height": 450}

    shape_layer = {
        "type": "ShapeLayer",
        "shape": shape,
        "fill": fill,
        "border": border,
        "params": params,
        "z": z_shape,
    }

    image_layer = {
        "type": "ImageLayer",
        "path": final_icon_path,
        "size": {"dynamic": True},
        "position": {"x": "center", "y": "center"},
        "z": random.randint(20, 29),
    }

    config = {
        "canvas": canvas,
        "layers": [
            # background_layer, added this layer in image-generation backend so no need to pass here
            shape_layer,
            image_layer
        ],
    }

    return config

async def generate_text_image_config(badge_name: str, badge_description: str, 
                                   image_text: dict, institution: str) -> dict:
    """Generate image configuration with optimized text overlay"""
    seed = random.randint(1, 10000)
    
    meta = {
        "badge_title": image_text.get("short_title", badge_name),
        "subtitle": image_text.get("institution_display", institution),
        "extra_text": image_text.get("achievement_phrase", "Achievement Unlocked")
    }
    
    config = generate_badge_config(
        meta=meta,
        seed=seed,
        logo_path="assets/logos/wgu_logo.png"
    )
    
    return {
        "layout_type": "text_overlay",
        "config": config,
        "image_text": image_text,
        "background_style": random.choice(["gradient", "solid", "pattern"]),
        "text_position": random.choice(["center", "bottom", "top"]),
        "color_scheme": random.choice(["professional", "vibrant", "minimal"]),
        "font_style": random.choice(["modern", "classic", "bold"]),
        "seed_used": seed
    }

async def generate_icon_image_config(badge_name: str, badge_description: str, 
                                   icon_suggestions: dict, institution: str) -> dict:
    """Generate image configuration with suggested icon"""
    
    suggested_icon = None
    if icon_suggestions and icon_suggestions.get('suggested_icon', {}).get('name'):
        suggested_icon = icon_suggestions['suggested_icon']['name']
    
    seed = random.randint(1, 10000)
    
    meta = {
        "badge_title": badge_name,
        "subtitle": institution,
        "extra_text": badge_description
    }
    
    config = generate_badge_image_config(
        meta=meta,
        seed=seed,
        suggested_icon=suggested_icon
    )
    
    return {
        "layout_type": "icon_based",
        "config": config,
        "suggested_icon": suggested_icon,
        "seed_used": seed
    }

