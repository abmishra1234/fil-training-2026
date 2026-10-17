"""
01_first_call.py - your first chat completion (deck: "Your first call", Parts 1+2).

Lab ideas:
  1. Change the user message.
  2. Change the developer message ("Answer like a pirate.").
  3. Remove the timeout idea: what happens if the gateway is slow? (see LLM_TIMEOUT_SECONDS)
"""

from llm_client import describe, get_client, settings
print("Config  :", describe())

client = get_client()
reply = client.chat.completions.create(
    model=settings.chat_model,
    messages=[
        {"role": "user", "content": "What is the capital of France?"},
        {"role": "developer", "content": "Answer like a pirate."}
    ],
    timeout=settings.timeout,
)

print(f"Reply   : {reply.choices[0].message.content}")

u = reply.usage
if u:
    print(f"Usage   : {u.prompt_tokens} prompt tokens, {u.completion_tokens} completion tokens, {u.total_tokens} total tokens")
