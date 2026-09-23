"""Debug script: verify a raw SQL UPDATE against the ``packages`` table.

Bypasses the repository/stored-procedure layer to run a direct parameterised
UPDATE on package id 1 (including the conditional image-keep logic), commits it,
then re-selects the row to confirm the values actually persisted. Used to
isolate whether an update bug is in the SQL itself or in higher-level code.
"""
import utils.db_config as cfg
import utils.db as db

cfg.load_db_config()
conn = db.get_connection()
# Manage the transaction explicitly so we can commit only after the UPDATE.
conn.autocommit = False
cur = conn.cursor()
image_val = "assets/images/packages/packages_1789223263883.jpg"
# CASE keeps the existing pkg_image when the passed value is empty; otherwise overwrites it.
cur.execute("""
    UPDATE packages
    SET pkg_name = %s, pkg_price_per_pax = %s, pkg_min_pax = %s, pkg_description = %s,
        pkg_image = CASE WHEN %s <> '' THEN %s ELSE pkg_image END
    WHERE pkg_id = %s
""", ("Budget Fiesta Package", 350.0, 30, "Test desc", image_val, image_val, 1))
print("Rowcount:", cur.rowcount)
conn.commit()

# Read the row back to confirm the committed values.
cur.execute("SELECT pkg_id, pkg_name, pkg_image FROM packages WHERE pkg_id = 1")
print("Fetched:", cur.fetchone())
