"""Debug helper: print the columns of the ``bookings`` table.

Queries ``information_schema.columns`` and prints each column name and data
type in ordinal order, used to confirm the bookings schema.
"""
import utils.db as db

cur = db.get_connection().cursor()
# Fetch column name + type for the bookings table, in physical column order.
cur.execute("""
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_name = 'bookings'
    ORDER BY ordinal_position;
""")
for r in cur.fetchall():
    print(r)
