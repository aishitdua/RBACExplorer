#!/usr/bin/env python3
"""
Pre-migration guard: stamps Alembic version for databases that already have
the schema but no Alembic version tracking (e.g. existing Neon DB on re-deploy).
"""

import os
import subprocess
import sys

import psycopg2

url = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")

conn = psycopg2.connect(url)
cur = conn.cursor()

# Check if alembic_version table exists and has a row
cur.execute("""
    SELECT version_num FROM alembic_version LIMIT 1
""")
version = cur.fetchone()
conn.close()

if version:
    print(f"Alembic already at {version[0]}, running upgrade head.")
else:
    # No version recorded — detect how much of the schema already exists
    conn2 = psycopg2.connect(url)
    cur2 = conn2.cursor()

    cur2.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables WHERE table_name = 'projects'
        )
    """)
    has_projects = cur2.fetchone()[0]

    if has_projects:
        cur2.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'projects' AND column_name = 'owner_user_id'
        """)
        has_owner_col = cur2.fetchone() is not None
        stamp = "a1b2c3d4e5f6" if has_owner_col else "e54c4c2d9945"
        print(f"Tables exist without Alembic tracking — stamping at {stamp}")
        subprocess.run(["alembic", "stamp", stamp], check=True, capture_output=False)
    else:
        print("Fresh database — running all migrations from scratch.")

    conn2.close()

sys.exit(subprocess.run(["alembic", "upgrade", "head"]).returncode)
