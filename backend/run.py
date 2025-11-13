#!/usr/bin/env python3
"""
Smart LMS Backend - Easy Startup Script
Run this file to start the server with proper configuration
"""

import os
import sys
from pathlib import Path


def check_environment():
    """Check if environment is properly set up"""
    print("🔍 Checking environment setup...")
    
    # Check if .env file exists
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ ERROR: .env file not found!")
        print("📝 Please create .env file using .env.example as template")
        print("   Run: cp .env.example .env")
        return False
    
    # Check if virtual environment is activated
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("⚠️  WARNING: Virtual environment not activated!")
        print("   Activate it with:")
        print("   - Windows: venv\\Scripts\\activate")
        print("   - Mac/Linux: source venv/bin/activate")
        response = input("Continue anyway? (y/N): ")
        if response.lower() != 'y':
            return False
    
    # Check critical environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    required_vars = [
        'SECRET_KEY',
        'SUPABASE_URL',
        'SUPABASE_KEY',
        'GEMINI_API_KEY'
    ]
    
    missing = []
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    
    if missing:
        print(f"❌ ERROR: Missing required environment variables:")
        for var in missing:
            print(f"   - {var}")
        print("\n📝 Please update your .env file")
        return False
    
    print("✅ Environment check passed!")
    return True


def check_dependencies():
    """Check if all dependencies are installed"""
    print("\n🔍 Checking dependencies...")
    
    try:
        import fastapi
        import uvicorn
        import supabase
        import google.generativeai
        print("✅ All core dependencies installed!")
        return True
    except ImportError as e:
        print(f"❌ ERROR: Missing dependency: {e}")
        print("\n📦 Install dependencies with:")
        print("   pip install -r requirements.txt")
        return False


def print_banner():
    """Print startup banner"""
    banner = """
╔═══════════════════════════════════════════════════╗
║                                                   ║
║         Smart Learning Management System          ║
║              with AI-Powered Proctoring           ║
║                                                   ║
║                  Backend Server                   ║
║                   Version 1.0.0                   ║
║                                                   ║
╚═══════════════════════════════════════════════════╝
    """
    print(banner)


def print_startup_info():
    """Print startup information"""
    print("\n🚀 Starting server...")
    print("\n📚 Once started, you can access:")
    print("   • API Docs (Swagger): http://localhost:8000/docs")
    print("   • API Docs (ReDoc):   http://localhost:8000/redoc")
    print("   • Health Check:       http://localhost:8000/health")
    print("\n💡 Press CTRL+C to stop the server")
    print("\n" + "="*55 + "\n")


def main():
    """Main startup function"""
    print_banner()
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Print startup info
    print_startup_info()
    
    # Start the server
    try:
        import uvicorn
        from app.config import settings
        
        uvicorn.run(
            "app.main:app",
            host=settings.host,
            port=settings.port,
            reload=settings.debug,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped by user")
    except Exception as e:
        print(f"\n❌ ERROR: Failed to start server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()