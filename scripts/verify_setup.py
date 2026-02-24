#!/usr/bin/env python3
"""
Verification script for the architectural improvements.
Run this after applying all migrations and starting the services.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def check_imports():
    """Verify all new modules can be imported."""
    print("Checking imports...")
    
    try:
        from app.core.logging_config import get_logger
        print("✓ Logging config")
    except Exception as e:
        print(f"✗ Logging config: {e}")
        return False
    
    try:
        from app.core.rate_limiter import limiter
        print("✓ Rate limiter")
    except Exception as e:
        print(f"✗ Rate limiter: {e}")
        return False
    
    try:
        from app.core.metrics import http_requests_total
        print("✓ Metrics")
    except Exception as e:
        print(f"✗ Metrics: {e}")
        return False
    
    try:
        from app.core.celery import celery_app
        print("✓ Celery")
    except Exception as e:
        print(f"✗ Celery: {e}")
        return False
    
    try:
        from app.tasks.automations import run_automation_task
        print("✓ Automation tasks")
    except Exception as e:
        print(f"✗ Automation tasks: {e}")
        return False
    
    return True


def check_database():
    """Verify database connection and migrations."""
    print("\nChecking database...")
    
    try:
        from app.core.database import engine
        from sqlalchemy import text
        
        with engine.connect() as conn:
            # Check campanias has VoIP columns
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'campanias' AND column_name = 'trunk_id'
            """))
            if result.fetchone():
                print("✓ Campanias table has VoIP columns")
            else:
                print("✗ Campanias table missing VoIP columns - run migrations!")
                return False
            
            # Check indexes exist
            result = conn.execute(text("""
                SELECT indexname 
                FROM pg_indexes 
                WHERE tablename = 'leads' AND indexname = 'ix_leads_cuenta_created'
            """))
            if result.fetchone():
                print("✓ Performance indexes created")
            else:
                print("✗ Performance indexes missing - run migrations!")
                return False
        
        return True
    except Exception as e:
        print(f"✗ Database check failed: {e}")
        return False


def check_models():
    """Verify model relationships."""
    print("\nChecking models...")
    
    try:
        from app.models.campaign import Campania
        from app.models.voip import CampaignAgent, CampaignLead
        
        # Check relationships exist
        assert hasattr(Campania, 'campaign_leads'), "Campania missing campaign_leads"
        assert hasattr(Campania, 'campaign_agents'), "Campania missing campaign_agents"
        assert hasattr(Campania, 'trunk'), "Campania missing trunk"
        assert hasattr(CampaignLead, 'campania'), "CampaignLead missing campania"
        assert hasattr(CampaignAgent, 'campania'), "CampaignAgent missing campania"
        
        print("✓ Model relationships correct")
        return True
    except Exception as e:
        print(f"✗ Model check failed: {e}")
        return False


def check_security():
    """Verify security configuration."""
    print("\nChecking security...")
    
    try:
        from app.core.config import settings
        
        # Check CORS origins are not wildcard
        if settings.ALLOWED_ORIGINS == "*" or "*" in settings.ALLOWED_ORIGINS:
            print("✗ CORS still allows wildcard!")
            return False
        
        print("✓ CORS configured")
        
        # Check AUTH_ENABLED is removed
        if hasattr(settings, 'AUTH_ENABLED'):
            print("⚠ AUTH_ENABLED still exists (should be removed)")
        else:
            print("✓ AUTH_ENABLED removed")
        
        return True
    except Exception as e:
        print(f"✗ Security check failed: {e}")
        return False


def main():
    """Run all checks."""
    print("="*60)
    print("Centro de Control - Architecture Verification")
    print("="*60)
    
    results = []
    
    results.append(("Imports", check_imports()))
    results.append(("Database", check_database()))
    results.append(("Models", check_models()))
    results.append(("Security", check_security()))
    
    print("\n" + "="*60)
    print("Results:")
    print("="*60)
    
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{name:20} {status}")
    
    all_passed = all(r[1] for r in results)
    
    if all_passed:
        print("\n🎉 All checks passed! System is ready.")
        return 0
    else:
        print("\n⚠ Some checks failed. Please review and fix issues.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
