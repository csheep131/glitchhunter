#!/usr/bin/env python3
"""
GLITCHHUNTER HERO GRAPHICS GENERATOR
Generiert große, elegante Grafiken für die Web-UI
Sandfarben/Grün GlitchHunter-Stil (kein Nordic/Cyber!)
"""

import sys
import time
import requests
import subprocess
from pathlib import Path

# ═══════════════════════════════════════════════════════════════════════════
# KONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

COMFYUI_URL = "http://asgard:8188"
OUTPUT_DIR = Path("/home/schaf/projects/glitchhunter/ui/web/frontend/assets")
ASGARD_OUTPUT_DIR = "/home/schaf/outputs/image"
ASGARD_SSH_HOST = "asgard"

MODELS = {
    "unet": "flux-2-klein-base-9b-fp8.safetensors",
    "qwen": "qwen_3_8b_fp8mixed.safetensors",
    "vae": "full_encoder_small_decoder.safetensors"
}

# ═══════════════════════════════════════════════════════════════════════════
# GLITCHHUNTER FARBPALETTE
# ═══════════════════════════════════════════════════════════════════════════

DESIGN = {
    "sand": "#d4c4a8",
    "gold": "#c9b896",
    "green": "#10b981",
    "dark": "#1f2937",
    "light": "#f9fafb",
}

# ═══════════════════════════════════════════════════════════════════════════
# HERO BANNER (1200x400px) - Großes Dashboard-Hintergrundbild
# ═══════════════════════════════════════════════════════════════════════════

HERO_BANNER = {
    "prompt": f"wide panoramic dashboard interface, sand colored background (#d4c4a8), "
              f"golden circuit board patterns (#c9b896), "
              f"neon green data streams (#10b981), "
              f"multiple holographic monitoring screens floating in space, "
              f"glitch effect subtle, "
              f"modern security operations center, "
              f"wide angle 16:9, cinematic lighting, "
              f"high detail, professional UI design",
    "width": 1200, "height": 400, "steps": 35,
    "filename": "hero_banner.png",
    "description": "Hero Banner - 1200x400px Dashboard-Hintergrund"
}

# ═══════════════════════════════════════════════════════════════════════════
# HERO CHARACTER (800x600px) - GlitchHunter als große Figur
# ═══════════════════════════════════════════════════════════════════════════

HERO_CHARACTER = {
    "prompt": f"cyberpunk glitch hunter character, sand colored armor (#d4c4a8), "
              f"golden circuit patterns (#c9b896), "
              f"neon green glowing eyes (#10b981), "
              f"holding a digital bug detector device, "
              f"standing in front of a massive server room, "
              f"dramatic lighting, "
              f"1:1 portrait, "
              f"high detail, professional character design",
    "width": 800, "height": 600, "steps": 40,
    "filename": "hero_character.png",
    "description": "Hero Character - GlitchHunter Figur 800x600px"
}

# ═══════════════════════════════════════════════════════════════════════════
# SECTION DIVIDERS (800x100px) - Dekorative Trenner
# ═══════════════════════════════════════════════════════════════════════════

DIVIDERS = {
    "divider_gold": {
        "prompt": f"horizontal decorative divider, golden (#c9b896) geometric pattern, "
                  f"sand colored background (#d4c4a8), "
                  f"subtle circuit board texture, "
                  f"elegant minimal design, "
                  f"800x100px, high detail",
        "width": 800, "height": 100, "steps": 25,
        "filename": "divider_gold.png",
        "description": "Goldener Divider - 800x100px"
    },
    "divider_green": {
        "prompt": f"horizontal decorative divider, neon green (#10b981) glowing lines, "
                  f"sand colored background (#d4c4a8), "
                  f"data stream pattern, "
                  f"800x100px, high detail",
        "width": 800, "height": 100, "steps": 25,
        "filename": "divider_green.png",
        "description": "Grüner Divider - 800x100px"
    },
}

# ═══════════════════════════════════════════════════════════════════════════
# LARGE FEATURE CARDS (512x300px) - Für Feature-Sektionen
# ═══════════════════════════════════════════════════════════════════════════

