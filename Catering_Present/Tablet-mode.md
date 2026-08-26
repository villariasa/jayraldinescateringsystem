Create a **Tablet App** for Jayraldine’s Catering System.

This tablet app is a **new application** and currently does not exist. Its purpose is to allow staff to create customer orders from the tablet, preview the order, print the customer receipt, and export the completed order so it can be transferred/imported into the main PC application.

The tablet should intentionally have a **limited feature set**. Do not replicate the entire PC system on the tablet.

## 1. Tablet App Scope

The tablet should contain only these main features:

### Customer + Order

Allow the user to:

* Add/select a customer
* Enter customer information
* Create an order
* Select the catering package/menu
* Add order items
* Set event/order details
* Add applicable additional charges
* Enter the required order information

After completing the order, show an **Order Preview** before finalizing.

The preview must allow the staff to verify all information before confirming the order.

---

## 2. Order Preview

Before saving/finalizing an order, display a complete preview containing:

* Customer name
* Contact information
* Event details
* Event date
* Selected package/menu
* Ordered items
* Additional items/charges
* Subtotal
* Discounts, if applicable
* Total amount
* Down payment, if applicable
* Remaining balance
* Other relevant order information

Provide actions such as:

**Edit Order**
**Confirm Order**

The user should be able to go back and correct mistakes before confirming the order.

---

## 3. Billing Menu

The tablet should have a simple **Billing** menu.

The Billing menu should follow the same general billing behavior already used in the existing PC application.

The user should be able to:

* View the order amount
* View payment/down payment information
* Edit applicable billing information
* View remaining balance
* See the customer's payment status

The tablet does not need the full advanced billing management system of the PC. It only needs the functionality necessary to correctly create and record the order/billing information that will later be transferred to the PC.

---

## 4. Receipt Printing

After an order is confirmed, allow the user to **print the customer's receipt/order receipt** directly from the tablet.

The receipt should contain:

* Customer name
* Order/event information
* Ordered package/items
* Additional charges
* Total amount
* Payment/down payment
* Remaining balance
* Date/time
* Relevant receipt/order reference number

The printed receipt should clearly show what the customer ordered and how much the order costs.

---

## 5. Export Order/Data to PC

After completing the order on the tablet, provide an **Export** function.

The purpose is to transfer the tablet-created data to the main PC application.

The workflow should be:

**Create Order → Preview → Confirm → Print Receipt → Export**

The exported data must contain everything necessary for the PC to import the order correctly, including:

* Customer information
* Order information
* Package/menu
* Order items
* Additional charges
* Billing information
* Payment/down payment information
* Order status
* Relevant dates
* Unique identifiers
* Created/updated timestamps

The export format should be structured so the PC application can safely import and merge the records using the existing import/synchronization logic.

Do not make the tablet dependent on the PC being online while creating an order.

The tablet should be able to create and save orders locally, then export the data afterward.

---

# 6. Mandatory Rules Acknowledgement Before Ordering

Before an order can be finalized, require the customer/staff to acknowledge the **Catering Terms and Conditions / Rules**.

The user must explicitly agree before the system allows the order to be confirmed.

Example:

**Terms and Conditions**

[ ] I have read and understood the Catering Rules and Terms and Conditions.

The **Confirm Order** button must remain disabled until the checkbox is checked.

The system should record that the rules were acknowledged.

Store at minimum:

* Acknowledgement status
* Date/time acknowledged
* Order/customer reference
* Version of the Terms and Conditions that was accepted

This is important because the terms may change in the future. The system should know which version was accepted for each order.

---

## 7. Terms and Conditions Support

The complete Catering Terms and Conditions will be provided separately.

Once the Terms and Conditions are provided:

* Display them clearly during the order process.
* Make them readable on the tablet.
* Provide a checkbox confirming acknowledgement.
* Do not allow order confirmation without acknowledgement.
* Store the accepted Terms and Conditions version with the order.

