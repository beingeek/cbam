# Copyright (c) 2024, phamos GmbH and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import uuid
from frappe.utils import cstr

class CBAMOperatingCompany(Document):
	def before_naming(self):
		self.generated_uuid()

	def validate(self):
		self.set_parent_supplier()
		# self._create_new_employee()

	# def _create_new_employee(self):
	# 	if not self.contact_person_employee:
	# 		contact_person = frappe.db.get_value("Supplier Employee", {"email": self.email}, "name")
	# 		if not contact_person:
	# 			contact_person_doc = frappe.new_doc("Supplier Employee")
	# 			contact_person_doc.supplier_company = self.parent_supplier
	# 			contact_person_doc.first_name = self.first_name
	# 			contact_person_doc.last_name = self.last_name
	# 			contact_person_doc.phone_number = self.phone_number
	# 			contact_person_doc.email = self.email
	# 			contact_person_doc.position = self.position_in_the_company
	# 			contact_person_doc.save()
	# 			contact_person = contact_person_doc.name
	# 		self.contact_person_employee = contact_person

	def generated_uuid(self):
		self.uuid = cstr(uuid.uuid4())

	def check_if_user_supplieruser(self):
		user_email = frappe.session.user
		try:
			user = frappe.get_doc("User", user_email)
		except frappe.DoesNotExistError:
			frappe.throw(_("User not found"))
		role_list = [r.role for r in user.roles]
		if "Supplier" in role_list:
			employee_list = frappe.get_all("Supplier Employee", filters={"email": user_email}, fields=["name"], pluck="name")
			if not employee_list:
				frappe.throw("You are not registered as an employee of a supplier. Please login with another user.")
				return False, []
			elif len(employee_list) > 1:
				frappe.throw("You are registered as an employee of more than one supplier. Please contact the system administrator.")
				return False, []
			else:
				return True, employee_list
		else:
			frappe.msgprint("You are not registered as a supplier. Be aware that the Parent Supplier Field will not be filled out automatically. If you have chosen 'Same contact person', please change to 'Different contact person' as the contact person has to be filled out manually.")
			return False, []

	def set_parent_supplier(self):
		is_user_supplier, employee_list = self.check_if_user_supplieruser()
		if is_user_supplier and not self.parent_supplier == "":
			try:
				supplier = frappe.db.get_value("Supplier Employee", employee_list[0], "supplier_company")
				self.parent_supplier = supplier
			except frappe.DoesNotExistError:
				frappe.throw("Supplier not found")