FEATURE_CARDS = {
    "feature_swarm": {
        "prompt": f"large feature card illustration, multi-agent swarm concept, "
                  f"sand colored background (#d4c4a8), "
                  f"golden (#c9b896) network nodes connecting, "
                  f"neon green (#10b981) data flows between agents, "
                  f"5 distinct agent figures working together, "
                  f"wide format 16:9, "
                  f"high detail, professional illustration",
        "width": 512, "height": 300, "steps": 30,
        "filename": "feature_swarm.png",
        "description": "Feature: Multi-Agent Swarm - 512x300px"
    },
    "feature_ml": {
        "prompt": f"large feature card illustration, machine learning brain, "
                  f"sand colored background (#d4c4a8), "
                  f"golden (#c9b896) neural network, "
                  f"neon green (#10b981) glowing synapses, "
                  f"data visualization elements, "
                  f"wide format 16:9, "
                  f"high detail, professional illustration",
        "width": 512, "height": 300, "steps": 30,
        "filename": "feature_ml.png",
        "description": "Feature: ML Prediction - 512x300px"
    },
    "feature_refactor": {
        "prompt": f"large feature card illustration, code refactoring concept, "
                  f"sand colored background (#d4c4a8), "
                  f"golden (#c9b896) code blocks transforming, "
                  f"neon green (#10b981) checkmarks and arrows, "
                  f"before/after comparison visual, "
                  f"wide format 16:9, "
                  f"high detail, professional illustration",
        "width": 512, "height": 300, "steps": 30,
        "filename": "feature_refactor.png",
        "description": "Feature: Auto-Refactoring - 512x300px"
    },
    "feature_stacks": {
        "prompt": f"large feature card illustration, hardware stack visualization, "
                  f"sand colored background (#d4c4a8), "
                  f"golden (#c9b896) server racks, "
                  f"neon green (#10b981) status indicators, "
                  f"GPU and CPU components visible, "
                  f"wide format 16:9, "
                  f"high detail, professional illustration",
        "width": 512, "height": 300, "steps": 30,
        "filename": "feature_stacks.png",
        "description": "Feature: Stack-Management - 512x300px"
    },
}

# ═══════════════════════════════════════════════════════════════════════════
# FLUX.2 WORKFLOW
# ═══════════════════════════════════════════════════════════════════════════

def create_flux_workflow(prompt, width, height, steps):
    seed = int(time.time() * 1000) % (2**32)
    return {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": MODELS["unet"], "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": MODELS["qwen"], "type": "flux2"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": MODELS["vae"]}},
        "4": {"class_type": "EmptyFlux2LatentImage", "inputs": {"width": width, "height": height, "batch_size": 1}},
        "5": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["2", 0]}},
        "5b": {"class_type": "CLIPTextEncode", "inputs": {"text": "", "clip": ["2", 0]}},
        "6": {"class_type": "Flux2Scheduler", "inputs": {"steps": steps, "width": width, "height": height}},
        "7": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}},
        "8": {"class_type": "RandomNoise", "inputs": {"noise_seed": seed}},
        "9": {"class_type": "CFGGuider", "inputs": {"cfg": 1.0, "model": ["1", 0], "positive": ["5", 0], "negative": ["5b", 0]}},
        "10": {"class_type": "SamplerCustomAdvanced", "inputs": {"noise": ["8", 0], "guider": ["9", 0], "sampler": ["7", 0], "sigmas": ["6", 0], "latent_image": ["4", 0]}},
        "11": {"class_type": "VAEDecode", "inputs": {"samples": ["10", 0], "vae": ["3", 0]}},
        "12": {"class_type": "SaveImage", "inputs": {"filename_prefix": "GlitchHunter_Hero", "images": ["11", 0]}}
    }

# ═══════════════════════════════════════════════════════════════════════════
# FUNKTIONEN
# ═══════════════════════════════════════════════════════════════════════════

def check_comfyui_connection():
    try:
        resp = requests.get(f"{COMFYUI_URL}/system_stats", timeout=5)
        return resp.status_code == 200
    except Exception as e:
        print(f"   ❌ Verbindung: {e}")
        return False

def get_latest_remote_image():
    try:
        cmd = f"ssh {ASGARD_SSH_HOST} 'ls -t {ASGARD_OUTPUT_DIR}/GlitchHunter_Hero_*.png 2>/dev/null | head -1'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception as e:
        print(f"   ⚠️  SSH Error: {e}")
    return None

