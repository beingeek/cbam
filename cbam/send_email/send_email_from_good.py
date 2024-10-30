import frappe
from cbam.send_email.create_email import create_email
from cbam.send_email.create_new_supplier_user import create_new_supplier_user
from cbam.send_email.update_good_item import update_good_items
from frappe.core.doctype.communication.email import make
import json

@frappe.whitelist()
def send_email(good):
    supplier = frappe.db.get_value('Good', good, 'supplier')
    employee = frappe.db.get_value("Good", good, "employee")
    try:
        create_new_supplier_user(employee)
        create_email(employee)
        employee_doc = frappe.get_doc("Supplier Employee", employee)
        frappe.db.set_value("Supplier Employee", employee, "status", "Sent to Supplier Employee")
        for good in employee_doc.goods:
            if good.status == "Raw Data":
                frappe.db.set_value('Good', good.good_number, 'status', 'Sent for completing')
            update_good_items(good.good_number, supplier, employee)
        if employee_doc.is_main_contact:
            frappe.db.set_value('Supplier', supplier, 'status', "Sent for confirmation")
    except Exception as e:
        frappe.throw(f"Couldn't send Email. Please contact the System Administrator. <br><br>Error: {e}")
