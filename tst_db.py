import psycopg2

try:
    conn = psycopg2.connect(
    "postgresql://postgres.ejqbeibaopjwzwvxcudu:Getdev.com%40123@aws-1-ap-northeast-2.pooler.supabase.com:6543/postgres")

    print("✅ Connection successful!")
    conn.close()
except Exception as e:
    print("❌ Connection failed:", e)