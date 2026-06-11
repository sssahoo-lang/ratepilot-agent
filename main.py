from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import os
from routers import bills, negotiations, agent
from routers import email_router
from database import init_db

app = FastAPI(title="BillFight - Autonomous Negotiation Agent", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    await init_db()

app.include_router(bills.router, prefix="/api/bills", tags=["bills"])
app.include_router(negotiations.router, prefix="/api/negotiations", tags=["negotiations"])
app.include_router(agent.router, prefix="/api/agent", tags=["agent"])
app.include_router(email_router.router, prefix="/api/email", tags=["email"])

@app.get("/")
async def root():
    return {"message": "BillFight Agent API running"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
