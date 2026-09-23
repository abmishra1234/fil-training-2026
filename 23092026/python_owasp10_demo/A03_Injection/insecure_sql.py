import sqlite3

def get_user_by_username(username: str):
    conn = sqlite3.connect(':memory:')
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE users (id INT, username TEXT)")
    cursor.execute("INSERT INTO users VALUES (1, 'Abinash'), (2, 'Rahul')")
    
    # Insecure: Using user input directly in the SQL query
    query = f"SELECT * FROM users WHERE username = '{username}'"
    cursor.execute(query)
    user = cursor.fetchall()
    conn.close()
    return user

if __name__ == "__main__":
    # Attacker input: ' OR 1=1 --
    attacker_input = "' OR 1=1 --"
    print(f"Users found: {get_user_by_username(attacker_input)}")
