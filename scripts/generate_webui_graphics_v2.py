#!/usr/bin/env python3
"""
GLITCHHUNTER GRAPHICS GENERATOR V2.0
Generiert alle Grafiken für die GlitchHunter Web-UI v3.0
Nordic Cyber Security Design System - Hochauflösend & Stil-konsistent

Neu in V2:
- 128x128px Navigation Icons (2x für Retina)
- Spezifischere Prompts mit metallischen Texturen & Runen-Details
- Automatische Skalierung auf 256px/512px
- Ordner-Struktur: nav/, status/, decorative/, logo/
- Qualitäts-Check (Unschärfe-Erkennung)
- Batch-Processing mit Fortschritt
"""

import sys
import time
import requests
import subprocess
import json
from pathlib import Path
from datetime import datetime

# ═══════════════════════════════════════════════════════════════════════════
# KONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

COMFYUI_URL = "http://asgard:8188"
BASE_OUTPUT_DIR = Path("/home/schaf/projects/glitchhunter/ui/web/frontend/assets")
BASE_OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

# Ordner-Struktur
FOLDERS = {
    "nav": BASE_OUTPUT_DIR / "nav",
    "status": BASE_OUTPUT_DIR / "status",
    "decorative": BASE_OUTPUT_DIR / "decorative",
    "logo": BASE_OUTPUT_DIR / "logo",
    "empty_states": BASE_OUTPUT_DIR / "empty_states",
}

for folder in FOLDERS.values():
    folder.mkdir(exist_ok=True, parents=True)

ASGARD_OUTPUT_DIR = "/home/schaf/outputs/image"
ASGARD_SSH_HOST = "asgard"

MODELS = {
    "unet": "flux-2-klein-base-9b-fp8.safetensors",
    "qwen": "qwen_3_8b_fp8mixed.safetensors",
    "vae": "full_encoder_small_decoder.safetensors"
}

# Design-Tokens für Prompts
DESIGN = {
    "primary": "#d4c4a8",
    "gold": "#c9b896",
    "accent": "#10b981",
    "dark": "#1f2937",
    "light": "#f9fafb",
    "style": "nordic cyber security, symmetrical geometric forms, metallic textures, neon accents, runic circuit patterns, 3D depth with shadows and gradients"
}

# ═══════════════════════════════════════════════════════════════════════════
# NAVIGATION ICONS V2 (10 Stück, 128x128px)
# ═══════════════════════════════════════════════════════════════════════════

