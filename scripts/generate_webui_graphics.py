#!/usr/bin/env python3
"""
GLITCHHUNTER GRAPHICS GENERATOR V1.0
Generiert alle Grafiken für die GlitchHunter Web-UI
Nordic/Cyber-Stil in Sand/Gold/Grün (GlitchHunter Farben)
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
# NAVIGATION ICONS (10 Seiten)
# ═══════════════════════════════════════════════════════════════════════════

NAV_ICONS = {
    # Haupt-Dashboard
    "icon_dashboard": {
        "prompt": "cyberpunk dashboard control center, holographic display with multiple screens showing code analysis graphs, sand colored interface with neon green accents, futuristic command center, 1:1 icon, nordic cyber style",
        "width": 64, "height": 64, "steps": 20,
        "filename": "icon_dashboard.png",
        "description": "Dashboard - Hauptübersicht"
    },

    # Problemlöser
    "icon_problem": {
        "prompt": "cyberpunk brain with glowing neural networks, sand colored brain with neon green synapses, problem solving symbol, lightbulb made of circuits, 1:1 icon, nordic cyber style",
        "width": 64, "height": 64, "steps": 20,
        "filename": "icon_problem.png",
        "description": "Problemlöser - KI-Analyse"
    },

    # Refactoring
    "icon_refactor": {
        "prompt": "cyberpunk hammer and chisel crossing, golden tools with neon green glow, code refactoring symbol, geometric patterns, 1:1 icon, nordic cyber style",
        "width": 64, "height": 64, "steps": 20,
        "filename": "icon_refactor.png",
        "description": "Refactoring - Code verbessern"
    },

    # Reports
    "icon_reports": {
        "prompt": "cyberpunk scroll unfurling, ancient runic tablet with holographic display, sand colored parchment with neon green text, data visualization, 1:1 icon, nordic cyber style",
        "width": 64, "height": 64, "steps": 20,
        "filename": "icon_reports.png",
        "description": "Reports - Berichte"
    },

    # History
    "icon_history": {
        "prompt": "cyberpunk hourglass with digital sand flowing, golden hourglass with neon green glow, time tracking symbol, ancient meets future, 1:1 icon, nordic cyber style",
        "width": 64, "height": 64, "steps": 20,
        "filename": "icon_history.png",
        "description": "History - Verlauf"
    },

    # Stacks
    "icon_stacks": {
        "prompt": "cyberpunk server racks stacked vertically, golden servers with neon green status lights, hardware stack symbol, data center aesthetic, 1:1 icon, nordic cyber style",
        "width": 64, "height": 64, "steps": 20,
        "filename": "icon_stacks.png",
        "description": "Stacks - Hardware-Konfiguration"
    },

    # Models
    "icon_models": {
        "prompt": "cyberpunk robot head portrait, golden android with neon green eyes, AI model symbol, neural network patterns on face, 1:1 icon, nordic cyber style",
        "width": 64, "height": 64, "steps": 20,
        "filename": "icon_models.png",
        "description": "Models - KI-Modelle"
    },

    # Testing
    "icon_testing": {
        "prompt": "cyberpunk test tube and beaker, golden laboratory glassware with neon green liquid, testing symbol, scientific aesthetic, 1:1 icon, nordic cyber style",
        "width": 64, "height": 64, "steps": 20,
        "filename": "icon_testing.png",
        "description": "Testing - Stack-Tests"
    },

    # Hardware
    "icon_hardware": {
        "prompt": "cyberpunk gpu graphics card, golden circuit board with neon green accents, hardware monitoring symbol, tech aesthetic, 1:1 icon, nordic cyber style",
        "width": 64, "height": 64, "steps": 20,
        "filename": "icon_hardware.png",
        "description": "Hardware - Ressourcen"
    },

    # Settings
    "icon_settings": {
        "prompt": "cyberpunk gear cog wheel, golden mechanical gear with neon green teeth, settings symbol, precision engineering, 1:1 icon, nordic cyber style",
        "width": 64, "height": 64, "steps": 20,
        "filename": "icon_settings.png",
        "description": "Settings - Einstellungen"
    },
}

# ═══════════════════════════════════════════════════════════════════════════
# STATUS INDICATORS
# ═══════════════════════════════════════════════════════════════════════════

STATUS_ICONS = {
    "status_online": {
        "prompt": "cyberpunk status indicator dot, glowing neon green circle, online status, pulsing light, 1:1 icon, minimal design",
        "width": 32, "height": 32, "steps": 15,
        "filename": "status_online.png",
        "description": "Status - Online"
    },

    "status_offline": {
        "prompt": "cyberpunk status indicator dot, dim gray circle, offline status, dark minimal, 1:1 icon, minimal design",
        "width": 32, "height": 32, "steps": 15,
        "filename": "status_offline.png",
        "description": "Status - Offline"
    },

    "status_error": {
        "prompt": "cyberpunk status indicator dot, glowing red circle, error status, warning light, 1:1 icon, minimal design",
        "width": 32, "height": 32, "steps": 15,
        "filename": "status_error.png",
        "description": "Status - Error"
    },

    "status_warning": {
        "prompt": "cyberpunk status indicator dot, glowing orange circle, warning status, caution light, 1:1 icon, minimal design",
        "width": 32, "height": 32, "steps": 15,
        "filename": "status_warning.png",
        "description": "Status - Warning"
    },
}

# ═══════════════════════════════════════════════════════════════════════════
# FEATURE GRAFICS (für Cards/Sections)
# ═══════════════════════════════════════════════════════════════════════════

FEATURE_GRAPHICS = {
    # GlitchHunter Logo Variant
    "logo_small": {
        "prompt": "cyberpunk glitch hunter logo, stylized bug insect made of circuits, golden beetle with neon green eyes, geometric logo design, clean minimal, 1:1 logo, nordic cyber style",
        "width": 128, "height": 128, "steps": 25,
        "filename": "logo_small.png",
        "description": "Logo - Klein"
    },

    # Analysis Complete
    "analysis_complete": {
        "prompt": "cyberpunk checkmark badge, golden shield with neon green check, analysis complete symbol, success indicator, 1:1 icon, nordic cyber style",
        "width": 96, "height": 96, "steps": 20,
        "filename": "analysis_complete.png",
        "description": "Analyse abgeschlossen"
    },

    # Analysis Running
    "analysis_running": {
        "prompt": "cyberpunk loading spinner, golden circular progress indicator with neon green glow, analysis in progress, spinning arcs, 1:1 icon, nordic cyber style",
        "width": 96, "height": 96, "steps": 20,
        "filename": "analysis_running.png",
        "description": "Analyse läuft"
    },

    # Bug Found
    "bug_found": {
        "prompt": "cyberpunk bug alert symbol, golden warning triangle with neon green bug icon, code issue detected, alert badge, 1:1 icon, nordic cyber style",
        "width": 64, "height": 64, "steps": 20,
        "filename": "bug_found.png",
        "description": "Bug gefunden"
    },

    # Security Shield
    "security_shield": {
        "prompt": "cyberpunk security shield, golden protective barrier with neon green runic patterns, defense symbol, cybersecurity, 1:1 icon, nordic cyber style",
        "width": 64, "height": 64, "steps": 20,
        "filename": "security_shield.png",
        "description": "Security Shield"
    },

    # Performance Speed
    "performance_speed": {
        "prompt": "cyberpunk speedometer gauge, golden dial with neon green needle in high zone, performance boost symbol, velocity, 1:1 icon, nordic cyber style",
        "width": 64, "height": 64, "steps": 20,
        "filename": "performance_speed.png",
        "description": "Performance Boost"
    },

    # AI Brain
    "ai_brain": {
        "prompt": "cyberpunk artificial intelligence brain, golden neural network with glowing neon green connections, machine learning symbol, deep learning, 1:1 icon, nordic cyber style",
        "width": 64, "height": 64, "steps": 20,
        "filename": "ai_brain.png",
        "description": "AI/ML Symbol"
    },

    # Code File
    "code_file": {
        "prompt": "cyberpunk code file document, golden scroll with neon green code lines, source code symbol, programming, 1:1 icon, nordic cyber style",
        "width": 64, "height": 64, "steps": 20,
        "filename": "code_file.png",
        "description": "Code File"
    },

    # Database
    "database": {
        "prompt": "cyberpunk database cylinder, golden storage unit with neon green data streams, database symbol, data storage, 1:1 icon, nordic cyber style",
        "width": 64, "height": 64, "steps": 20,
        "filename": "database.png",
        "description": "Database"
    },

    # API Connection
    "api_connection": {
        "prompt": "cyberpunk network connection nodes, golden nodes connected by neon green lines, API symbol, distributed network, 1:1 icon, nordic cyber style",
        "width": 64, "height": 64, "steps": 20,
        "filename": "api_connection.png",
        "description": "API Connection"
    },
}

# ═══════════════════════════════════════════════════════════════════════════
# DECORATIVE GRAPHICS (zum Aufhübschen)
# ═══════════════════════════════════════════════════════════════════════════

DECORATIVE_GRAPHICS = {
    # Yggdrasil Tree (Background Element)
    "yggdrasil_small": {
        "prompt": "cyberpunk yggdrasil world tree, golden tree with neon green leaves and roots, nine realms connected by branches, nordic tree of life, wide landscape, nordic cyber style",
        "width": 512, "height": 256, "steps": 30,
        "filename": "yggdrasil_small.png",
        "description": "Yggdrasil - Deko"
    },

    # Bifrost Bridge (Divider)
    "bifrost_divider": {
        "prompt": "cyberpunk bifrost rainbow bridge, golden bridge with neon green energy arcs, asgard connector, horizontal divider, nordic cyber style",
        "width": 800, "height": 100, "steps": 25,
        "filename": "bifrost_divider.png",
        "description": "Bifrost - Divider"
    },

    # Runes Pattern (Background)
    "runes_pattern": {
        "prompt": "cyberpunk runic alphabet pattern, golden ancient runes with neon green glow, repeating background pattern, nordic symbols, seamless texture, nordic cyber style",
        "width": 512, "height": 512, "steps": 25,
        "filename": "runes_pattern.png",
        "description": "Runes - Pattern"
    },

    # Circuit Board (Background)
    "circuit_board": {
        "prompt": "cyberpunk circuit board texture, golden PCB with neon green traces, tech background, electronic patterns, seamless texture, nordic cyber style",
        "width": 512, "height": 512, "steps": 25,
        "filename": "circuit_board.png",
        "description": "Circuit - Background"
    },

    # Loading Spinner
    "loading_spinner": {
        "prompt": "cyberpunk loading animation frame, golden rotating circle with neon green segments, progress indicator, spinner animation frame, 1:1 icon, nordic cyber style",
        "width": 64, "height": 64, "steps": 20,
        "filename": "loading_spinner.png",
        "description": "Loading Spinner"
    },

    # Empty State Illustration
    "empty_state": {
        "prompt": "cyberpunk empty box container, golden open box with neon green interior, empty state illustration, nothing here, minimal, 1:1 illustration, nordic cyber style",
        "width": 128, "height": 128, "steps": 20,
        "filename": "empty_state.png",
        "description": "Empty State"
    },

    # Success Celebration
    "success_celebration": {
        "prompt": "cyberpunk success confetti explosion, golden particles with neon green sparkles, celebration effect, achievement unlocked, 1:1 illustration, nordic cyber style",
        "width": 128, "height": 128, "steps": 20,
        "filename": "success_celebration.png",
        "description": "Success Celebration"
    },

    # Error Alert
    "error_alert": {
        "prompt": "cyberpunk error warning symbol, golden exclamation mark in triangle with red neon glow, alert badge, warning sign, 1:1 icon, nordic cyber style",
        "width": 64, "height": 64, "steps": 20,
        "filename": "error_alert.png",
        "description": "Error Alert"
    },

    # Info Icon
    "info_icon": {
        "prompt": "cyberpunk information symbol, golden letter i in circle with neon blue glow, help icon, information badge, 1:1 icon, nordic cyber style",
        "width": 64, "height": 64, "steps": 20,
        "filename": "info_icon.png",
        "description": "Info Icon"
    },

    # External Link
    "external_link": {
        "prompt": "cyberpunk external link arrow, golden arrow pointing up-right with neon green glow, new tab symbol, hyperlink icon, 1:1 icon, nordic cyber style",
        "width": 48, "height": 48, "steps": 20,
        "filename": "external_link.png",
        "description": "External Link"
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