Do not hard-code assumptions about the actual rules yet. Use the exact Terms and Conditions provided for the business.

---

# 8. Tablet UI Principles

The tablet UI should be optimized for touch interaction.

Use:

* Large buttons
* Large input fields
* Touch-friendly dropdowns
* Clear navigation
* Minimal unnecessary menus
* Simple order workflow
* Easy-to-read billing information

The tablet should be significantly simpler than the PC application.

The goal is:

**Fast customer ordering + accurate order capture + receipt + export to PC**

Not full business management.

---

# 9. Important Data Integrity Rules

Because the tablet will eventually transfer data to the PC:

* Every order must have a unique identifier.
* Every customer/order/payment record must have identifiable relationships.
* Exported data must not create duplicate orders when imported into the PC.
* The export must preserve the original order creation date/time.
* The export must preserve payment and billing information.
* Additional charges must remain identifiable.
* Terms and Conditions acknowledgement must remain attached to the correct order.
* The tablet must not overwrite existing PC financial records during import.
* The existing PC import conflict-resolution rules must still apply.

The tablet is an **order creation device**, while the PC remains the main management system.

---

# 10. Final Tablet Workflow

Implement the complete workflow as:

**Customer**
↓
**Create Order**
↓
**Select Package/Menu**
↓
**Add Items / Additional Charges**
↓
**Billing**
↓
**Order Preview**
↓
**Terms & Conditions**
↓
**☑ Acknowledge Rules**
↓
**Confirm Order**
↓
**Print Receipt**
↓
**Export to PC**

The order should only become finalized after the Terms and Conditions have been acknowledged.

Keep the implementation modular so the complete Terms and Conditions can be inserted later without redesigning the entire ordering workflow.

Do not add unrelated PC features to the tablet. Keep this application focused on **Customer + Order + Billing + Preview + Receipt + Terms Acknowledgement + Export**.


## 11. PC → Tablet Master Data Import

Add a feature that allows the owner/admin to **import the current master data from the PC application into the Tablet App**.

This is specifically intended to reduce setup and maintenance work.

The owner should not need to manually create all packages and menus again on every tablet.

### Data That Can Be Imported

The PC should be able to export the necessary master data for the tablet, including:

* Catering packages
* Menu items
* Package inclusions
* Menu categories
* Item prices
* Package prices
* Available/customizable options
* Additional-charge options, if applicable
* Other information required to display the ordering menu

The tablet should then import this data and update its local database.

### Example

PC currently contains:

**Packages**

* Package A – ₱15,000
* Package B – ₱20,000
* Package C – ₱25,000

**Menus**

* Chicken
* Pork
* Beef
* Fish
* Rice
* Desserts
* Drinks

The owner exports this information from the PC.

On the tablet:

**Import Master Data → Select File → Import**

The tablet should now show the same packages, menus, prices, and options without manually entering them again.

---

## 12. Master Data Import Rules

The import should be a **synchronization/update**, not a destructive replacement.

When importing new PC data:

* Existing valid tablet data should be updated when the PC version is newer.
* New packages/items should be added.
* Updated prices should replace old prices where appropriate.
* Removed/inactive packages should become unavailable for new orders without destroying historical orders.
* Existing tablet orders must not be changed just because a package or menu price was later updated.
* Historical orders must preserve the original item names and prices used when the order was created.

This is extremely important.

For example:

If Package A was ₱15,000 when Customer X ordered it, and the owner later changes Package A to ₱17,000 on the PC, importing the new master data must **not change Customer X's existing order from ₱15,000 to ₱17,000**.

Master data controls **future orders**. Historical orders retain their original values.

---

## 13. Recommended Tablet Order Flow

The tablet's main purpose is to make ordering fast and simple.

The intended workflow should be:

### Step 1 — Customer

Enter/select customer information.

### Step 2 — Package Selection

Display the packages imported from the PC.

The user selects the customer's desired package.

### Step 3 — Menu Selection

