import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_schema():
    try:
        # Use DATABASE_URL from environment
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            print("DATABASE_URL not found in environment")
            return
            
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        
        tables = ['subjects', 'chapters', 'slos']
        for table in tables:
            print(f"\nSchema for table: {table}")
            # Use parameterized query to prevent SQL injection
            # Note: table names cannot be parameterized in the same way as values, 
            # but since we are iterating over a fixed list, it is safe here.
            # However, information_schema query can take the table_name as a parameter.
            query = "SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name = %s"
            cur.execute(query, (table,))
            rows = cur.fetchall()
            for row in rows:
                print(row)
        
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_schema()
