# Secure: structured logging on success/failure
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def login(username, password):
    is_successful = False  # imagine auth logic here
    if is_successful:
        logging.info('Successful login for user: %s', username)
        return True
    else:
        logging.warning('Failed login attempt for user: %s', username)
        return False

if __name__ == "__main__":
    login('testuser', 'badpass')
