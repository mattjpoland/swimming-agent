import psycopg2
import os

DATABASE_URL = os.getenv("DATABASE_URL")

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def ensure_rag_sources_table():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rag_sources (
            id SERIAL PRIMARY KEY,
            type VARCHAR(16) NOT NULL,
            url TEXT,
            path TEXT,
            label TEXT,
            enabled BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW()
        );
    """)
    conn.commit()
    conn.close()

def get_all_rag_sources(enabled_only=True):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT type, url, path, label FROM rag_sources"
    if enabled_only:
        query += " WHERE enabled = TRUE"
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    sources = []
    for row in rows:
        source = {
            "type": row[0],
            "url": row[1],
            "path": row[2],
            "label": row[3]
        }
        # Remove None fields for compatibility
        source = {k: v for k, v in source.items() if v is not None}
        sources.append(source)
    return sources

def add_rag_source(source_type, url=None, path=None, label=None, enabled=True):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
        INSERT INTO rag_sources (type, url, path, label, enabled)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
    """
    cursor.execute(query, (source_type, url, path, label, enabled))
    new_id = cursor.fetchone()[0]
    conn.commit()
    conn.close()
    return new_id

def rag_source_exists(source_type, url=None, path=None, label=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT 1 FROM rag_sources WHERE type=%s AND label=%s"
    params = [source_type, label]
    if url:
        query += " AND url=%s"
        params.append(url)
    elif path:
        query += " AND path=%s"
        params.append(path)
    cursor.execute(query, tuple(params))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists