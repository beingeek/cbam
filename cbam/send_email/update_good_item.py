import frappe

def update_good_items(good, supplier, employee):
    frappe.db.set_value("Good Item", {"good_number": good}, {
        "supplier": supplier,
        "employee": employee,
        "status": "Sent for completing"
        })