def download_image(remote_path, local_path):
    try:
        cmd = f"scp {ASGARD_SSH_HOST}:{remote_path} {local_path}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
        if result.returncode == 0 and local_path.exists():
            return True
        print(f"   ❌ SCP: {result.stderr}")
    except Exception as e:
        print(f"   ❌ Download: {e}")
    return False

def generate_image(name, config):
    width = config['width']
    height = config['height']
    
    print(f"\n{'─' * 70}")
    print(f"🎨 {name.upper()} → {config['filename']}")
    print(f"   {width}×{height}px | Steps: {config['steps']}")
    print(f"   {config['description']}")
    print(f"   Prompt: {config['prompt'][:80]}...")

    prev_image = get_latest_remote_image()
    workflow = create_flux_workflow(config['prompt'], width, height, config['steps'])

    try:
        resp = requests.post(f"{COMFYUI_URL}/prompt", json={"prompt": workflow}, timeout=15)
        if resp.status_code != 200:
            print(f"   ❌ Senden: {resp.status_code}")
            return False

        prompt_id = resp.json().get('prompt_id')
        print(f"   ✅ Job: {prompt_id}")

        estimated_time = config['steps'] * 2 + 15
        print(f"   ⏳ Warte ~{estimated_time}s...")
        time.sleep(estimated_time)

        print(f"   🔍 Suche generiertes Bild...")
        for attempt in range(10):
            time.sleep(5)
            new_image = get_latest_remote_image()
            if new_image and new_image != prev_image:
                print(f"   📁 Gefunden: {new_image}")
                
                local_path = OUTPUT_DIR / config['filename']
                local_path.parent.mkdir(parents=True, exist_ok=True)
                
                if download_image(new_image, local_path):
                    print(f"   ✅ Gespeichert: {local_path} ({local_path.stat().st_size} bytes)")
                    return True
            print(f"   ⏳ Versuch {attempt + 1}/10...")

        print(f"   ⚠️  Kein neues Bild gefunden")
        return False

    except Exception as e:
        print(f"   ❌ Fehler: {e}")
        return False

def generate_batch(graphics_list, delay=2.0):
    stats = {"success": 0, "failed": 0, "total": len(graphics_list)}
    for i, (name, config) in enumerate(graphics_list, 1):
        print(f"\n{'=' * 70}")
        print(f"📊 FORTSCHRITT: {i}/{len(graphics_list)} ({i/len(graphics_list)*100:.1f}%)")
        if generate_image(name, config):
            stats["success"] += 1
        else:
            stats["failed"] += 1
        if i < len(graphics_list):
            time.sleep(delay)
    return stats

# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    print("\n" + "╔" + "═" * 68 + "╗")
    print("║" + "  🐛  GLITCHHUNTER HERO GRAPHICS GENERATOR".center(68) + "║")
    print("║" + "  Sandfarben/Grün - Große elegante Grafiken".center(68) + "║")
    print("╚" + "═" * 68 + "╝")

    if not check_comfyui_connection():
        print("\n❌ Asgard nicht erreichbar!")
        return False

    print("✅ Asgard verbunden!")

    # Alle Grafiken kombinieren
    ALL_GRAPHICS = {}
    ALL_GRAPHICS["hero_banner"] = HERO_BANNER
    ALL_GRAPHICS["hero_character"] = HERO_CHARACTER
    ALL_GRAPHICS.update(DIVIDERS)
    ALL_GRAPHICS.update(FEATURE_CARDS)

    print(f"\n📊 {len(ALL_GRAPHICS)} große Grafiken werden generiert:")
    print(f"   - 1 Hero Banner (1200×400px)")
    print(f"   - 1 Hero Character (800×600px)")
    print(f"   - 2 Divider (800×100px)")
    print(f"   - 4 Feature Cards (512×300px)")

    # Auto-start ohne Bestätigung
    print("\n⚠️  Starte automatisch...")

    stats = generate_batch(list(ALL_GRAPHICS.items()), delay=3.0)

    print("\n" + "=" * 70)
    print(f"ABGESCHLOSSEN: {stats['success']}/{stats['total']} erfolgreich")
    print(f"Quote: {stats['success']/stats['total']*100:.1f}%")
    print("=" * 70)

    return stats["failed"] == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
