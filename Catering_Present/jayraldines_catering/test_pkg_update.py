import utils.repository as repo
import utils.db as db

print("Calling update_package...")
ok = repo.update_package(1, {
    "name": "Budget Fiesta Package",
    "price_per_pax": 350.0,
    "min_pax": 30,
    "description": "Affordable complete catering package perfect for intimate birthdays and family gatherings.",
    "image": "assets/images/packages/packages_1789223263883.jpg"
})
print("Result:", ok)
print("After update DB:", db.fetchone("SELECT pkg_id, pkg_name, pkg_image FROM packages WHERE pkg_id = 1"))
