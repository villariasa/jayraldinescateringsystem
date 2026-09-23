"""Debug script: exercise the repository-level ``update_package`` path.

Calls ``repo.update_package`` for package id 1 with a sample payload (the
higher-level API that wraps the stored procedure / SQL), prints its return
value, then re-reads the row to confirm the change persisted. Complements
``test_direct_update.py`` by testing the code path instead of raw SQL.
"""
import utils.repository as repo
import utils.db as db

print("Calling update_package...")
# Update via the repository API using its dict-based field names.
ok = repo.update_package(1, {
    "name": "Budget Fiesta Package",
    "price_per_pax": 350.0,
    "min_pax": 30,
    "description": "Affordable complete catering package perfect for intimate birthdays and family gatherings.",
    "image": "assets/images/packages/packages_1789223263883.jpg"
})
print("Result:", ok)
# Re-read the row to verify the update actually landed in the database.
print("After update DB:", db.fetchone("SELECT pkg_id, pkg_name, pkg_image FROM packages WHERE pkg_id = 1"))
