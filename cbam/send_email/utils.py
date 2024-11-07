import frappe
from frappe import _

def send_email_via_notification(employee_doc):
    tier_1_request_email_notification = frappe.get_cached_value("CBAM Settings", "CBAM Settings", "tier_1_request_email")

    if not tier_1_request_email_notification:
        frappe.throw(_("Please set Tier 1 Request Email in CBAM Settings"))

    notification  = frappe.get_doc("Notification", tier_1_request_email_notification)
    notification.send(employee_doc)