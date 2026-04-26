#!/usr/bin/env python3
"""
GLITCHHUNTER GRAPHICS GENERATOR V2.0
Generiert alle Grafiken für die GlitchHunter Web-UI
Clean Nordic/Cyber-Stil in Sand/Gold/Grün — minimalistisch, modern, praktisch
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
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

ASGARD_OUTPUT_DIR = "/home/schaf/outputs/image"
ASGARD_SSH_HOST = "asgard"

MODELS = {
    "unet": "flux-2-klein-base-9b-fp8.safetensors",
    "qwen": "qwen_3_8b_fp8mixed.safetensors",
    "vae": "full_encoder_small_decoder.safetensors"
}

# ═══════════════════════════════════════════════════════════════════════════
# NAVIGATION ICONS (10 Seiten) — Clean, minimalistisch, 128x128
# ═══════════════════════════════════════════════════════════════════════════

NAV_ICONS = {
    "icon_dashboard": {
        "prompt": "minimalist dashboard icon, clean geometric grid layout with 4 panels, sand gold color with subtle green accent, flat design, transparent background, 128x128, modern UI icon style",
        "width": 128, "height": 128, "steps": 20,
        "filename": "nav/dashboard.png",
        "description": "Dashboard - Hauptübersicht"
    },

    "icon_problem": {
        "prompt": "minimalist brain icon with circuit patterns, sand gold with green glow, clean geometric lines, transparent background, 128x128, modern UI icon style",
        "width": 128, "height": 128, "steps": 20,
        "filename": "nav/problem.png",
        "description": "Problemlöser - KI-Analyse"
    },

    "icon_refactor": {
        "prompt": "minimalist wrench and code brackets icon, sand gold with green accent, clean lines, transparent background, 128x128, modern UI icon style",
        "width": 128, "height": 128, "steps": 20,
        "filename": "nav/refactor.png",
        "description": "Refactoring - Code verbessern"
    },

    "icon_reports": {
        "prompt": "minimalist document with chart icon, sand gold with green data bars, clean flat design, transparent background, 128x128, modern UI icon style",
        "width": 128, "height": 128, "steps": 20,
        "filename": "nav/reports.png",
        "description": "Reports - Berichte"
    },

    "icon_history": {
        "prompt": "minimalist clock with timeline icon, sand gold with green markers, clean geometric design, transparent background, 128x128, modern UI icon style",
        "width": 128, "height": 128, "steps": 20,
        "filename": "nav/history.png",
        "description": "History - Verlauf"
    },

    "icon_stacks": {
        "prompt": "minimalist stacked server icon, sand gold with green status dots, clean geometric cubes, transparent background, 128x128, modern UI icon style",
        "width": 128, "height": 128, "steps": 20,
        "filename": "nav/stacks.png",
        "description": "Stacks - Hardware-Konfiguration"
    },

    "icon_models": {
        "prompt": "minimalist AI robot head icon, sand gold with green eyes, clean geometric design, transparent background, 128x128, modern UI icon style",
        "width": 128, "height": 128, "steps": 20,
        "filename": "nav/models.png",
        "description": "Models - KI-Modelle"
    },

    "icon_testing": {
        "prompt": "minimalist test tube with checkmark icon, sand gold with green liquid, clean laboratory design, transparent background, 128x128, modern UI icon style",
        "width": 128, "height": 128, "steps": 20,
        "filename": "nav/testing.png",
        "description": "Testing - Stack-Tests"
    },

    "icon_hardware": {
        "prompt": "minimalist GPU chip icon, sand gold with green circuit traces, clean tech design, transparent background, 128x128, modern UI icon style",
        "width": 128, "height": 128, "steps": 20,
        "filename": "nav/hardware.png",
        "description": "Hardware - Ressourcen"
    },

    "icon_settings": {
        "prompt": "minimalist gear cog icon, sand gold with clean teeth, precise mechanical design, transparent background, 128x128, modern UI icon style",
        "width": 128, "height": 128, "steps": 20,
        "filename": "nav/settings.png",
        "description": "Settings - Einstellungen"
    },
}

# ═══════════════════════════════════════════════════════════════════════════
# STATUS INDICATORS — Clean, 64x64
# ═══════════════════════════════════════════════════════════════════════════

STATUS_ICONS = {
    "status_online": {
        "prompt": "minimalist green circle status indicator, soft glow, clean dot, transparent background, 64x64",
        "width": 64, "height": 64, "steps": 15,
        "filename": "status/online.png",
        "description": "Status - Online"
    },

    "status_offline": {
        "prompt": "minimalist gray circle status indicator, muted color, clean dot, transparent background, 64x64",
        "width": 64, "height": 64, "steps": 15,
        "filename": "status/offline.png",
        "description": "Status - Offline"
    },

    "status_error": {
        "prompt": "minimalist red circle status indicator, soft glow, clean dot, transparent background, 64x64",
        "width": 64, "height": 64, "steps": 15,
        "filename": "status/error.png",
        "description": "Status - Error"
    },

    "status_warning": {
        "prompt": "minimalist orange circle status indicator, soft glow, clean dot, transparent background, 64x64",
        "width": 64, "height": 64, "steps": 15,
        "filename": "status/warning.png",
        "description": "Status - Warning"
    },
}

# ═══════════════════════════════════════════════════════════════════════════
# FEATURE GRAFICS — Clean, 128x128
# ═══════════════════════════════════════════════════════════════════════════

FEATURE_GRAPHICS = {
    "logo_small": {
        "prompt": "minimalist beetle icon made of clean geometric shapes, sand gold with green eyes, flat design, transparent background, 128x128, modern logo",
        "width": 128, "height": 128, "steps": 25,
        "filename": "logo/logo_small.png",
        "description": "Logo - Klein"
    },

    "analysis_complete": {
        "prompt": "minimalist shield with green checkmark, sand gold border, clean success badge, transparent background, 128x128",
        "width": 128, "height": 128, "steps": 20,
        "filename": "status/analysis_complete.png",
        "description": "Analyse abgeschlossen"
    },

    "analysis_running": {
        "prompt": "minimalist circular progress spinner, sand gold arc with green glow, clean loading indicator, transparent background, 128x128",
        "width": 128, "height": 128, "steps": 20,
        "filename": "status/analysis_running.png",
        "description": "Analyse läuft"
    },

    "bug_found": {
        "prompt": "minimalist bug icon in warning triangle, sand gold with green accent, clean alert symbol, transparent background, 128x128",
        "width": 128, "height": 128, "steps": 20,
        "filename": "empty_states/bug_found.png",
        "description": "Bug gefunden"
    },

    "security_shield": {
        "prompt": "minimalist security shield icon, sand gold with green runic pattern, clean protection symbol, transparent background, 128x128",
        "width": 128, "height": 128, "steps": 20,
        "filename": "decorative/security_shield.png",
        "description": "Security Shield"
    },

    "performance_speed": {
        "prompt": "minimalist speedometer gauge, sand gold dial with green needle, clean performance symbol, transparent background, 128x128",
        "width": 128, "height": 128, "steps": 20,
        "filename": "decorative/performance_speed.png",
        "description": "Performance Boost"
    },

    "ai_brain": {
        "prompt": "minimalist brain icon with neural network dots, sand gold with green connections, clean AI symbol, transparent background, 128x128",
        "width": 128, "height": 128, "steps": 20,
        "filename": "decorative/ai_brain.png",
        "description": "AI/ML Symbol"
    },

    "code_file": {
        "prompt": "minimalist code file icon with brackets, sand gold with green syntax lines, clean document symbol, transparent background, 128x128",
        "width": 128, "height": 128, "steps": 20,
        "filename": "decorative/code_file.png",
        "description": "Code File"
    },

    "database": {
        "prompt": "minimalist database cylinder icon, sand gold with green data streams, clean storage symbol, transparent background, 128x128",
        "width": 128, "height": 128, "steps": 20,
        "filename": "decorative/database.png",
        "description": "Database"
    },

    "api_connection": {
        "prompt": "minimalist network nodes icon, sand gold nodes with green connections, clean API symbol, transparent background, 128x128",
        "width": 128, "height": 128, "steps": 20,
        "filename": "decorative/api_connection.png",
        "description": "API Connection"
    },
}

# ═══════════════════════════════════════════════════════════════════════════
# DECORATIVE GRAPHICS — Clean, subtle
# ═══════════════════════════════════════════════════════════════════════════

DECORATIVE_GRAPHICS = {
    "loading_spinner": {
        "prompt": "minimalist loading spinner, sand gold rotating arc with green glow, clean circular progress, transparent background, 128x128",
        "width": 128, "height": 128, "steps": 20,
        "filename": "status/loading_spinner.png",
        "description": "Loading Spinner"
    },

    "empty_state": {
        "prompt": "minimalist empty box icon, sand gold open container with green interior, clean empty state illustration, transparent background, 128x128",
        "width": 128, "height": 128, "steps": 20,
        "filename": "empty_states/empty_state.png",
        "description": "Empty State"
    },

    "success_celebration": {
        "prompt": "minimalist success particles, sand gold sparkles with green glow, clean celebration effect, transparent background, 128x128",
        "width": 128, "height": 128, "steps": 20,
        "filename": "status/success_celebration.png",
        "description": "Success Celebration"
    },

    "error_alert": {
        "prompt": "minimalist error exclamation mark in triangle, sand gold with red glow, clean warning symbol, transparent background, 128x128",
        "width": 128, "height": 128, "steps": 20,
        "filename": "empty_states/error_alert.png",
        "description": "Error Alert"
    },

    "info_icon": {
        "prompt": "minimalist information i in circle, sand gold with blue glow, clean help symbol, transparent background, 128x128",
        "width": 128, "height": 128, "steps": 20,
        "filename": "decorative/info_icon.png",
        "description": "Info Icon"
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
        "12": {"class_type": "SaveImage", "inputs": {"filename_prefix": "GlitchHunter_Graphic", "images": ["11", 0]}}
    }

# ═══════════════════════════════════════════════════════════════════════════
# FUNKTIONEN
# ═══════════════════════════════════════════════════════════════════════════

def check_comfyui_connection():
    try:
        resp = requests.get(f"{COMFYUI_URL}/system_stats", timeout=3)
        return resp.status_code == 200
    except Exception as e:
        print(f"   ❌ Verbindung: {e}")
        return False

def get_latest_remote_image():
    try:
        cmd = f"ssh {ASGARD_SSH_HOST} 'ls -t {ASGARD_OUTPUT_DIR}/GlitchHunter_Graphic_*.png 2>/dev/null | head -1'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception as e:
        print(f"   ⚠️  SSH Error: {e}")
    return None

def download_image(remote_path, local_filename):
    try:
        local_path = OUTPUT_DIR / local_filename
        cmd = f"scp {ASGARD_SSH_HOST}:{remote_path} {local_path}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
        if result.returncode == 0 and local_path.exists():
            return True
        print(f"   ❌ SCP: {result.stderr}")
    except Exception as e:
        print(f"   ❌ Download: {e}")
    return False

def generate_image(name, config):
    print(f"\n{'─' * 70}")
    print(f"🎨 {name.upper()} → {config['filename']}")
    print(f"   {config['width']}×{config['height']}px | Steps: {config['steps']}")
    print(f"   {config['description']}")
    print(f"   Prompt: {config['prompt'][:70]}...")

    prev_image = get_latest_remote_image()
    workflow = create_flux_workflow(config['prompt'], config['width'], config['height'], config['steps'])

    try:
        resp = requests.post(f"{COMFYUI_URL}/prompt", json={"prompt": workflow}, timeout=10)
        if resp.status_code != 200:
            print(f"   ❌ Senden: {resp.status_code}")
            return False

        prompt_id = resp.json().get('prompt_id')
        print(f"   ✅ Job: {prompt_id}")

        estimated_time = config['steps'] * 1.5 + 1
        print(f"   ⏳ Warte ~{estimated_time}s...")
        time.sleep(estimated_time)

        print(f"   🔍 Suche generiertes Bild...")
        for attempt in range(5):
            time.sleep(3)
            new_image = get_latest_remote_image()
            if new_image and new_image != prev_image:
                print(f"   📁 Gefunden: {new_image}")
                if download_image(new_image, config['filename']):
                    local_path = OUTPUT_DIR / config['filename']
                    print(f"   ✅ Gespeichert: {local_path} ({local_path.stat().st_size} bytes)")
                    return True
            print(f"   ⏳ Versuch {attempt + 1}/5...")

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
    print("║" + "  🐛  GLITCHHUNTER GRAPHICS GENERATOR V1.0".center(68) + "║")
    print("║" + "  Nordic/Cyber Style - Sand/Gold/Green".center(68) + "║")
    print("╚" + "═" * 68 + "╝")

    if not check_comfyui_connection():
        print("\n❌ Asgard nicht erreichbar!")
        return False

    print("✅ Asgard verbunden!")

    # Alle Grafiken kombinieren
    ALL_GRAPHICS = {}
    ALL_GRAPHICS.update(NAV_ICONS)
    ALL_GRAPHICS.update(STATUS_ICONS)
    ALL_GRAPHICS.update(FEATURE_GRAPHICS)
    ALL_GRAPHICS.update(DECORATIVE_GRAPHICS)

    print(f"\n📊 {len(ALL_GRAPHICS)} Grafiken werden generiert:")
    print(f"   - {len(NAV_ICONS)} Navigation Icons")
    print(f"   - {len(STATUS_ICONS)} Status Indicators")
    print(f"   - {len(FEATURE_GRAPHICS)} Feature Grafiken")
    print(f"   - {len(DECORATIVE_GRAPHICS)} Dekorative Elemente")

    confirm = input("\n⚠️  Starten? (y/n): ").strip().lower()
    if confirm != 'y':
        return False

    stats = generate_batch(list(ALL_GRAPHICS.items()), delay=3.0)

    print("\n" + "=" * 70)
    print(f"ABGESCHLOSSEN: {stats['success']}/{stats['total']} erfolgreich")
    print(f"Quote: {stats['success']/stats['total']*100:.1f}%")
    print(f"Gesamt: {len(list(OUTPUT_DIR.glob('*.png')))} Bilder generiert")
    print("=" * 70)

    return stats["failed"] == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
