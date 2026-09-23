# Python OWASP Top 10 – Demo (FastAPI + Scripts)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](#prerequisites) [![FastAPI](https://img.shields.io/badge/FastAPI-0.110-green)](#prerequisites) [![License](https://img.shields.io/badge/educational-demo-important)](#-disclaimer)

This repository is an **educational demo** showcasing the **OWASP Top 10** concepts in Python.
It contains small, focused examples for each category—typically in **paired files**: one **insecure** implementation and one **secure** fix.

Many examples are served via **FastAPI** apps (run with `uvicorn`), while others are simple Python scripts runnable with `python file.py`.

> **Audience**: beginner-friendly, with step-by-step setup for **Windows** and **macOS/Linux**.


## Table of Contents
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
  - [Windows (PowerShell or CMD)](#windows-powershell-or-cmd)
  - [macOS/Linux (bash/zsh)](#macoslinux-bashzsh)
- [Project Layout](#project-layout)
- [How to Run Demos](#how-to-run-demos)
  - [FastAPI examples (served with Uvicorn)](#fastapi-examples-served-with-uvicorn)
  - [Script-only examples](#script-only-examples)
- [Testing — Quick Smoke Tests](#testing--quick-smoke-tests)
- [Basic Jenkinsfile (CI Pipeline)](#basic-jenkinsfile-ci-pipeline)
  - [Running this pipeline](#running-this-pipeline)
- [Troubleshooting](#troubleshooting)
- [⚠️ Disclaimer](#-disclaimer)


## Prerequisites

- **Python**: 3.10 or newer (3.11 recommended)
- **pip**: comes with Python
- **Git** (optional, if you clone from a repo)
- **curl** or a REST client (e.g., Postman) for trying endpoints
- **(Optional)**: `virtualenv` or `venv` (we automate this for you)

> We ship a `vendor/` folder with pre-downloaded wheels to speed up installs (especially helpful on offline/locked-down machines). If `vendor/` is present, our bootstrap script uses it automatically.


## Quick Start

> The project includes a helper script **`bootstrap.py`** to create a virtual environment and install dependencies (preferring local wheels in `vendor/` if available).

### Windows (PowerShell or CMD)
```pwsh
# 1) Unzip the archive
Expand-Archive .\python_owasp10_demo.zip -DestinationPath .

# 2) Move into the project
cd .\python_owasp10_demo

# 3) Create venv + install packages (uses vendor/ if present)
python bootstrap.py

# 4) Activate the virtual environment
# PowerShell:
. .\.venv\Scripts\Activate.ps1
# CMD:
call .\.venv\Scripts\activate

# 5) Verify install
python -c "import fastapi, uvicorn; print('Deps OK')"

# 6) (Optional) See an example command to run a demo app
type run.bat
```

### macOS/Linux (bash/zsh)
```bash
# 1) Unzip the archive
unzip python_owasp10_demo.zip

# 2) Move into the project
cd python_owasp10_demo

# 3) Create venv + install packages (uses vendor/ if present)
python3 bootstrap.py

# 4) Activate the virtual environment
source .venv/bin/activate

# 5) Verify install
python -c "import fastapi, uvicorn; print('Deps OK')"

# 6) (Optional) See an example command to run a demo app
cat run.sh
```

## Project Layout

Key folders by OWASP category (each has *insecure* vs *secure* examples):

- `A01_Broken_Access_Control/`
  - `a01_insecure_access.py`
  - `a01_secure_access.py`
- `A02_Cryptographic_Failures/`
  - `insecure_plaintext.py`
  - `secure_hashing.py`
- `A03_Injection/`
  - `insecure_sql.py`
  - `secure_sql.py`
- `A04_Insecure_Design/`
  - `insecure_no_rate_limit.py`
  - `secure_rate_limit.py`
- `A05_Security_Misconfiguration/`
  - `a05_insecure_config.py`
  - `a05_secure_config.py`
- `A07_Identification_Authentication_Failures/`
  - `insecure_no_verify_jwt.py`
  - `secure_verify_jwt.py`
- `A08_Software_and_Data_Integrity_Failures/`
  - `insecure_pickle.py`
  - `secure_json.py`
- `A09_Security_Logging_and_Monitoring_Failures/`
  - `insecure_no_logging.py`
  - `secure_logging.py`
- `A10_SSRF/`
  - `a10_insecure_ssrf.py`
  - `a10_secure_ssrf.py`


## How to Run Demos

There are two styles of examples:

1. **FastAPI apps** (run with `uvicorn`): these start a local HTTP server.
2. **Plain Python scripts**: run directly with `python file.py`.

> Tip: the files are tiny—open them to read the insecure pattern and the secure fix side-by-side.


### FastAPI examples (served with Uvicorn)

Activate your **virtual environment** first (see *Quick Start*), then use this pattern:

```bash
uvicorn A01_Broken_Access_Control.a01_insecure_access:app --port 5001
# or the secure variant
uvicorn A01_Broken_Access_Control.a01_secure_access:app --port 5001
```

Now call the endpoint from another terminal:

```bash
# Insecure access control demo
curl "http://127.0.0.1:5001/user/1"
curl "http://127.0.0.1:5001/user/2"
```

**Other FastAPI examples** (same pattern):
- `A10_SSRF/a10_insecure_ssrf.py` → `A10_SSRF.a10_insecure_ssrf:app`
- `A10_SSRF/a10_secure_ssrf.py`   → `A10_SSRF.a10_secure_ssrf:app`

**SSRF demo quick test** (insecure version allows any URL; secure version restricts domains):
```bash
# Insecure: fetch any image URL (⚠️ demonstration only)
curl -G "http://127.0.0.1:5001/fetch_image" --data-urlencode "url=https://httpbin.org/image/jpeg" -o test.jpg

# Secure: only allowed domains (as coded in the example)
curl -G "http://127.0.0.1:5001/fetch_image" --data-urlencode "url=https://images.example.com/path.jpg" -o test.jpg
```

> If the port is in use, change `--port` (e.g., `--port 8000`). You can also add `--reload` during development for auto-reload.


### Script-only examples

Run them directly with Python (after activating the venv):

```bash
# A02 – Cryptographic Failures
python A02_Cryptographic_Failures/insecure_plaintext.py
python A02_Cryptographic_Failures/secure_hashing.py

# A03 – Injection
python A03_Injection/insecure_sql.py     # Shows SQL injection risk
python A03_Injection/secure_sql.py       # Uses parameters

# A07 – Identification & Authentication Failures
python A07_Identification_Authentication_Failures/insecure_no_verify_jwt.py
python A07_Identification_Authentication_Failures/secure_verify_jwt.py

# A08 – Software & Data Integrity Failures
python A08_Software_and_Data_Integrity_Failures/insecure_pickle.py
python A08_Software_and_Data_Integrity_Failures/secure_json.py

# A09 – Logging & Monitoring
python A09_Security_Logging_and_Monitoring_Failures/insecure_no_logging.py
python A09_Security_Logging_and_Monitoring_Failures/secure_logging.py
```

> Some categories include additional notes or example requirement files (e.g., `A06_Vulnerable_Outdated_Components/`). Read their contents for context.


## Testing — Quick Smoke Tests

This demo doesn't ship a formal unit-test suite, but you can still **smoke test** quickly:

```bash
# 1) Import key packages
python -c "import fastapi, uvicorn, requests, jwt; print('Imports OK')"

# 2) Run a server and hit an endpoint (see above)
uvicorn A01_Broken_Access_Control.a01_secure_access:app --port 5001 &
sleep 2
curl -i http://127.0.0.1:5001/user/1
```

If you want to add unit tests later, install `pytest` into the venv:
```bash
pip install pytest
pytest -q
```


## Basic Jenkinsfile (CI Pipeline)

> Place a file named **`Jenkinsfile`** at the root of the project (beside `bootstrap.py`). This simple pipeline installs dependencies and runs quick smoke checks.

```groovy
pipeline {
  agent any

  options {
    timestamps()
  }

  tools {
    // Make sure a Python 3.11 tool is configured in Jenkins (Manage Jenkins → Global Tool Configuration)
    // Or install Python in the agent and remove this block.
  }

  stages {
    stage('Checkout') {
      steps {
        checkout scm
      }
    }

    stage('Setup venv + Deps') {
      steps {
        sh '''#!/usr/bin/env bash
        set -e
        python3 --version
        python3 bootstrap.py
        source .venv/bin/activate
        python -c "import fastapi, uvicorn, requests, jwt; print('Deps OK')"
        '''
      }
    }

    stage('Smoke Tests') {
      steps {
        sh '''#!/usr/bin/env bash
        set -e
        source .venv/bin/activate
        # Start a sample app in background, hit it, then kill it
        uvicorn A01_Broken_Access_Control.a01_secure_access:app --port 5010 &
        PID=$!
        sleep 2
        curl -sSf http://127.0.0.1:5010/user/1 | grep -q "Alice"
        kill $PID || true
        '''
      }
    }
  }

  post {
    always {
      archiveArtifacts artifacts: '**/*.py', fingerprint: true, onlyIfSuccessful: false
    }
  }
}
```

### Running this pipeline

1. **Push** this project to a Git repository accessible by Jenkins.
2. Create a **Multibranch Pipeline** or **Pipeline** job pointing at your repo.
3. Ensure the agent has **Python 3.10+** and basic tools: `bash`, `curl`.
4. Run the job; you should see *Setup venv + Deps* and *Smoke Tests* stages pass.


## Troubleshooting

- **`pip` cannot build wheels / no internet** → We include `vendor/` with prebuilt wheels; `bootstrap.py` will use it automatically. Ensure you run `python bootstrap.py` from the project root so it finds `vendor/`.
- **Virtual env not activating (Windows)** → If `Activate.ps1` is blocked, enable scripts temporarily:  
  `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`
- **Port already in use** → Change `--port` (e.g., `--port 8000`).
- **`ModuleNotFoundError`** → Confirm the venv is activated: prompt should show `(.venv)`; otherwise run `source .venv/bin/activate` (macOS/Linux) or `.\.venv\Scripts\activate` (Windows).
- **Permission denied on shell scripts (macOS/Linux)** → Make them executable: `chmod +x run.sh`.


## ⚠️ Disclaimer

This repo is for **education and demonstration only**. The insecure samples are intentionally vulnerable—**do not** deploy them to production or accessible environments. Always follow your organization’s security policies and the official OWASP guidance.

