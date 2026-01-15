#!/usr/bin/env python
"""
KlikniJídlo v2 - Pre-Deployment Security Check

Run this script before deploying to production:
    python check_security.py
"""

import os
import sys
from pathlib import Path

# Add project to path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kliknijidlo.settings')
import django
django.setup()

from django.conf import settings
from django.core.management import call_command
from io import StringIO


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_header(text):
    print(f"\n{Colors.BLUE}{Colors.BOLD}{'=' * 70}{Colors.END}")
    print(f"{Colors.BLUE}{Colors.BOLD}{text:^70}{Colors.END}")
    print(f"{Colors.BLUE}{Colors.BOLD}{'=' * 70}{Colors.END}\n")


def print_check(name, passed, message=""):
    status = f"{Colors.GREEN}✓ PASS{Colors.END}" if passed else f"{Colors.RED}✗ FAIL{Colors.END}"
    print(f"{status} {name}")
    if message:
        print(f"     {Colors.YELLOW}{message}{Colors.END}")


def print_warning(message):
    print(f"{Colors.YELLOW}! WARNING: {message}{Colors.END}")


def print_info(message):
    print(f"{Colors.BLUE}i INFO: {message}{Colors.END}")


def check_debug_mode():
    """Check if DEBUG is False in production"""
    passed = not settings.DEBUG
    message = "" if passed else "DEBUG must be False in production!"
    print_check("DEBUG = False", passed, message)
    return passed


def check_secret_key():
    """Validate SECRET_KEY"""
    secret = settings.SECRET_KEY
    
    # Check if it's the default insecure key
    is_default = 'django-insecure' in secret
    is_short = len(secret) < 50
    
    passed = not is_default and not is_short
    
    messages = []
    if is_default:
        messages.append("Using default Django SECRET_KEY!")
    if is_short:
        messages.append(f"SECRET_KEY too short ({len(secret)} chars, min 50 recommended)")
    
    message = " ".join(messages) if messages else ""
    print_check("SECRET_KEY is secure", passed, message)
    
    if not passed:
        print_info("Generate new key: python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'")
    
    return passed


def check_allowed_hosts():
    """Check ALLOWED_HOSTS configuration"""
    hosts = settings.ALLOWED_HOSTS
    
    has_wildcard = '*' in hosts
    has_localhost_only = hosts == ['localhost', '127.0.0.1'] or hosts == ['127.0.0.1']
    has_production_domain = any('kliknijidlo.cz' in host for host in hosts)
    
    passed = not has_wildcard and has_production_domain and not has_localhost_only
    
    message = ""
    if has_wildcard:
        message = "ALLOWED_HOSTS contains '*' - this is insecure!"
    elif has_localhost_only:
        message = "ALLOWED_HOSTS only contains localhost - add production domain!"
    elif not has_production_domain:
        message = "Add jidelna.kliknijidlo.cz to ALLOWED_HOSTS"
    
    print_check("ALLOWED_HOSTS configured", passed, message)
    if passed:
        print_info(f"Hosts: {', '.join(hosts)}")
    
    return passed


def check_database():
    """Check database configuration"""
    db_engine = settings.DATABASES['default']['ENGINE']
    
    is_sqlite = 'sqlite' in db_engine
    is_production_ready = 'postgresql' in db_engine or 'mysql' in db_engine
    
    passed = is_production_ready
    
    message = ""
    if is_sqlite:
        message = "SQLite not recommended for production. Use PostgreSQL or MySQL."
    
    print_check("Database is production-ready", passed, message)
    print_info(f"Database engine: {db_engine}")
    
    return passed


def check_security_settings():
    """Check Django security settings"""
    checks = [
        ('SECURE_SSL_REDIRECT', getattr(settings, 'SECURE_SSL_REDIRECT', False)),
        ('SESSION_COOKIE_SECURE', getattr(settings, 'SESSION_COOKIE_SECURE', False)),
        ('CSRF_COOKIE_SECURE', getattr(settings, 'CSRF_COOKIE_SECURE', False)),
        ('SECURE_HSTS_SECONDS', getattr(settings, 'SECURE_HSTS_SECONDS', 0) > 0),
        ('X_FRAME_OPTIONS', getattr(settings, 'X_FRAME_OPTIONS', None) == 'DENY'),
    ]
    
    all_passed = True
    for name, value in checks:
        passed = value if not settings.DEBUG else True  # Allow in development
        if not passed:
            all_passed = False
        print_check(f"  {name}", passed, "" if passed else "Should be enabled in production")
    
    return all_passed