After selecting the package, display the menus/items available for that package.

The user can select the required menu choices.

For example:

**Package B**

Main Dish:

* Chicken BBQ
* Fried Chicken
* Pork Adobo

Side Dish:

* Chopsuey
* Vegetable Mix

Rice:

* Steamed Rice
* Java Rice

The exact available choices should come from the imported PC master data.

### Step 4 — Additional Items / Charges

Allow the user to add additional items or charges.

Examples:

* Additional lechon
* Menu change – ₱300
* Additional serving
* Extra service
* Other approved custom charges

Each addition must clearly show its description and amount.

### Step 5 — Billing

Calculate:

**Base Package Price**

* **Additional Items/Charges**
  − **Discounts**
  = **Final Order Total**

Then record applicable payment/down payment information.

### Step 6 — Order Preview

Show the complete order before final confirmation.

The customer/staff should be able to review:

* Customer
* Event
* Package
* Selected menus
* Additional items
* Additional charges
* Total
* Payment
* Remaining balance

Allow editing before final confirmation.

### Step 7 — Terms & Conditions

Display the business Terms and Conditions.

Require:

**☐ I acknowledge and agree to the Catering Terms and Conditions.**

The order cannot be finalized unless this is checked.

Record the acknowledgement with the order.

### Step 8 — Confirm Order

After acknowledgement, finalize the order and generate the unique order ID.

### Step 9 — Print Receipt

Print the customer's order receipt containing the final selected package, menus, additional charges, total, payment, and remaining balance.

### Step 10 — Export to PC

Export the completed order so it can later be imported into the main PC application.

---

## 14. Two-Way Data Flow

The system should have a clear distinction between **Master Data** and **Transaction Data**.

### PC → Tablet

Used for master data:

**PC**
→ Packages
→ Menus
→ Prices
→ Package options
→ Additional-charge options
→ **Export**

Then:

**Tablet**
→ **Import Master Data**
→ Update local menu/order selection database

### Tablet → PC

Used for completed transactions:

**Tablet**
→ Customers
→ Orders
→ Selected packages/menus
→ Additional charges
→ Billing
→ Payments
→ Terms acknowledgement
→ **Export**

Then:

**PC**
→ **Import Orders**
→ Merge into main system

The tablet should not become the main accounting/management database.

The **PC remains the primary source of truth for the business**, while the tablet is mainly an order-entry device.

---

## 15. Owner/Admin Setup

Add an easy workflow for the owner:

**On PC:**

`Export Tablet Master Data`

This generates a transfer file containing the latest packages, menus, prices, and related ordering information.

**On Tablet:**

`Import Master Data`

Select the exported file and import it.

After successful import, show a summary such as:

**Import Complete**

* 12 Packages
* 48 Menu Items
* 15 Additional Options
* 4 Updated Prices
* 3 New Items

This makes it easy for the owner to verify that the tablet received the correct data.

---

## 16. Important Separation

Do not mix the two import/export systems.

### Master Data Transfer

**PC → Tablet**

Used to update:

* Packages
* Menus
* Prices
* Options

### Order Data Transfer

**Tablet → PC**

Used to transfer:

* Customers
* Orders
* Selected menus
* Additional charges
* Billing
* Payments
* Terms acknowledgement

Both should have clear buttons and labels so the user cannot accidentally import the wrong type of data.

Use unique identifiers and version/timestamp information so the tablet can determine whether imported master data is newer than what it already has.

The goal is:

**Owner updates menu/package data once on the PC → exports master data → imports into tablet → tablet immediately uses the updated menu/package structure for new orders.**


## 17. IMPORTANT — Preserve the Existing Schema and System Architecture

The Tablet App is an additional client for the existing Jayraldine’s Catering System.

**Do NOT redesign, replace, or arbitrarily create a completely separate database structure.**

The implementation must continue following the **existing PC application's schema, relationships, naming conventions, identifiers, and business rules** wherever applicable.

