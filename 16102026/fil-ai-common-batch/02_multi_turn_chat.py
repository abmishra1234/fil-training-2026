"""
02_multi_turn_chat.py - roles in action: the model has no memory, YOU send the history.

    python 02_multi_turn_chat.py        (type 'exit' to quit)
"""

from llm_client import describe, get_client, settings
print("Config  :", describe())

client = get_client()
messages = [{"role": "user", "content": "Hello, who are you?"},
            {"role": "developer", "content": "Answer like a pirate."}]
             
while True:
    user_text = input("You      : ")
    if user_text.lower() in {"exit", "quit", ""}:
        break   
    messages.append({"role": "user", "content": user_text})

    reply = client.chat.completions.create(
        model=settings.chat_model, 
        messages=messages, 
        timeout=settings.timeout
    )

    answer = reply.choices[0].message.content
    print(f"bot>,   : {answer}")

    messages.append({"role": "assistant", "content": answer})
    print(f"[history: {len(messages)} messages, {reply.usage.total_tokens} tokens this call]")
