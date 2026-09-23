# Passwords are stored in plain text (insecure)
user_passwords = {
    'abinash': 'password123'
}

def check_password(user, password):
    return user in user_passwords and user_passwords[user] == password

if __name__ == "__main__":
    print(f"The password for 'abinash' is: {user_passwords['abinash']}")
    print(f"Login successful: {check_password('abinash', 'password123')}")
