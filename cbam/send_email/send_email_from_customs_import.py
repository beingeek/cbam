import frappe
from cbam.send_email.create_email import create_email
from cbam.send_email.create_new_supplier_user import create_new_supplier_user
from cbam.send_email.update_good_item import update_good_items

import json

@frappe.whitelist()
def create_user_and_send_email(goods_list):
    all_goods = json.loads(goods_list)
    for item in all_goods:
        good = item['good_number']
        supplier = item['supplier']
        employee = frappe.db.get_value("Good", good, "employee")
        try:
            create_new_supplier_user(employee)
            # frappe.enqueue(create_email, queue='default', param1=employee)
            employee_doc = frappe.get_doc("Supplier Employee", employee)
            tier_1_request_email_notification = frappe.get_cached_value("CBAM Settings", "CBAM Settings", "tier_1_request_email")
            notification  = frappe.get_doc("Notification", tier_1_request_email_notification)
            notification.send(employee_doc)
            if frappe.db.get_value("Good", good, "status") == "Raw Data":
                frappe.db.set_value('Good', good, 'status', 'Sent for completing')
            frappe.db.set_value("Supplier Employee", employee, "status", "Sent to Supplier Employee")
            is_employee_main_contact = frappe.db.get_value('Supplier Employee', employee, 'is_main_contact')
            if is_employee_main_contact:
                frappe.db.set_value('Supplier', supplier, 'status', "Sent for confirmation")
            update_good_items(good, supplier, employee)
        except Exception as e:
            frappe.throw(f"Couldn't send Email. Please contact the System Administrator. <br><br>Error: {e}")