NAV_ICONS_V2 = {
    "dashboard": {
        "prompt": f"flat geometric dashboard icon, symmetrical control panel design, "
                  f"metallic gold gradient background ({DESIGN['gold']} to {DESIGN['primary']}), "
                  f"neon green holographic display screens ({DESIGN['accent']} glow), "
                  f"subtle runic circuit patterns along edges, "
                  f"clean minimal UI icon, transparent background, "
                  f"professional interface asset, high detail, 1:1 aspect ratio",
        "size": 128,
        "steps": 25,
        "folder": "nav",
        "description": "Dashboard - Hauptübersicht mit holografischem Control-Center"
    },

    "problem": {
        "prompt": f"flat geometric brain icon, symmetrical neural network design, "
                  f"metallic gold cranial structure ({DESIGN['gold']} metallic finish), "
                  f"neon green glowing synapses and connections ({DESIGN['accent']}), "
                  f"runic circuit board pattern inside brain, "
                  f"clean minimal UI icon, transparent background, "
                  f"professional interface asset, high detail, 1:1 aspect ratio",
        "size": 128,
        "steps": 25,
        "folder": "nav",
        "description": "Problemlöser - KI-Analyse mit neuronalem Netzwerk"
    },

    "refactor": {
        "prompt": f"flat geometric hammer and wrench crossing icon, symmetrical design, "
                  f"metallic gold tools ({DESIGN['gold']} brushed metal texture), "
                  f"neon green energy glow on tool edges ({DESIGN['accent']}), "
                  f"subtle runic engravings on tool handles, "
                  f"clean minimal UI icon, transparent background, "
                  f"professional interface asset, high detail, 1:1 aspect ratio",
        "size": 128,
        "steps": 25,
        "folder": "nav",
        "description": "Refactoring - Code-Verbesserung mit nordischen Werkzeugen"
    },

    "reports": {
        "prompt": f"flat geometric scroll icon, symmetrical ancient tablet design, "
                  f"metallic gold parchment ({DESIGN['gold']} aged metal), "
                  f"neon green holographic text lines ({DESIGN['accent']}), "
                  f"runic alphabet patterns along scroll edges, "
                  f"clean minimal UI icon, transparent background, "
                  f"professional interface asset, high detail, 1:1 aspect ratio",
        "size": 128,
        "steps": 25,
        "folder": "nav",
        "description": "Reports - Berichte als holografische Runentafel"
    },

    "history": {
        "prompt": f"flat geometric hourglass icon, symmetrical time-tracking design, "
                  f"metallic gold frame ({DESIGN['gold']} polished bronze), "
                  f"neon green flowing digital sand ({DESIGN['accent']}), "
                  f"nordic knotwork patterns on hourglass frame, "
                  f"clean minimal UI icon, transparent background, "
                  f"professional interface asset, high detail, 1:1 aspect ratio",
        "size": 128,
        "steps": 25,
        "folder": "nav",
        "description": "History - Verlauf mit nordischer Sanduhr"
    },

    "stacks": {
        "prompt": f"flat geometric server rack icon, symmetrical stacked design, "
                  f"metallic gold server units ({DESIGN['gold']} brushed steel), "
                  f"neon green status indicator lights ({DESIGN['accent']}), "
                  f"circuit board patterns on server fronts, "
                  f"clean minimal UI icon, transparent background, "
                  f"professional interface asset, high detail, 1:1 aspect ratio",
        "size": 128,
        "steps": 25,
        "folder": "nav",
        "description": "Stacks - Hardware-Konfiguration als Server-Rack"
    },

    "models": {
        "prompt": f"flat geometric robot head icon, symmetrical android portrait, "
                  f"metallic gold faceplate ({DESIGN['gold']} polished metal), "
                  f"neon green glowing eyes ({DESIGN['accent']}), "
                  f"neural network circuit patterns on face, "
                  f"clean minimal UI icon, transparent background, "
                  f"professional interface asset, high detail, 1:1 aspect ratio",
        "size": 128,
        "steps": 25,
        "folder": "nav",
        "description": "Models - KI-Modelle als goldener Android"
    },

    "testing": {
        "prompt": f"flat geometric test tube icon, symmetrical laboratory design, "
                  f"metallic gold glassware holder ({DESIGN['gold']} bronze fixture), "
                  f"neon green glowing liquid inside ({DESIGN['accent']}), "
                  f"runic measurement markings on glass, "
                  f"clean minimal UI icon, transparent background, "
                  f"professional interface asset, high detail, 1:1 aspect ratio",
        "size": 128,
        "steps": 25,
        "folder": "nav",
        "description": "Testing - Stack-Tests mit nordischem Labor"
    },

    "hardware": {
        "prompt": f"flat geometric GPU icon, symmetrical circuit board design, "
                  f"metallic gold PCB substrate ({DESIGN['gold']} gold-plated), "
                  f"neon green circuit traces and chips ({DESIGN['accent']}), "
                  f"nordic geometric patterns on heatsink, "
                  f"clean minimal UI icon, transparent background, "
                  f"professional interface asset, high detail, 1:1 aspect ratio",
        "size": 128,
        "steps": 25,
        "folder": "nav",
        "description": "Hardware - Ressourcen als goldene Grafikkarte"
    },

    "settings": {
        "prompt": f"flat geometric gear icon, symmetrical mechanical design, "
                  f"metallic gold gear body ({DESIGN['gold']} machined metal), "
                  f"neon green teeth highlights ({DESIGN['accent']}), "
                  f"runic precision markings on gear face, "
                  f"clean minimal UI icon, transparent background, "
                  f"professional interface asset, high detail, 1:1 aspect ratio",
        "size": 128,
        "steps": 25,
        "folder": "nav",
        "description": "Settings - Einstellungen mit nordischem Zahnrad"
    },
}

# ═══════════════════════════════════════════════════════════════════════════
# STATUS INDICATORS V2 (4 Stück, 64x64px)
# ═══════════════════════════════════════════════════════════════════════════

