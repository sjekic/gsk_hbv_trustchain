"""
Run once: python init_db.py
Creates the trustchain database and all tables.
"""
import psycopg
from app.db import engine, Base
from app import models  # noqa: F401 — registers models with Base
from sqlalchemy import text

# Create database if needed
try:
    conn = psycopg.connect("postgresql://postgres:postgres@localhost:5432/postgres", autocommit=True)
    conn.execute("CREATE DATABASE trustchain")
    conn.close()
    print("Database 'trustchain' created.")
except psycopg.errors.DuplicateDatabase:
    print("Database 'trustchain' already exists.")

# Create schema + tables
with engine.begin() as conn:
    conn.execute(text("CREATE SCHEMA IF NOT EXISTS trustchain"))
Base.metadata.create_all(bind=engine)
print("All tables created in 'trustchain' schema.")
