import psycopg2

def check_schema():
    try:
        conn = psycopg2.connect("postgresql://postgres.ejqbeibaopjwzwvxcudu:Getdev.com%40123@aws-1-ap-northeast-2.pooler.supabase.com:6543/postgres")
        cur = conn.cursor()
        
        tables = ['subjects', 'chapters', 'slos']
        for table in tables:
            print(f"\nSchema for table: {table}")
            cur.execute(f"SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name = '{table}'")
            rows = cur.fetchall()
            for row in rows:
                print(row)
        
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_schema()
