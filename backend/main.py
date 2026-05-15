from dotenv import load_dotenv
load_dotenv()  # must run before any module that reads os.environ at import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import admin, appointments, chat, providers

app = FastAPI(title="Kyron Medical API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(appointments.router)
app.include_router(providers.router)
app.include_router(admin.router)
