import utils.db_config as cfg
import utils.db as db

cfg.load_db_config()
conn = db.get_connection()
conn.autocommit = False
cur = conn.cursor()
image_val = "assets/images/packages/packages_1789223263883.jpg"
cur.execute("""
    UPDATE packages
    SET pkg_name = %s, pkg_price_per_pax = %s, pkg_min_pax = %s, pkg_description = %s,
        pkg_image = CASE WHEN %s <> '' THEN %s ELSE pkg_image END
    WHERE pkg_id = %s
""", ("Budget Fiesta Package", 350.0, 30, "Test desc", image_val, image_val, 1))
print("Rowcount:", cur.rowcount)
conn.commit()

cur.execute("SELECT pkg_id, pkg_name, pkg_image FROM packages WHERE pkg_id = 1")
print("Fetched:", cur.fetchone())
