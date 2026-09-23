from fastapi import FastAPI, HTTPException # type: ignore

app = FastAPI(title="A01 Broken Access Control - Insecure")

# Dummy user data
users = {
    '1': {'name': 'Abinash', 'email': 'abinash@example.com'},
    '2': {'name': 'Rahul', 'email': 'rahul@example.com'}
}

@app.get("/user/{user_id}")
async def get_user(user_id: str):
    # Insecure: Fails to check user authorization
    if user_id in users:
        return users[user_id]
    raise HTTPException(status_code=404, detail="User not found")
