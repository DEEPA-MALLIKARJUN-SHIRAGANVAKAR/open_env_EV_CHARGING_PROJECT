#!/usr/bin/env python3
"""
HuggingFace Spaces compatible app entry point for EV Charging Scheduler.
Provides a Gradio interface for interactive testing and evaluation.
"""

import os
import sys


try:
    from ui import demo
    
    # Export demo for HuggingFace Spaces
    # HF Spaces will look for the 'demo' object and launch it automatically
    if __name__ == "__main__":
        # Launch locally if script is run directly
        demo.launch(
            show_error=True,
            server_name="0.0.0.0",  # Required for HF Spaces
            server_port=7860,        # Standard for HF Spaces
            share=False
        )
        
except ImportError as e:
    print(f"Error: Failed to import UI: {e}")
    print("Make sure gradio and ev_charging_env are properly installed.")
    sys.exit(1)
except Exception as e:
    print(f"Error: Failed to launch UI: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
