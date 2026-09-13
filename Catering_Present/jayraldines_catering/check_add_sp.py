import utils.db as db

conn = db.get_connection()
cur = conn.cursor()
cur.execute("""
    SELECT specific_name, parameter_name, data_type, parameter_mode, ordinal_position
    FROM information_schema.parameters
    WHERE specific_name LIKE 'sp_add_package%'
    ORDER BY ordinal_position;
""")
for r in cur.fetchall():
    print(r)

cur.execute("""
    SELECT routine_name, routine_definition
    FROM information_schema.routines
    WHERE routine_name = 'sp_add_package';
""")
for r in cur.fetchall():
    print("DEF:", r)