STATUS_ICONS_V2 = {
    "online": {
        "prompt": f"flat geometric status dot, symmetrical circular design, "
                  f"neon green glowing circle ({DESIGN['accent']}), "
                  f"subtle outer glow ring, pulsing light effect, "
                  f"clean minimal indicator, transparent background, "
                  f"professional UI asset, high detail, 1:1 aspect ratio",
        "size": 64,
        "steps": 20,
        "folder": "status",
        "description": "Status - Online (leuchtend grün)"
    },

    "offline": {
        "prompt": f"flat geometric status dot, symmetrical circular design, "
                  f"dim gray circle ({DESIGN['dark']}), "
                  f"subtle shadow, no glow, dark minimal, "
                  f"clean minimal indicator, transparent background, "
                  f"professional UI asset, high detail, 1:1 aspect ratio",
        "size": 64,
        "steps": 20,
        "folder": "status",
        "description": "Status - Offline (dunkel grau)"
    },

    "error": {
        "prompt": f"flat geometric status dot, symmetrical circular design, "
                  f"glowing red circle (#ef4444), "
                  f"warning light effect, subtle outer pulse ring, "
                  f"clean minimal indicator, transparent background, "
                  f"professional UI asset, high detail, 1:1 aspect ratio",
        "size": 64,
        "steps": 20,
        "folder": "status",
        "description": "Status - Error (leuchtend rot)"
    },

    "warning": {
        "prompt": f"flat geometric status dot, symmetrical circular design, "
                  f"glowing orange circle (#f59e0b), "
                  f"caution light effect, subtle outer glow, "
                  f"clean minimal indicator, transparent background, "
                  f"professional UI asset, high detail, 1:1 aspect ratio",
        "size": 64,
        "steps": 20,
        "folder": "status",
        "description": "Status - Warning (leuchtend orange)"
    },
}

# ═══════════════════════════════════════════════════════════════════════════
# LOGO VARIANTEN V2 (3 Größen)
# ═══════════════════════════════════════════════════════════════════════════

LOGO_V2 = {
    "logo_256": {
        "prompt": f"flat geometric glitch hunter logo, symmetrical stylized beetle design, "
                  f"metallic gold beetle body ({DESIGN['gold']} polished finish), "
                  f"neon green glowing eyes ({DESIGN['accent']}), "
                  f"circuit board patterns on shell, runic details, "
                  f"professional logo design, transparent background, "
                  f"clean minimal, high detail, 1:1 aspect ratio",
        "size": 256,
        "steps": 30,
        "folder": "logo",
        "description": "Logo - 256x256px Hauptvariante"
    },

    "logo_512": {
        "prompt": f"flat geometric glitch hunter logo, symmetrical stylized beetle design, "
                  f"metallic gold beetle body ({DESIGN['gold']} polished finish), "
                  f"neon green glowing eyes ({DESIGN['accent']}), "
                  f"intricate circuit board patterns on shell, detailed runic engravings, "
                  f"professional logo design, transparent background, "
                  f"clean minimal, ultra high detail, 1:1 aspect ratio",
        "size": 512,
        "steps": 35,
        "folder": "logo",
        "description": "Logo - 512x512px Hochauflösend"
    },

    "logo_favicon": {
        "prompt": f"flat geometric glitch hunter logo simplified, symmetrical beetle icon, "
                  f"metallic gold beetle ({DESIGN['gold']}), "
                  f"neon green eyes ({DESIGN['accent']}), "
                  f"minimal circuit details, "
                  f"favicon design, transparent background, "
                  f"ultra clean minimal, high detail, 1:1 aspect ratio",
        "size": 64,
        "steps": 25,
        "folder": "logo",
        "description": "Logo - 64x64px Favicon"
    },
}

# ═══════════════════════════════════════════════════════════════════════════
# DASHBOARD BANNER V2
# ═══════════════════════════════════════════════════════════════════════════

BANNER_V2 = {
    "yggdrasil_banner": {
        "prompt": f"cyberpunk yggdrasil world tree banner, wide landscape composition, "
                  f"metallic gold tree trunk and branches ({DESIGN['gold']}), "
                  f"neon green glowing leaves and roots ({DESIGN['accent']}), "
                  f"circuit board patterns in bark, runic symbols on branches, "
                  f"nine realms connected, professional banner design, "
                  f"1200x300px, high detail, nordic cyber security style",
        "width": 1200,
        "height": 300,
        "steps": 35,
        "folder": "decorative",
        "description": "Yggdrasil Banner - 1200x300px Dashboard-Hintergrund"
    },

    "bifrost_divider": {
        "prompt": f"cyberpunk bifrost rainbow bridge, horizontal divider composition, "
                  f"metallic gold bridge structure ({DESIGN['gold']}), "
                  f"neon green energy arcs and light beams ({DESIGN['accent']}), "
                  f"runic patterns along bridge, asgard connector motif, "
                  f"professional divider design, "
                  f"800x100px, high detail, nordic cyber security style",
        "width": 800,
        "height": 100,
        "steps": 30,
        "folder": "decorative",
        "description": "Bifrost Divider - 800x100px Sektions-Trenner"
    },
}

