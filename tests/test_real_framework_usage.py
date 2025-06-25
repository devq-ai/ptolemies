#!/usr/bin/env python3
"""
Real Framework Usage Test Script
==============================

Tests actual framework usage that should be validated
against our enhanced knowledge base.
"""

# Real FastAPI usage
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel

app = FastAPI()

class User(BaseModel):
    name: str
    email: str

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/users/{user_id}")
def read_user(user_id: int):
    return {"user_id": user_id}

@app.post("/users/")
def create_user(user: User):
    return user

# Real Pydantic AI usage (if available in knowledge base)
try:
    from pydantic_ai import Agent
    
    agent = Agent('openai:gpt-4')
    
    @agent.system_prompt
    def system_prompt():
        return "You are a helpful assistant."
    
except ImportError:
    print("Pydantic AI not available")

# Some potentially unknown methods
app.unknown_method()  # Should be flagged
user.fake_attribute   # Should be flagged