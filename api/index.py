"""
Vercel 서버리스 진입점.

backend/ 를 import 경로에 올리고 FastAPI 앱을 그대로 노출한다.
Vercel Python 런타임이 ASGI 앱(`app`)을 자동으로 잡는다.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend"))

from app.main import app  # noqa: E402,F401
