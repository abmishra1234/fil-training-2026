# Insecure: no logging on failure -> blind spots
def login(username, password):
    is_successful = False  # imagine auth logic here
    if is_successful:
        return True
    else:
        # No logs on failure
        return False
