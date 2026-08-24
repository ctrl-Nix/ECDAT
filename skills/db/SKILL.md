# DB Skill

Rules:
- PostgreSQL only.
- SQLAlchemy 2.0 only.
- Use TIMESTAMPTZ for timestamps that need timezone semantics.
- Use TEXT instead of VARCHAR for string columns.
- Use ON DELETE CASCADE for dependent relationships.
- Check constraints must match enum values used in code.
- The model stores all 12 scanner Finding fields.
- No multi-DBMS compatibility layer.
- Add indexes on foreign keys and filter columns.
- CRUD.py is the ONLY file that writes to the database.
- Test with SQLite in-memory when possible.
