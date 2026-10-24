import os
import sys
import argparse
import psycopg2

def run_migrations(db_url: str):
    print(f"[*] Connecting to PostgreSQL database...")
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        cursor = conn.cursor()
        print("[+] Successfully connected to database.")
    except Exception as e:
        print(f"[!] Failed to connect to database: {e}")
        sys.exit(1)

    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    mig1_path = os.path.join(root_dir, "supabase", "migrations", "001_initial_schema.sql")
    mig2_path = os.path.join(root_dir, "supabase", "migrations", "002_rls_policies.sql")

    # 1. Run Initial Schema
    print("[*] Applying 001_initial_schema.sql...")
    with open(mig1_path, "r", encoding="utf-8") as f:
        sql1 = f.read()
    try:
        cursor.execute(sql1)
        print("[+] 001_initial_schema.sql applied successfully.")
    except Exception as e:
        print(f"[!] Error applying 001_initial_schema.sql: {e}")
        conn.close()
        sys.exit(1)

    # 2. Run RLS Policies
    print("[*] Applying 002_rls_policies.sql...")
    with open(mig2_path, "r", encoding="utf-8") as f:
        sql2 = f.read()
    try:
        cursor.execute(sql2)
        print("[+] 002_rls_policies.sql applied successfully.")
    except Exception as e:
        print(f"[!] Error applying 002_rls_policies.sql: {e}")
        conn.close()
        sys.exit(1)

    # 3. Verify public tables
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        ORDER BY table_name;
    """)
    tables = [r[0] for r in cursor.fetchall()]
    print(f"\n[+] Migration Complete! Verified {len(tables)} tables in database:")
    for t in tables:
        print(f"    - {t}")

    cursor.close()
    conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Automated Supabase / PostgreSQL Migration Runner")
    parser.add_argument("--db-url", type=str, help="PostgreSQL connection string (from Supabase Database settings)")
    args = parser.parse_args()

    db_url = args.db_url or os.getenv("DATABASE_URL")
    if not db_url:
        db_url = input("Enter your Supabase PostgreSQL connection URI: ").strip()

    if not db_url:
        print("[!] No connection string provided. Aborting.")
        sys.exit(1)

    run_migrations(db_url)
