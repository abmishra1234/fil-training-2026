# SSRF (Server-Side Request Forgery) Security Training

## Overview

This repository demonstrates Server-Side Request Forgery (SSRF) vulnerabilities and secure coding practices. SSRF occurs when an application fetches remote resources without properly validating user-supplied URLs, allowing attackers to make requests to internal systems or unauthorized external resources.

## Files in this Repository

- `a10_insecure_ssrf.py` - Demonstrates vulnerable SSRF implementation
- `a10_secure_ssrf.py` - Shows secure implementation with proper validation
- `README.md` - This documentation file

## Security Scanning with pip-audit

### What is pip-audit?

`pip-audit` is a tool developed by PyPA (Python Packaging Authority) that scans Python packages for known security vulnerabilities. It checks your installed packages against the Python Advisory Database (PyAD) and other vulnerability databases.

### Installing pip-audit

```bash
# Install pip-audit
pip install pip-audit

# Or install globally
pip install --user pip-audit
```

### Using pip-audit

#### Basic Usage
```bash
# Scan current environment
pip-audit

# Scan requirements.txt file
pip-audit -r requirements.txt

# Scan specific package
pip-audit package_name==version
```

#### Advanced Options
```bash
# Generate detailed report in JSON format
pip-audit --format=json --output=vulnerability-report.json

# Scan and automatically fix vulnerabilities (where possible)
pip-audit --fix

# Scan with specific vulnerability database
pip-audit --vulnerability-service=osv

# Exclude specific vulnerabilities
pip-audit --ignore-vuln PYSEC-2022-42969
```

#### Integration in CI/CD Pipeline
```yaml
# Example GitHub Actions workflow
name: Security Audit
on: [push, pull_request]

jobs:
  security-audit:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    - name: Install dependencies
      run: |
        pip install pip-audit
        pip install -r requirements.txt
    - name: Run security audit
      run: pip-audit
```

### Other Security Tools

Besides `pip-audit`, consider using these tools:

- **Safety**: `pip install safety && safety check`
- **Bandit**: `pip install bandit && bandit -r .`
- **Semgrep**: Static analysis tool for finding vulnerabilities
- **Snyk**: Commercial tool with free tier for open source

## Code Explanation

### Insecure SSRF Implementation (`a10_insecure_ssrf.py`)

```python
import requests
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response

app = FastAPI(title="A10 SSRF - Insecure")

@app.get('/fetch_image')
async def fetch_image(url: str):
    # Insecure: Making a request to a user-supplied URL without validation
    try:
        response = requests.get(url)
        response.raise_for_status()
        return Response(content=response.content, media_type="image/jpeg")
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error fetching image: {e}")
```

#### Vulnerabilities in Insecure Code:

1. **No URL Validation**: The application accepts any URL from the user without validation
2. **Internal Network Access**: Attackers can access internal services (e.g., `http://localhost:8080/admin`)
3. **Metadata Service Access**: Cloud metadata services can be accessed (e.g., `http://169.254.169.254/`)
4. **Port Scanning**: Attackers can scan internal network ports
5. **Protocol Abuse**: Can use different protocols like `file://`, `ftp://`, etc.

#### Attack Examples:

```bash
# Access internal services
curl "http://localhost:8000/fetch_image?url=http://127.0.0.1:22"

# Access cloud metadata (AWS)
curl "http://localhost:8000/fetch_image?url=http://169.254.169.254/latest/meta-data/"

# File system access (if supported)
curl "http://localhost:8000/fetch_image?url=file:///etc/passwd"
```

### Secure SSRF Implementation (`a10_secure_ssrf.py`)

```python
import requests
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from urllib.parse import urlparse

app = FastAPI(title="A10 SSRF - Secure")

# Whitelist of allowed domains
ALLOWED_DOMAINS = {'images.example.com', 'static.example.com'}

@app.get('/fetch_image')
async def fetch_image(url: str):
    parsed_url = urlparse(url)

    # Secure: Validate the domain against a whitelist
    if parsed_url.hostname in ALLOWED_DOMAINS:
        try:
            response = requests.get(url)
            response.raise_for_status()
            return Response(content=response.content, media_type="image/jpeg")
        except requests.exceptions.RequestException as e:
            raise HTTPException(status_code=500, detail=f"Error fetching image: {e}")
    else:
        raise HTTPException(status_code=403, detail="Forbidden domain")
```

#### Security Improvements:

1. **Domain Whitelisting**: Only allows requests to predefined trusted domains
2. **URL Parsing**: Uses `urlparse()` to extract and validate URL components
3. **Explicit Validation**: Checks hostname against `ALLOWED_DOMAINS` set
4. **Error Handling**: Returns appropriate HTTP 403 status for forbidden domains

#### Additional Security Enhancements (Best Practices):

