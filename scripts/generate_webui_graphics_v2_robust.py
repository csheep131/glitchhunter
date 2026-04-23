#!/usr/bin/env python3
"""
GLITCHHUNTER GRAPHICS GENERATOR V2.1 - ROBUST
Generiert alle Grafiken für die GlitchHunter Web-UI
Mit besserer Fehlerbehandlung und Retry-Logik
"""

import sys
import time
import requests
import subprocess
from pathlib import Path
import json

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
# NAVIGATION ICONS V2 (128x128px)
# ═══════════════════════════════════════════════════════════════════════════

NAV_ICONS = {
    "dashboard": {
        "prompt": "flat geometric dashboard icon, symmetrical control panel design, metallic gold surface, neon green data streams, holographic screens, 1:1 icon, clean minimal, high detail",
        "size": 128, "steps": 25, "folder": "nav"
    },
    "problem": {
        "prompt": "flat geometric brain icon, symmetrical neural network design, metallic gold cranium, neon green synaptic connections, glowing nodes, 1:1 icon, clean minimal, high detail",
        "size": 128, "steps": 25, "folder": "nav"
    },
    "refactor": {
        "prompt": "flat geometric hammer and wrench crossing icon, symmetrical design, metallic gold tools, neon green glowing edges, crossed at 45 degrees, 1:1 icon, clean minimal, high detail",
        "size": 128, "steps": 25, "folder": "nav"
    },
    "reports": {
        "prompt": "flat geometric document icon, symmetrical scroll design, metallic gold parchment, neon green text lines, unfurling scroll, 1:1 icon, clean minimal, high detail",
        "size": 128, "steps": 25, "folder": "nav"
    },
    "history": {
        "prompt": "flat geometric hourglass icon, symmetrical design, metallic gold frame, neon green flowing sand, time tracking symbol, 1:1 icon, clean minimal, high detail",
        "size": 128, "steps": 25, "folder": "nav"
    },
    "stacks": {
        "prompt": "flat geometric server rack icon, symmetrical stacked design, metallic gold servers, neon green status lights, vertical stack, 1:1 icon, clean minimal, high detail",
        "size": 128, "steps": 25, "folder": "nav"
    },
    "models": {
        "prompt": "flat geometric robot head icon, symmetrical android portrait, metallic gold chassis, neon green glowing eyes, neural network patterns, 1:1 icon, clean minimal, high detail",
        "size": 128, "steps": 25, "folder": "nav"
    },
    "testing": {
        "prompt": "flat geometric test tube icon, symmetrical laboratory glassware, metallic gold beaker, neon green liquid, bubbling reaction, 1:1 icon, clean minimal, high detail",
        "size": 128, "steps": 25, "folder": "nav"
    },
    "hardware": {
        "prompt": "flat geometric GPU icon, symmetrical circuit board design, metallic gold PCB, neon green traces, graphics card layout, 1:1 icon, clean minimal, high detail",
        "size": 128, "steps": 25, "folder": "nav"
    },
    "settings": {
        "prompt": "flat geometric gear icon, symmetrical cog wheel design, metallic gold teeth, neon green center hub, precision engineering, 1:1 icon, clean minimal, high detail",
        "size": 128, "steps": 25, "folder": "nav"
    },
}

# ═══════════════════════════════════════════════════════════════════════════
# STATUS ICONS V2 (64x64px)
# ═══════════════════════════════════════════════════════════════════════════

