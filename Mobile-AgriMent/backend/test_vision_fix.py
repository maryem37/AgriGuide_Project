"""
Quick test to verify the Gemini API configuration
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import get_settings

settings = get_settings()

print("=" * 60)
print("Vision API Configuration Test")
print("=" * 60)
print(f"Provider: {settings.VISION_PROVIDER}")
print(f"Gemini Model: {settings.GEMMA_MODEL}")
print(f"Gemini API URL: {settings.GEMMA_API_URL}")
print(f"Gemini API Key configured: {'Yes' if settings.GEMMA_API_KEY else 'No'}")
print(f"Mistral API Key configured: {'Yes' if settings.MISTRAL_API_KEY else 'No'}")
print("=" * 60)

if settings.VISION_PROVIDER.lower() == "gemma":
    print("\n✓ Using Gemini (Gemma) as vision provider")
    if settings.GEMMA_MODEL == "gemini-3.5-flash":
        print("✓ Model name is correct: gemini-3.5-flash")
    else:
        print(f"✗ Warning: Model name might be incorrect: {settings.GEMMA_MODEL}")
        print("  Expected: gemini-3.5-flash")
else:
    print(f"\n✓ Using {settings.VISION_PROVIDER} as vision provider")

print("\nTo test with an actual image, restart the backend:")
print("  cd C:\\Users\\azizb\\Downloads\\Mobile")
print("  .\\restart-backend.bat")
