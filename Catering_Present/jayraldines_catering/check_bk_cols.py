import utils.db as db

cur = db.get_connection().cursor()
cur.execute("""
    SELECT column_name, data_type 
    FROM information_schema.columns 
    WHERE table_name = 'bookings'
    ORDER BY ordinal_position;
""")
for r in cur.fetchall():
    print(r)
