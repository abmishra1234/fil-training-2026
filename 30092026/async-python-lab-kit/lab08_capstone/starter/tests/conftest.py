import os

# Make the fake vendors fast for tests (must be set before 'app' is imported).
os.environ.setdefault("NOTIFY_DELAY", "0.05")
os.environ.setdefault("NOTIFY_TIMEOUT", "1.0")
