"""
File: backend/app/database.py
Description:
    Database Connection & Session Management (PostgreSQL).
    - Configures SQLAlchemy engine with PostgreSQL connection pooling.
    - Sets up the scoped session maker (SessionLocal).
    - Defines Base declarative model class.
    - Provides dependency generator (get_db) yielding a database session per request.
"""