STATUS_ICONS = {
    "online": {
        "prompt": "flat geometric status indicator dot, glowing neon green circle, online status, pulsing light effect, 1:1 icon, minimal design",
        "size": 64, "steps": 15, "folder": "status"
    },
    "offline": {
        "prompt": "flat geometric status indicator dot, dim gray circle, offline status, dark minimal, 1:1 icon, minimal design",
        "size": 64, "steps": 15, "folder": "status"
    },
    "error": {
        "prompt": "flat geometric status indicator dot, glowing red circle, error status, warning light, 1:1 icon, minimal design",
        "size": 64, "steps": 15, "folder": "status"
    },
    "warning": {
        "prompt": "flat geometric status indicator dot, glowing orange circle, warning status, caution light, 1:1 icon, minimal design",
        "size": 64, "steps": 15, "folder": "status"
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
        "12": {"class_type": "SaveImage", "inputs": {"filename_prefix": "GlitchHunter_V2", "images": ["11", 0]}}
    }

# ═══════════════════════════════════════════════════════════════════════════
# FUNKTIONEN MIT FEHLERBEHANDLUNG
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
        cmd = f"ssh {ASGARD_SSH_HOST} 'ls -t {ASGARD_OUTPUT_DIR}/GlitchHunter_V2_*.png 2>/dev/null | head -1'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception as e:
        print(f"   ⚠️  SSH Error: {e}")
    return None

def download_image_with_retry(remote_path, local_path, max_retries=3):
    """Download mit Retry-Logik"""
    for attempt in range(max_retries):
        try:
            cmd = f"scp {ASGARD_SSH_HOST}:{remote_path} {local_path}"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
            if result.returncode == 0 and local_path.exists():
                return True
            print(f"   ⚠️  SCP Versuch {attempt + 1} fehlgeschlagen: {result.stderr.strip()}")
        except Exception as e:
            print(f"   ⚠️  Download Versuch {attempt + 1} fehlgeschlagen: {e}")
        
        if attempt < max_retries - 1:
            time.sleep(5)  # 5 Sekunden warten vor Retry
    
    return False

def generate_image(name, config):
    width = config.get("size", 128)
    height = config.get("size", 128)
    folder = config.get("folder", "nav")
    
    print(f"\n{'─' * 70}")
    print(f"🎨 {name.upper()} → {folder}/{name}.png")
    print(f"   {width}×{height}px | Steps: {config['steps']}")
    print(f"   {config.get('description', '')}")
    print(f"   Prompt: {config['prompt'][:70]}...")

    prev_image = get_latest_remote_image()
    workflow = create_flux_workflow(config['prompt'], width, height, config['steps'])

    try:
        # Job senden
        resp = requests.post(f"{COMFYUI_URL}/prompt", json={"prompt": workflow}, timeout=15)
        if resp.status_code != 200:
            print(f"   ❌ Senden: {resp.status_code}")
            return False

        prompt_id = resp.json().get('prompt_id')
        print(f"   ✅ Job: {prompt_id}")

        # Warten
        estimated_time = config['steps'] * 1.5 + 5
        print(f"   ⏳ Warte ~{estimated_time}s...")
        time.sleep(estimated_time)

        # Bild suchen und downloaden
        print(f"   🔍 Suche generiertes Bild...")
        for attempt in range(8):  # 8 Versuche × 5s = 40s maximal
            time.sleep(5)
            new_image = get_latest_remote_image()
            if new_image and new_image != prev_image:
                print(f"   📁 Gefunden: {new_image}")
                
                # Localer Pfad
                local_path = OUTPUT_DIR / folder / f"{name}.png"
                local_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Download mit Retry
                if download_image_with_retry(new_image, local_path):
                    print(f"   ✅ Gespeichert: {local_path} ({local_path.stat().st_size} bytes)")
                    return True
                else:
                    print(f"   ❌ Download fehlgeschlagen")
                    return False
            
            print(f"   ⏳ Versuch {attempt + 1}/8...")

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
    print("║" + "  🐛  GLITCHHUNTER GRAPHICS GENERATOR V2.1".center(68) + "║")
    print("║" + "  Robust Version mit Retry-Logik".center(68) + "║")
    print("╚" + "═" * 68 + "╝")

    if not check_comfyui_connection():
        print("\n❌ Asgard nicht erreichbar!")
        return False

    print("✅ Asgard verbunden!")

    # Alle Grafiken kombinieren
    ALL_GRAPHICS = {}
    ALL_GRAPHICS.update(NAV_ICONS)
    ALL_GRAPHICS.update(STATUS_ICONS)

    print(f"\n📊 {len(ALL_GRAPHICS)} Grafiken werden generiert:")
    print(f"   - {len(NAV_ICONS)} Navigation Icons (128×128px)")
    print(f"   - {len(STATUS_ICONS)} Status Icons (64×64px)")

    # Ordner erstellen
    for name, config in ALL_GRAPHICS.items():
        folder = config.get("folder", "nav")
        (OUTPUT_DIR / folder).mkdir(parents=True, exist_ok=True)

    print(f"\n📁 Ordner-Struktur:")
    for name, config in ALL_GRAPHICS.items():
        folder = config.get("folder", "nav")
        print(f"   - {OUTPUT_DIR / folder}")

    # Auto-start
    print("\n⚠️  Starte automatisch...")

    stats = generate_batch(list(ALL_GRAPHICS.items()), delay=2.0)

    print("\n" + "=" * 70)
    print(f"ABGESCHLOSSEN: {stats['success']}/{stats['total']} erfolgreich")
    print(f"Quote: {stats['success']/stats['total']*100:.1f}%")
    print("=" * 70)

    return stats["failed"] == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