# ═══════════════════════════════════════════════════════════════════════════
# EMPTY STATES V2
# ═══════════════════════════════════════════════════════════════════════════

EMPTY_STATES_V2 = {
    "empty_box": {
        "prompt": f"flat geometric empty box illustration, symmetrical open container design, "
                  f"metallic gold box exterior ({DESIGN['gold']}), "
                  f"neon green glowing interior ({DESIGN['accent']}), "
                  f"subtle runic patterns on box sides, "
                  f"empty state metaphor, transparent background, "
                  f"professional illustration, high detail, 1:1 aspect ratio",
        "size": 256,
        "steps": 30,
        "folder": "empty_states",
        "description": "Empty State - Leere Schatulle"
    },

    "empty_search": {
        "prompt": f"flat geometric magnifying glass illustration, symmetrical search icon design, "
                  f"metallic gold frame ({DESIGN['gold']}), "
                  f"neon green lens glow ({DESIGN['accent']}), "
                  f"circuit pattern inside lens, "
                  f"empty search state metaphor, transparent background, "
                  f"professional illustration, high detail, 1:1 aspect ratio",
        "size": 256,
        "steps": 30,
        "folder": "empty_states",
        "description": "Empty State - Leere Suche"
    },

    "empty_data": {
        "prompt": f"flat geometric database illustration, symmetrical empty storage design, "
                  f"metallic gold cylinder ({DESIGN['gold']}), "
                  f"neon green data streams fading out ({DESIGN['accent']}), "
                  f"runic patterns on database surface, "
                  f"empty data state metaphor, transparent background, "
                  f"professional illustration, high detail, 1:1 aspect ratio",
        "size": 256,
        "steps": 30,
        "folder": "empty_states",
        "description": "Empty State - Leere Datenbank"
    },
}

# ═══════════════════════════════════════════════════════════════════════════
# FLUX.2 WORKFLOW V2
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
        "12": {"class_type": "SaveImage", "inputs": {"filename_prefix": "GlitchHunter_Graphic_V2", "images": ["11", 0]}}
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
        cmd = f"ssh {ASGARD_SSH_HOST} 'ls -t {ASGARD_OUTPUT_DIR}/GlitchHunter_Graphic_V2_*.png 2>/dev/null | head -1'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
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

def check_image_quality(local_path):
    """
    Qualitäts-Check: Prüft auf minimale Dateigröße und Unschärfe.
    Returns: (is_valid, reason)
    """
    try:
        file_size = local_path.stat().st_size
        
        # Minimale Dateigröße (unter 5KB = wahrscheinlich zu simpel/unscharf)
        if file_size < 5000:
            return False, f"Datei zu klein ({file_size} bytes) - wahrscheinlich unscharf"
        
        # Mit ImageMagick auf Unschärfe prüfen (falls verfügbar)
        try:
            result = subprocess.run(
                ["identify", "-verbose", str(local_path)],
                capture_output=True, text=True, timeout=10
            )
            if "blur" in result.stdout.lower():
                return False, "Bild erkannt als unscharf"
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass  # ImageMagick nicht verfügbar, überspringen
        
        return True, "OK"
    except Exception as e:
        return False, f"Qualitäts-Check fehlgeschlagen: {e}"

