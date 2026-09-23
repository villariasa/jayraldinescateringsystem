"""Debug helper: inspect the ``sp_add_package`` stored procedure.

Connects to the app database and prints the procedure's declared parameters
(name, type, mode, position) followed by its full routine definition, so its
signature/body can be verified against the calling code.
"""
import utils.db as db

conn = db.get_connection()
cur = conn.cursor()
# List the parameters of every sp_add_package* overload, in declaration order.
cur.execute("""
    SELECT specific_name, parameter_name, data_type, parameter_mode, ordinal_position
    FROM information_schema.parameters
    WHERE specific_name LIKE 'sp_add_package%'
    ORDER BY ordinal_position;
""")
for r in cur.fetchall():
    print(r)

# Dump the procedure's source/definition.
cur.execute("""
    SELECT routine_name, routine_definition
    FROM information_schema.routines
    WHERE routine_name = 'sp_add_package';
""")
for r in cur.fetchall():
    print("DEF:", r)