### Schema Compatibility

Before implementing the Tablet App:

1. Inspect and understand the existing database schema.
2. Reuse existing entities/tables where they already represent the required data.
3. Reuse existing primary keys, foreign keys, relationships, and unique identifiers.
4. Do not create duplicate tables for data that already exists in the PC database unless there is a clear technical reason.
5. Any new tablet-specific tables must be introduced only when necessary and must integrate cleanly with the existing schema.
6. Preserve existing data types, relationships, and financial logic.
7. Do not rename or remove existing fields simply to make the tablet implementation easier.
8. Do not change existing working database behavior without a specific requirement.

### Existing PC System Remains the Reference

The PC application remains the primary reference for:

* Customer structure
* Order structure
* Package structure
* Menu structure
* Billing structure
* Payment structure
* Additional charges
* Ledger relationships
* User/account relationships
* Existing identifiers
* Existing business rules

The tablet must conform to these structures when creating and exporting transaction data.

### Master Data

For PC → Tablet synchronization, use the existing package/menu/master-data structure whenever possible.

The tablet should import the PC's existing:

* Packages
* Menus
* Package inclusions
* Prices
* Additional-item/options data
* Other required master data

Do not create a second unrelated version of the package/menu schema.

The tablet may maintain a **local copy/cache** of this data for offline operation, but the structure and identifiers must remain compatible with the PC system.

### Transaction Data

For Tablet → PC transfer, exported records must map directly to the existing PC schema.

The following must retain their correct relationships:

**Customer → Order → Order Items/Menu Selections → Additional Charges → Billing → Payments/Ledger**

Do not flatten these into a single generic record if the existing schema already stores them separately.

### Historical Data Protection

When importing or syncing master data:

* Updating a package price must not modify historical orders.
* Updating a menu must not modify previously confirmed orders.
* Deactivating a package must not delete historical order information.
* Historical transactions must retain the original values used at the time of ordering.

### Import/Export Compatibility

The export/import mechanism must use stable identifiers so that:

* Existing records can be matched correctly.
* Duplicate records are prevented.
* Existing payments are not overwritten.
* Existing PC billing status is not downgraded.
* Imported tablet orders can be linked to the correct customer and order records.
* Re-importing the same file does not create duplicate transactions.

### Critical Financial Rule

The tablet must follow the same financial/business rules as the PC.

Do not implement separate billing calculations that can produce different results.

The final billing result must remain consistent with the existing PC logic:

**Order Total + Additional Charges − Discounts − Valid Payments = Remaining Balance**

The status should be derived from the actual transaction/payment records rather than relying only on a manually stored status value.

### Local Tablet Database

Because the tablet needs to work independently while creating orders, it may use a local database.

However:

**Local database ≠ independent schema design.**

The local database should mirror the relevant existing schema or provide a clearly defined compatible local representation with a deterministic mapping back to the PC schema.

Every record that will eventually be exported must have the identifiers and relationships required for safe reconstruction in the PC database.

### Terms and Conditions

The Terms and Conditions acknowledgement must also be associated with the existing order structure.

Store:

* Order ID
* Terms version
* Acknowledgement status
* Acknowledged date/time
* User/customer reference when applicable

Do not attach the acknowledgement to an unrelated standalone record that cannot be traced back to the order.

### Before Coding

Before changing the database:

**First inspect the existing schema.**

Understand:

* Existing tables
* Columns
* Primary keys
* Foreign keys
* Constraints
* Existing relationships
* Existing payment/billing logic
* Existing import/export logic

Then extend the system using the **minimum schema changes necessary**.

### Final Rule

The Tablet App is an extension of the existing system, **not a replacement or a second unrelated system**.

The final architecture should preserve:

**Existing PC Schema**
↓
**PC Master Data Export**
↓
**Tablet Local Compatible Data**
↓
**Tablet Order Creation**
↓
**Tablet Transaction Export**
↓
**PC Import/Merge**
↓
**Existing Billing/Ledger System**

