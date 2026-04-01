import psycopg2

try:
    conn = psycopg2.connect(
        dbname="postgres",
        user="postgres",
        password="getdev.com@123",
        host="db.ejqbeibaopjwzwvxcudu.supabase.co",
        port="5432",
        sslmode="require"
    )
    print("✅ Connection successful!")
    conn.close()
except Exception as e:
    print("❌ Connection failed:", e)