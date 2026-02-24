#!/usr/bin/env python3
"""
Security audit script for multi-tenant endpoints.
Scans all endpoints and identifies potential security issues.
"""
import ast
import os
import sys
from pathlib import Path


def find_endpoints_without_tenant_check(directory: str) -> list:
    """Find API endpoint files that might be missing tenant checks."""
    issues = []
    
    api_dir = Path(directory)
    for file_path in api_dir.rglob("*.py"):
        if file_path.name.startswith("test_"):
            continue
            
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Check for queries without cuenta_id filter
        if '.query(' in content:
            lines = content.split('\n')
            for i, line in enumerate(lines, 1):
                # Look for .filter() calls
                if '.filter(' in line and '.first()' in line or '.all()' in line:
                    # Check if it filters by cuenta_id
                    if 'cuenta_id' not in line and 'id ==' in line:
                        issues.append({
                            'file': str(file_path),
                            'line': i,
                            'code': line.strip(),
                            'issue': 'Query filters by ID without cuenta_id verification'
                        })
    
    return issues


def main():
    """Run security audit."""
    print("=" * 70)
    print("SECURITY AUDIT - Multi-Tenant Isolation Check")
    print("=" * 70)
    
    # Scan endpoints
    endpoints_dir = "app/api/v1/endpoints"
    
    if not os.path.exists(endpoints_dir):
        print(f"❌ Directory not found: {endpoints_dir}")
        sys.exit(1)
    
    print(f"\nScanning: {endpoints_dir}")
    print("-" * 70)
    
    issues = find_endpoints_without_tenant_check(endpoints_dir)
    
    if not issues:
        print("✅ No obvious issues found (basic check)")
    else:
        print(f"⚠️  Found {len(issues)} potential issues:\n")
        
        for issue in issues[:20]:  # Show first 20
            print(f"File: {issue['file']}")
            print(f"Line {issue['line']}: {issue['code'][:80]}")
            print(f"Issue: {issue['issue']}")
            print("-" * 70)
        
        if len(issues) > 20:
            print(f"... and {len(issues) - 20} more issues")
    
    print("\n" + "=" * 70)
    print("RECOMMENDATIONS:")
    print("=" * 70)
    print("""
1. All endpoints accessing resources by ID should verify cuenta_id:
   
   BEFORE (insecure):
       lead = db.query(Lead).filter(Lead.id == lead_id).first()
   
   AFTER (secure):
       lead = db.query(Lead).filter(
           Lead.id == lead_id,
           Lead.cuenta_id == current_user.cuenta_id
       ).first()

2. Use the verify_tenant_access() helper:
   
   from app.core.multi_tenant import verify_tenant_access
   
   lead = verify_tenant_access(db, Lead, lead_id, current_user)

3. Add current_user dependency to all protected endpoints:
   
   current_user: User = Depends(get_current_user)

4. Run tests to verify:
   pytest tests/test_security_multi_tenant.py -v
""")


if __name__ == "__main__":
    main()
