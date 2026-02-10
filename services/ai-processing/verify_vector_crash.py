import sys
import os

# Add local directory to path 
sys.path.append(os.getcwd())

from services.vector_service import VectorService

try:
    print("Initializing VectorService with invalid URL...")
    # Use a port that is likely closed/filtered
    vs = VectorService(qdrant_url="http://localhost:12345", openai_api_key="fake")
    print("VectorService initialized successfully!")
    
    import asyncio
    async def test_embed():
        try:
             await vs.embed_text("test")
        except Exception as e:
             print(f"Embed failed (expected with fake key): {e}")

    # asyncio.run(test_embed())
    
except Exception as e:
    print(f"CRASHED: {e}")
