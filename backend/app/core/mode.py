from fastapi import Request

def is_demo_mode(request: Request) -> bool:
    return request.headers.get("X-YuktiFi-Mode", "production") == "demo"
