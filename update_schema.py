import sqlite3
from app.config import DB_PATH

def migrate_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        c.execute("""
        CREATE TABLE IF NOT EXISTS incoming_batches (
            batch_id TEXT PRIMARY KEY,
            model_id TEXT,
            file_name TEXT,
            uploaded_at TEXT,
            row_count INTEGER,
            column_count INTEGER,
            schema_hash TEXT,
            has_target INTEGER,
            status TEXT,
            error_message TEXT
        )
        """)
        
        c.execute("""
        CREATE TABLE IF NOT EXISTS incoming_batch_rows (
            batch_id TEXT,
            row_number INTEGER,
            row_data TEXT,
            FOREIGN KEY (batch_id) REFERENCES incoming_batches(batch_id) ON DELETE CASCADE
        )
        """)
        
        c.execute("CREATE INDEX IF NOT EXISTS idx_batch_rows_batch_id ON incoming_batch_rows(batch_id)")
        
        conn.commit()
        print("Schema migration successful.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    migrate_db()
