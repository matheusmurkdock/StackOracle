from v3.normalize import normalize

logs = [
    "GET /users/123/profile 500",
    "GET /users/456/profile 503",
    "timeout after 5234ms user_id=99",
    "timeout after 6123ms user_id=42",
]

for l in logs:
    print(normalize(l))

