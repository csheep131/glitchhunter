#!/usr/bin/env python3
"""
Remote Llama Demo for GlitchHunter.

Demonstrates how to use GlitchHunter with a remote Llama server
in the local network.

Usage:
    # Set remote server URL
    export LLAMA_NETWORK_URL="http://192.168.1.100:8080"
    
    # Run demo
    python examples/remote_llama_demo.py

See docs/remote_llama_setup.md for server setup instructions.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add src/ to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def demo_basic_usage():
    """Demonstrate basic remote LLM usage."""
    print("\n" + "=" * 60)
    print("REMOTE LLAMA DEMO - Basic Usage")
    print("=" * 60)
    
    from inference.engine import InferenceEngine
    
    # Get remote URL from environment or use default
    remote_url = os.getenv(
        "LLAMA_NETWORK_URL",
        "http://localhost:8080"
    )
    
    print(f"\nConnecting to: {remote_url}")
    
    # Create engine with remote URL
    engine = InferenceEngine(
        model_name="qwen3.5-9b",
        api_url=remote_url,
        temperature=0.7,
        max_tokens=512,
    )
    
    try:
        # Load remote model
        print("Loading remote model...")
        engine.load_model()
        print("✓ Remote model loaded successfully!")
        
        # Test chat
        print("\nTesting chat completion...")
        response = engine.chat_simple(
            system_prompt="Du bist ein hilfreicher Assistent.",
            user_message="Was ist GlitchHunter?"
        )
        
        print(f"\nResponse:\n{response}")
        
        # Show model info
        info = engine.get_model_info()
        print(f"\nModel Info: {info}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False
        
    finally:
        engine.unload_model()


async def demo_health_check():
    """Demonstrate health check functionality."""
    print("\n" + "=" * 60)
    print("REMOTE LLAMA DEMO - Health Check")
    print("=" * 60)
    
    from inference.engine import InferenceEngine
    
    remote_url = os.getenv(
        "LLAMA_NETWORK_URL",
        "http://localhost:8080"
    )
    
    engine = InferenceEngine(api_url=remote_url)
    
    print(f"\nChecking health of: {remote_url}")
    
    is_healthy = await engine.check_remote_health()
    
    if is_healthy:
        print("✓ Server is healthy!")
    else:
        print("✗ Server is not responding")
    
    return is_healthy


def demo_sync_health_check():
    """Demonstrate synchronous health check."""
    print("\n" + "=" * 60)
    print("REMOTE LLAMA DEMO - Synchronous Health Check")
    print("=" * 60)
    
    from inference.engine import InferenceEngine
    
    remote_url = os.getenv(
        "LLAMA_NETWORK_URL",
        "http://localhost:8080"
    )
    
    engine = InferenceEngine(api_url=remote_url)
    
    print(f"\nChecking health of: {remote_url}")
    
    is_healthy = engine.check_remote_health_sync()
    
    if is_healthy:
        print("✓ Server is healthy!")
    else:
        print("✗ Server is not responding")
    
    return is_healthy


def demo_fallback_strategy():
    """Demonstrate remote-first with local fallback."""
    print("\n" + "=" * 60)
    print("REMOTE LLAMA DEMO - Fallback Strategy")
    print("=" * 60)
    
    from inference.engine import InferenceEngine
    
    remote_url = os.getenv(
        "LLAMA_NETWORK_URL",
        "http://localhost:8080"
    )
    
    # This would be your local model path
    local_model_path = "models/qwen3.5-9b-instruct-q4_k_m.gguf"
    
    engine = InferenceEngine(
        model_name="qwen3.5-9b",
        api_url=remote_url,
    )
    
    print(f"\nAttempting remote-first strategy...")
    print(f"Remote: {remote_url}")
    print(f"Local fallback: {local_model_path}")
    
    success = engine.load_model_with_fallback(
        model_path=local_model_path,
        fallback_to_local=True
    )
    
    if success:
        print("✓ Model loaded successfully!")
        
        if engine._is_remote:
            print("  → Using remote server")
        else:
            print("  → Using local model (fallback)")
    else:
        print("✗ Failed to load model (remote and local)")
    
    return success


def demo_config_integration():
    """Demonstrate integration with config.yaml."""
    print("\n" + "=" * 60)
    print("REMOTE LLAMA DEMO - Config Integration")
    print("=" * 60)
    
    from core.config import Config
    
    try:
        config = Config.load()
        
        if hasattr(config, "remote_inference"):
            remote_config = config.remote_inference
            
            print(f"\nRemote Inference Config:")
            print(f"  Enabled: {remote_config.enabled}")
            print(f"  Base URL: {remote_config.base_url}")
            print(f"  Timeout: {remote_config.timeout}s")
            print(f"  Fallback to local: {remote_config.fallback_to_local}")
            
            if remote_config.is_enabled:
                print(f"\n✓ Remote inference is ENABLED")
                print(f"  Server: {remote_config.get_server_url()}")
                
                # Set environment variable for other components
                os.environ["LLAMA_NETWORK_URL"] = remote_config.get_server_url()
                print(f"  → Set LLAMA_NETWORK_URL environment variable")
            else:
                print(f"\nℹ Remote inference is DISABLED")
                print(f"  → Edit config.yaml to enable")
        else:
            print("\nℹ No remote_inference section in config.yaml")
            print(f"  → See docs/remote_llama_setup.md for setup")
        
        return True
        
    except Exception as e:
        print(f"✗ Error loading config: {e}")
        return False


def demo_state_machine_with_remote():
    """Demonstrate state machine with remote LLM."""
    print("\n" + "=" * 60)
    print("REMOTE LLAMA DEMO - State Machine Integration")
    print("=" * 60)
    
    from agent.state_machine import GlitchHunterWorkflow
    from core.config import Config
    
    remote_url = os.getenv(
        "LLAMA_NETWORK_URL",
        "http://localhost:8080"
    )
    
    print(f"\nInitializing state machine with remote LLM...")
    print(f"Remote URL: {remote_url}")
    
    try:
        config = Config.load()
        
        # Create workflow with remote URL
        workflow = GlitchHunterWorkflow(
            config=config,
            api_url=remote_url,
        )
        
        print("✓ State machine initialized successfully!")
        print(f"  → Will use remote LLM for analysis and verification")
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def main():
    """Run all demos."""
    print("\n" + "=" * 60)
    print("GLITCHHUNTER REMOTE LLAMA DEMO")
    print("=" * 60)
    print("\nThis demo shows how to use GlitchHunter with a remote")
    print("Llama server in your local network.")
    print("\nSet LLAMA_NETWORK_URL environment variable:")
    print("  export LLAMA_NETWORK_URL=\"http://192.168.1.100:8080\"")
    print("\nSee docs/remote_llama_setup.md for server setup.")
    
    # Run demos
    results = {}
    
    # 1. Config Integration
    results["config"] = demo_config_integration()
    
    # 2. Basic Usage
    results["basic"] = demo_basic_usage()
    
    # 3. Health Check (Sync)
    results["health_sync"] = demo_sync_health_check()
    
    # 4. Health Check (Async)
    print("\n\nRunning async health check...")
    results["health_async"] = asyncio.run(demo_health_check())
    
    # 5. Fallback Strategy
    results["fallback"] = demo_fallback_strategy()
    
    # Summary
    print("\n" + "=" * 60)
    print("DEMO SUMMARY")
    print("=" * 60)
    
    for demo, success in results.items():
        status = "✓" if success else "✗"
        print(f"  {status} {demo}")
    
    all_success = all(results.values())
    
    if all_success:
        print("\n✓ All demos completed successfully!")
    else:
        print("\n✗ Some demos failed. Check output above for details.")
    
    return 0 if all_success else 1


if __name__ == "__main__":
    sys.exit(main())
