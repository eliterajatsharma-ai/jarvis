"""
J.A.R.V.I.S. Production Server Launcher.
Starts the FastAPI backend, 6-service synthetic simulator, WebSocket hub,
and serves the Iron Man HUD dashboard on http://localhost:8000.
"""

import uvicorn
import sys

def main():
    print("=" * 70)
    print("  J.A.R.V.I.S. -- Incident Intelligence Command Center")
    print("  Justified Analysis, Reasoning & Visualization of Incident Systems")
    print("=" * 70)
    print("  -> Dashboard HUD:   http://localhost:8000")
    print("  -> Interactive API: http://localhost:8000/docs")
    print("  -> Live WebSockets: ws://localhost:8000/ws/live")
    print("=" * 70)
    
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=False)

if __name__ == "__main__":
    main()
