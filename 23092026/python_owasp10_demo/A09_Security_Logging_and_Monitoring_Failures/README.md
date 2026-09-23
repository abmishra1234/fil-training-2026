Here is the updated content for your README.md:

---

# **Python Secure Coding Training**

This repository contains code examples for the secure coding training session. It covers common vulnerabilities and demonstrates secure coding practices.

---

## **Code Explanation: The Importance of Logging 🪵**

Logging is crucial for security. Without it, you have no visibility into what's happening in your application. This makes it impossible to detect attacks, investigate breaches, or debug issues. The provided code files illustrate this point using a simple login function.

### **insecure\_no\_logging.py: The Blind Spot 🙈**

This file demonstrates a dangerous practice: failing to log security-relevant events.

Python

\# Insecure: no logging on failure \-\> blind spots  
def login(username, password):  
    is\_successful \= False  \# imagine auth logic here  
    if is\_successful:  
        return True  
    else:  
        \# No logs on failure  
        return False

* **What's the problem?** The login function has no logging at all for failed attempts. If an attacker tries to guess passwords for a user (a "brute-force" attack), this activity is completely invisible.  
* **The Risk:** You will have no record of the attack and no way to respond. This lack of visibility is a major security flaw.

---

### **secure\_logging.py: Gaining Visibility 👁️**

This file shows the correct approach. It uses Python's built-in logging module to record both successful and failed login attempts.

Python

\# Secure: structured logging on success/failure  
import logging  
logging.basicConfig(level=logging.INFO, format\='%(asctime)s \- %(levelname)s \- %(message)s')

def login(username, password):  
    is\_successful \= False  \# imagine auth logic here  
    if is\_successful:  
        logging.info('Successful login for user: %s', username)  
        return True  
    else:  
        logging.warning('Failed login attempt for user: %s', username)  
        return False

if \_\_name\_\_ \== "\_\_main\_\_":  
    login('testuser', 'badpass')

* **What's improved?**  
  * **Logging is configured:** logging.basicConfig sets up a simple logger that includes a timestamp, the log level (e.g., INFO, WARNING), and the message.  
  * **Success is logged:** logging.info records successful logins. This is useful for auditing and tracking user activity.  
  * **Failure is logged:** logging.warning records failed login attempts. This is critical for security monitoring. Multiple failed attempts for the same user could trigger an alert for a potential attack.  
* **The Benefit:** By logging these events, you create an audit trail. This data can be fed into monitoring systems to detect suspicious behavior in real-time and provides crucial information for investigating incidents after they occur.

---

## **Detect Outdated/Vulnerable Components with pip-audit 🛡️**

Your application is only as secure as its weakest dependency. Using third-party packages is great for productivity, but they can contain known security vulnerabilities. Manually tracking this is impossible. Tools like pip-audit automate this for you.

### **What is pip-audit?**

pip-audit is a command-line tool that scans your Python environment or project dependencies against the Python Package Index (PyPI) vulnerability database to find packages with known vulnerabilities.

### **Installation**

You can install it easily using pip:

Bash

pip install pip-audit

### **How to Use It**

You can run pip-audit in a couple of primary ways.

1. Scan your current environment:  
   Simply run the command in your terminal with your project's virtual environment activated.  
   Bash  
   pip-audit

2. Scan a requirements file:  
   Point it directly at your project's dependency file.  
   Bash  
   pip-audit \-r requirements.txt

### **Example Output**

If pip-audit finds a vulnerability, it will give you a clear report like this:

$ pip-audit \-r requirements.txt  
Found 1 known vulnerability in 1 package  
Name    Version    ID                  Fix versions  
\------- \---------- \------------------- \------------  
Flask   0.5        PYSEC-2019-179      0.12  
Description:  
Pallets-Jinja captured the less-than and greater-than characters in an  
HTML-escaped form...

This output tells you:

* **Name:** The vulnerable package (Flask).  
* **Version:** The version you are using (0.5).  
* **ID:** The unique ID of the vulnerability (PYSEC-2019-179).  
* **Fix versions:** The version you should upgrade to (0.12).

### **Best Practice**

Integrate pip-audit into your **Continuous Integration/Continuous Deployment (CI/CD)** pipeline. This ensures that every time you build your project, your dependencies are automatically scanned for new vulnerabilities, preventing insecure code from ever reaching production.