def upscale_image(input_path, output_path, scale=2):
    """
    Skaliert ein Bild mit ImageMagick (falls verfügbar).
    """
    try:
        cmd = [
            "magick", "convert", str(input_path),
            "-resize", f"{scale}00%",
            "-filter", "Lanczos",
            str(output_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0 and output_path.exists():
            return True
        print(f"   ⚠️  Upscaling fehlgeschlagen: {result.stderr}")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print(f"   ⚠️  ImageMagick nicht verfügbar - überspringe Upscaling")
    return False

def generate_image(name, config):
    width = config.get("size", config.get("width", 128))
    height = config.get("size", config.get("height", 128))
    
    print(f"\n{'─' * 70}")
    print(f"🎨 {name.upper()} → {config['folder']}/{name}.png")
    print(f"   {width}×{height}px | Steps: {config['steps']}")
    print(f"   {config['description']}")
    print(f"   Prompt: {config['prompt'][:80]}...")

    prev_image = get_latest_remote_image()
    workflow = create_flux_workflow(config['prompt'], width, height, config['steps'])

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
                
                # Lokaler Pfad im richtigen Ordner
                local_path = FOLDERS[config['folder']] / f"{name}.png"
                
                if download_image(new_image, local_path):
                    # Qualitäts-Check
                    is_valid, reason = check_image_quality(local_path)
                    if is_valid:
                        print(f"   ✅ Qualität: {reason} ({local_path.stat().st_size} bytes)")
                        
                        # Optional: Upscale auf 2x für Retina
                        if config.get("size", 128) >= 128:
                            upscale_path = FOLDERS[config['folder']] / f"{name}@2x.png"
                            print(f"   🔍 Upscale auf 2x...")
                            if upscale_image(local_path, upscale_path, scale=2):
                                print(f"   ✅ Upscaled: {upscale_path}")
                        
                        return True
                    else:
                        print(f"   ❌ Qualität: {reason}")
                        print(f"   🗑️  Lösche schlechtes Bild...")
                        local_path.unlink(missing_ok=True)
                        return False
            print(f"   ⏳ Versuch {attempt + 1}/5...")

        print(f"   ⚠️  Kein neues Bild gefunden")
        return False

    except Exception as e:
        print(f"   ❌ Fehler: {e}")
        return False

def generate_batch(graphics_list, delay=3.0):
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

def print_summary(stats):
    print("\n" + "=" * 70)
    print(f"✅ ABGESCHLOSSEN: {stats['success']}/{stats['total']} erfolgreich")
    print(f"📊 Quote: {stats['success']/stats['total']*100:.1f}%")
    
    # Generierte Dateien zählen
    total_files = sum(len(list(f.glob("*.png"))) for f in FOLDERS.values())
    print(f"📁 Gesamt: {total_files} Bilder in Ordner-Struktur:")
    for folder_name, folder_path in FOLDERS.items():
        count = len(list(folder_path.glob("*.png")))
        if count > 0:
            print(f"   - {folder_name}/: {count} Dateien")
    
    print("=" * 70)

# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    print("\n" + "╔" + "═" * 68 + "╗")
    print("║" + "  🐛  GLITCHHUNTER GRAPHICS GENERATOR V2.0".center(68) + "║")
    print("║" + "  Nordic Cyber Security - Hochauflösend & Stil-konsistent".center(68) + "║")
    print("╚" + "═" * 68 + "╝")

    if not check_comfyui_connection():
        print("\n❌ Asgard nicht erreichbar!")
        return False

    print("✅ Asgard verbunden!")

    # Alle Grafiken kombinieren
    ALL_GRAPHICS = {}
    ALL_GRAPHICS.update(NAV_ICONS_V2)
    ALL_GRAPHICS.update(STATUS_ICONS_V2)
    ALL_GRAPHICS.update(LOGO_V2)
    ALL_GRAPHICS.update(BANNER_V2)
    ALL_GRAPHICS.update(EMPTY_STATES_V2)

    print(f"\n📊 {len(ALL_GRAPHICS)} Grafiken werden generiert:")
    print(f"   - {len(NAV_ICONS_V2)} Navigation Icons (128x128px)")
    print(f"   - {len(STATUS_ICONS_V2)} Status Indicators (64x64px)")
    print(f"   - {len(LOGO_V2)} Logo Varianten (256px/512px/64px)")
    print(f"   - {len(BANNER_V2)} Dashboard Banner (1200x300px/800x100px)")
    print(f"   - {len(EMPTY_STATES_V2)} Empty States (256x256px)")

    print(f"\n📁 Ordner-Struktur:")
    for folder_name, folder_path in FOLDERS.items():
        print(f"   - {folder_path}")

    # Auto-start ohne Bestätigung
    print("\n⚠️  Starte automatisch...")

    stats = generate_batch(list(ALL_GRAPHICS.items()), delay=3.0)
    print_summary(stats)

    return stats["failed"] == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
