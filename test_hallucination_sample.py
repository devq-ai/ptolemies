#!/usr/bin/env python3
"""
Sample script with potential hallucinations for testing
======================================================

This script contains a mix of valid and potentially hallucinated code
to test our hallucination detection system.
"""

# Valid imports
import os
import json
from fastapi import FastAPI
from pydantic import BaseModel

# Potentially hallucinated imports
from nonexistent_framework import MagicAPI
from imaginary_lib import FakeClass

# Valid code
app = FastAPI()

class UserModel(BaseModel):
    name: str
    email: str

# Potentially hallucinated code
magic_app = MagicAPI()
fake_obj = FakeClass()

# Valid method calls
@app.get("/users")
def get_users():
    return {"users": []}

# Potentially hallucinated method calls
magic_app.super_method()
fake_obj.nonexistent_function()

# Valid function calls
print("Hello, world!")
len([1, 2, 3])

# Potentially hallucinated function calls
imaginary_function()
another_fake_func("test")

# Valid attribute access
app.title
os.path

# Potentially hallucinated attribute access
magic_app.impossible_attribute
fake_obj.made_up_property