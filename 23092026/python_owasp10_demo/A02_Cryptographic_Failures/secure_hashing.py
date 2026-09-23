from werkzeug.security import generate_password_hash, check_password_hash # type: ignore

# Passwords are hashed and salted
user_passwords_hashed = {
    'abinash': generate_password_hash('password123')
}

def check_password_secure(user, password):
    if user in user_passwords_hashed:
        return check_password_hash(user_passwords_hashed[user], password)
    return False

if __name__ == "__main__":
    print(f"The password hash for 'password123' is: {user_passwords_hashed['abinash']}")
    print(f"Login successful: {check_password_secure('abinash', 'password123')}")