Any implementation that breaks the existing schema, creates duplicate representations of the same business data, or causes the tablet and PC to calculate/store different financial results is considered incorrect.


## 18. Customer Entry — New and Existing Customers

The tablet must support both **new customer registration** and **existing customer selection**, because the owner may hand the tablet directly to customers so they can fill out their own information.

### Customer Screen

The first step of the tablet ordering process should be a **Customer** screen with two options:

**[ New Customer ]**

and

**[ Existing Customer ]**

---

### New Customer

When the customer is new, allow them to enter their information directly on the tablet.

Required/appropriate fields should follow the existing PC customer schema.

For example:

* Full Name
* Contact Number
* Address
* Other customer information already required by the existing system

Do not invent unnecessary customer fields.

After the information is completed, continue to the Order screen.

The newly created customer must receive the appropriate unique identifier so that the record can later be exported to and inserted into the PC database without creating duplicate records.

---

### Existing Customer

Provide a search/select function for returning customers.

Allow searching using appropriate existing customer fields such as:

* Customer name
* Contact number
* Other existing searchable customer information

When an existing customer is selected:

* Do not create a duplicate customer.
* Reuse the existing customer ID.
* Create the new order under that customer.
* Preserve the existing customer information unless the workflow explicitly allows updating it.

---

## 19. Recommended Customer Data Flow

The preferred workflow is:

### New Customer

Tablet:

**New Customer**
↓
Customer fills out information
↓
Customer ID generated
↓
Create Order
↓
Preview
↓
Terms & Conditions
↓
Confirm
↓
Print Receipt
↓
Export to PC

### Existing Customer

Tablet:

**Existing Customer**
↓
Search Customer
↓
Select Customer
↓
Create New Order
↓
Preview
↓
Terms & Conditions
↓
Confirm
↓
Print Receipt
↓
Export to PC

---

## 20. Customer Synchronization Rule

Do not automatically import the entire PC customer database to every tablet unless specifically required.

The main tablet use case is customer self-entry during booking.

Therefore, the default data flow should be:

**PC → Tablet**

* Packages
* Menus
* Prices
* Ordering configuration

**Tablet → PC**

* New customers
* New orders
* Order items/menu selections
* Additional charges
* Billing/payment information
* Terms acknowledgement

This keeps the tablet lightweight and avoids unnecessary duplication of the entire customer database.

---

## 21. Duplicate Customer Protection

Before creating a new customer, perform a duplicate check using appropriate existing customer information.

For example, if the customer enters a contact number that already exists, show:

**“A customer with this contact information may already exist.”**

Then provide the option to:

**Use Existing Customer**

or

**Continue as New Customer**

The duplicate-checking logic must follow the existing database constraints and customer identification rules.

Do not rely only on the customer's name because multiple customers may have the same name.

---

## 22. Owner/Customer Self-Service Consideration

The tablet is intended to be handed directly to customers.

Therefore:

* Customer input fields must be large and touch-friendly.
* The flow should be simple enough for a customer to complete without staff assistance.
* Avoid exposing unnecessary admin functions.
* Do not allow customers to access PC management features.
* Keep the tablet focused on booking/order creation.

The owner/staff should still be able to access the necessary ordering controls.

The overall design should support:

**Owner hands tablet to customer → Customer enters information → Customer selects package/menu → Customer reviews order → Customer acknowledges rules → Order is confirmed → Receipt is printed → Order is exported to PC.**

---

## 23. Important Schema Rule

The customer implementation must still follow the **existing PC customer schema**.

Before implementing this feature:

* Inspect the existing customer table.
* Reuse its primary key/identifier structure.
* Reuse its existing fields.
* Preserve existing customer/order relationships.
* Do not create a separate incompatible customer model just for the tablet.

The tablet may maintain local customer data while offline, but exported customer records must map correctly to the existing PC customer structure.
