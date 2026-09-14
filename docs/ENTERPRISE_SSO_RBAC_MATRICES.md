# Role-Based Access Control (RBAC) Permission Matrix

## 1. Permission Roles
| Module / Capability | Administrator | Manager | Cashier / Staff | Kitchen Crew |
| :--- | :---: | :---: | :---: | :---: |
| **View Dashboard & Bookings** | Yes | Yes | Yes | View-Only |
| **Create & Modify Bookings** | Yes | Yes | Yes | No |
| **Process Billing & Invoices** | Yes | Yes | Yes | No |
| **Override Prices & Discounts** | Yes | Owner PIN | No | No |
| **Export Database & Financials** | Yes | Owner PIN | No | No |
| **Database Connection Config** | Yes | No | No | No |