def check_csrf_trusted_origins():
    """Check CSRF_TRUSTED_ORIGINS"""
    origins = getattr(settings, 'CSRF_TRUSTED_ORIGINS', [])
    
    has_https = any(origin.startswith('https://') for origin in origins)
    has_production = any('kliknijidlo.cz' in origin for origin in origins)
    
    passed = has_https and has_production
    
    message = ""
    if not has_https:
        message = "CSRF_TRUSTED_ORIGINS should use HTTPS"
    elif not has_production:
        message = "Add https://jidelna.kliknijidlo.cz to CSRF_TRUSTED_ORIGINS"
    
    print_check("CSRF_TRUSTED_ORIGINS configured", passed, message)
    if origins:
        print_info(f"Origins: {', '.join(origins)}")
    
    return passed


def check_directories():
    """Check required directories exist"""
    dirs_to_check = [
        ('logs', 'Log files directory'),
        ('media', 'User uploaded files'),
        ('staticfiles', 'Collected static files'),
    ]
    
    all_passed = True
    for dirname, description in dirs_to_check:
        dir_path = BASE_DIR / dirname
        exists = dir_path.exists()
        
        if not exists:
            all_passed = False
            message = f"{description} - Create with: mkdir -p {dirname}"
        else:
            message = ""
        
        print_check(f"  {dirname}/ exists", exists, message)
    
    return all_passed


def check_static_files():
    """Check if static files are collected"""
    static_root = Path(settings.STATIC_ROOT)
    
    if not static_root.exists():
        passed = False
        message = "Run: python manage.py collectstatic"
    else:
        # Check if directory has files
        has_files = any(static_root.iterdir())
        passed = has_files
        message = "" if passed else "Run: python manage.py collectstatic"
    
    print_check("Static files collected", passed, message)
    return passed


def check_env_file():
    """Check if .env file exists"""
    env_file = BASE_DIR / '.env'
    env_example = BASE_DIR / '.env.example'
    
    passed = env_file.exists()
    
    message = ""
    if not passed:
        if env_example.exists():
            message = "Create from: cp .env.example .env"
        else:
            message = ".env file missing!"
    
    print_check(".env file exists", passed, message)
    return passed


def run_django_check():
    """Run Django's built-in security check"""
    print(f"\n{Colors.BOLD}Running Django deployment checks...{Colors.END}\n")
    
    try:
        # Capture output
        out = StringIO()
        call_command('check', '--deploy', stdout=out, stderr=out)
        output = out.getvalue()
        
        if 'System check identified no issues' in output:
            print(f"{Colors.GREEN}✓ Django deployment check passed!{Colors.END}")
            return True
        else:
            print(f"{Colors.YELLOW}{output}{Colors.END}")
            return False
    except Exception as e:
        print(f"{Colors.RED}✗ Django check failed: {e}{Colors.END}")
        return False


def main():
    print_header("KlikniJídlo v2 - Production Security Check")
    
    results = []
    
    # Run all checks
    results.append(('Environment', check_env_file()))
    results.append(('DEBUG Mode', check_debug_mode()))
    results.append(('SECRET_KEY', check_secret_key()))
    results.append(('ALLOWED_HOSTS', check_allowed_hosts()))
    results.append(('Database', check_database()))
    results.append(('CSRF Origins', check_csrf_trusted_origins()))
    
    print(f"\n{Colors.BOLD}Security Settings:{Colors.END}")
    results.append(('Security', check_security_settings()))
    
    print(f"\n{Colors.BOLD}File System:{Colors.END}")
    results.append(('Directories', check_directories()))
    results.append(('Static Files', check_static_files()))
    
    # Django's deployment check
    results.append(('Django Check', run_django_check()))
    
    # Summary
    print_header("Summary")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    if passed == total:
        print(f"{Colors.GREEN}{Colors.BOLD}✓ ALL CHECKS PASSED ({passed}/{total}){Colors.END}")
        print(f"\n{Colors.GREEN}Your application is ready for production deployment!{Colors.END}")
        print(f"\nNext steps:")
        print(f"  1. Review DEPLOY.md for deployment instructions")
        print(f"  2. Set up SSL certificate (Let's Encrypt)")
        print(f"  3. Configure Nginx/Apache")
        print(f"  4. Set up automated backups")
        return 0
    else:
        failed = total - passed
        print(f"{Colors.RED}{Colors.BOLD}✗ {failed} CHECK(S) FAILED ({passed}/{total} passed){Colors.END}")
        print(f"\n{Colors.RED}Please fix the issues above before deploying to production.{Colors.END}")
        print(f"\nRefer to DEPLOY.md for detailed instructions.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
