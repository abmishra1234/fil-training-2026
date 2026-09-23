import sqlite3

def get_user_by_username_safe(username: str):
    conn = sqlite3.connect(':memory:')
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE users (id INT, username TEXT)")
    cursor.execute("INSERT INTO users VALUES (1, 'Abinash'), (2, 'Rahul')")
    
    # Secure: Using parameterized queries
    query = "SELECT * FROM users WHERE username = ?"
    cursor.execute(query, (username,))
    user = cursor.fetchall()
    conn.close()
    return user

if __name__ == "__main__":
    # Attacker input: ' OR 1=1 --
    attacker_input = "' OR 1=1 --"
    print(f"Users found: {get_user_by_username_safe(attacker_input)}")

# The secure version uses parameterized queries to prevent SQL injection attacks.
    attacker_input = "Abinash"
    print(f"Users found: {get_user_by_username_safe(attacker_input)}")