```python
import requests
import ipaddress
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from urllib.parse import urlparse
import socket

app = FastAPI(title="Enhanced Secure SSRF")

# Configuration
ALLOWED_DOMAINS = {'images.example.com', 'static.example.com'}
ALLOWED_PROTOCOLS = {'http', 'https'}
BLOCKED_NETWORKS = [
    ipaddress.ip_network('127.0.0.0/8'),    # Localhost
    ipaddress.ip_network('10.0.0.0/8'),     # Private Class A
    ipaddress.ip_network('172.16.0.0/12'),  # Private Class B  
    ipaddress.ip_network('192.168.0.0/16'), # Private Class C
    ipaddress.ip_network('169.254.0.0/16'), # Link-local
]

def is_safe_url(url: str) -> tuple[bool, str]:
    try:
        parsed = urlparse(url)
        
        # Check protocol
        if parsed.scheme not in ALLOWED_PROTOCOLS:
            return False, f"Protocol '{parsed.scheme}' not allowed"
        
        # Check domain whitelist
        if parsed.hostname not in ALLOWED_DOMAINS:
            return False, f"Domain '{parsed.hostname}' not in whitelist"
        
        # Resolve hostname to IP and check against blocked networks
        try:
            ip = socket.gethostbyname(parsed.hostname)
            ip_obj = ipaddress.ip_address(ip)
            
            for network in BLOCKED_NETWORKS:
                if ip_obj in network:
                    return False, f"IP {ip} is in blocked network {network}"
                    
        except socket.gaierror:
            return False, "Unable to resolve hostname"
            
        return True, "URL is safe"
        
    except Exception as e:
        return False, f"URL parsing error: {str(e)}"

@app.get('/fetch_image')
async def fetch_image(url: str):
    # Enhanced security validation
    is_safe, reason = is_safe_url(url)
    
    if not is_safe:
        raise HTTPException(status_code=403, detail=f"Forbidden: {reason}")
    
    try:
        # Additional security: set timeout and follow redirect limits
        response = requests.get(
            url, 
            timeout=10,           # Prevent hanging requests
            allow_redirects=True,
            max_redirects=3       # Limit redirect chains
        )
        response.raise_for_status()
        
        # Validate content type
        content_type = response.headers.get('content-type', '')
        if not content_type.startswith('image/'):
            raise HTTPException(
                status_code=400, 
                detail="Response is not an image"
            )
            
        return Response(
            content=response.content, 
            media_type=content_type
        )
        
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error fetching image: {e}"
        )
```

## Setup and Testing

### Prerequisites

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install fastapi uvicorn requests

# Install security tools
pip install pip-audit safety bandit
```

### Running the Applications

```bash
# Run insecure version
uvicorn A10_SSRF.a10_insecure_ssrf:app --host 127.0.0.1 --port 8000

# Run secure version  
uvicorn A10_SSRF.a10_secure_ssrf:app --host 127.0.0.1 --port 8001
```

### Testing SSRF Vulnerability

```bash
# Test insecure endpoint (will work with any URL)
# The below image url can be used for testing the url diversion
url: https://picsum.photos/200/300

curl "http://127.0.0.1:8000/fetch_image?url=https://picsum.photos/200/300"

# Test secure endpoint (will only work with whitelisted domains)
# The below image url can be used for testing the url diversion
url: https://picsum.photos/200/300
#curl "http://127.0.0.1:8001/fetch_image?url=https://images.example.com/test.jpg"
curl "http://127.0.0.1:8001/fetch_image?url=https://picsum.photos/200/300"

# This should be blocked by secure implementation
curl "http://127.0.0.1:8001/fetch_image?url=https://httpbin.org/json"
```

## OWASP A10 - Server-Side Request Forgery Context

SSRF is part of the OWASP Top 10 (2021) as A10. Key points:

- **Impact**: Can lead to data exposure, internal network scanning, and service abuse
- **Common Targets**: Cloud metadata services, internal APIs, databases
- **Prevention**: Input validation, network segmentation, allowlists

## Security Best Practices

1. **Use Allowlists**: Define trusted domains/IPs explicitly
2. **Network Segmentation**: Isolate application servers from internal resources
3. **Input Validation**: Validate and sanitize all user inputs
4. **Regular Updates**: Keep dependencies updated using tools like `pip-audit`
5. **Monitoring**: Log and monitor outbound requests
6. **Least Privilege**: Run applications with minimal required permissions

## Continuous Security Monitoring

Create a script to regularly audit your dependencies:

```bash
#!/bin/bash
# audit_dependencies.sh

echo "Running security audit..."
echo "========================"

echo "1. Checking for vulnerable packages with pip-audit:"
pip-audit --format=json --output=audit-report.json
pip-audit

echo -e "\n2. Checking with Safety:"
safety check --json --output=safety-report.json
safety check

echo -e "\n3. Running Bandit static analysis:"
bandit -r . -f json -o bandit-report.json
bandit -r .

echo -e "\nSecurity audit completed. Check report files for details."
```

## Training Exercises

1. **Identify Vulnerabilities**: Review the insecure code and list all potential attack vectors
2. **Implement Fixes**: Enhance the secure version with additional protections
3. **Test Security**: Create test cases for both vulnerable and secure implementations
4. **Audit Dependencies**: Run `pip-audit` on a sample project with known vulnerabilities

## Resources

- [OWASP SSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html)
- [pip-audit Documentation](https://pypi.org/project/pip-audit/)
- [Python Security Best Practices](https://python.org/dev/security/)
- [CVE Database](https://cve.mitre.org/)

---

**Note**: This code is for educational purposes only. Never deploy the insecure version in production environments.