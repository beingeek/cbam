# Copyright (c) 2024, phamos GmbH and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class SupplierEmployee(Document):
	def before_validate(self):
		self.check_confirmation_checkbox()
		self.insert_supplier_company_if_from_web_form()

	def before_save(self):
		if self.is_data_confirmed == True:
			self.status = "Data confirmed by Employee"
		# self.rename()

	def after_insert(self):
		self.add_child()

	def on_update(self):
		self.update_child()

	def on_trash(self):
		self.delete_child()
		self.delete_link_in_good()

	def delete_child(self):
		if self.supplier_company:
			supplier_employees = frappe.get_doc("Supplier", self.supplier_company)
			for child in supplier_employees.employees:
				if child.employee_number == self.name: #not tested yet.
					child.delete()

	def delete_link_in_good(self):
		goods_list = frappe.get_all("Good", filters={"employee": self.name}, fields=["name"])
		for good in goods_list:
			frappe.db.set_value("Good", good, "employee", None)

	def add_child(self):
		supplier_employee = frappe.get_doc("Supplier", self.supplier_company)
		supplier_employee.append("employees", {
			"employee_number": self.name,
			"employee_last_name": self.last_name,
			"employee_email": self.email,
			"is_main_contact": self.is_main_contact
		})
		supplier_employee.save()

	def update_child(self):
		supplier_employee_items = frappe.get_all("Supplier Employee Item", filters={"parent": self.supplier_company}, fields=["employee_number"], pluck="employee_number")
		if self.name in supplier_employee_items:
		# 	new_supplier_employee_item = frappe.new_doc("Supplier Employee Item")
		# 	new_supplier_employee_item.employee_number = self.name
		# 	new_supplier_employee_item.parenttype = "Supplier"
		# 	new_supplier_employee_item.parentfield = "employees"
		# 	new_supplier_employee_item.parent = self.supplier_company
		# 	new_supplier_employee_item.save()
		# else:
			supplier = frappe.get_doc("Supplier", self.supplier_company)
			for employee in supplier.employees:
				if employee.employee_number == self.name:
					employee.employee_last_name = self.last_name
					employee.employee_email = self.email
					employee.is_main_contact = self.is_main_contact
			# supplier_employee_item = frappe.db.get_value("Supplier Employee Item", filters={"employee_number": self.name}, fields=["name"], pluck="name")
			# frappe.db.set_value("Supplier Employee Item", supplier_employee_item, "employee_last_name", self.last_name)
			# frappe.db.set_value("Supplier Employee Item", supplier_employee_item, "employee_email", self.email)
			# frappe.db.set_value("Supplier Employee Item", supplier_employee_item, "is_main_contact", self.is_main_contact)

	# def rename(self):
	# 	if self.name != f"EMP-{self.last_name}-{self.email}":
	# 		goods_list = frappe.get_all("Good", filters={"employee": self.name}, fields=["name"])
	# 		#frappe.throw("Rename if is running")
	# 		self.name = f"EMP-{self.last_name}-{self.email}"
	# 		self.save()
	# 		self.delete_child()
	# 		for good in goods_list:
	# 			frappe.db.set_value("Good", good, "employee", self.name)

	def is_supplier_user(self):
		user_email = frappe.session.user
		try:
			user = frappe.get_doc("User", user_email)
		except frappe.DoesNotExistError:
			frappe.throw(_("User not found"))
		roles = [role.role for role in user.roles]
		if "Supplier" in roles:
			return True
		else:
			return False

	def check_confirmation_checkbox(self):
		if self.status == "Sent to Supplier Employee" and self.is_supplier_user() and self.is_data_confirmed != True:
			frappe.throw("Please check the 'Data Confirmed' checkbox before submitting the form.")

	def insert_supplier_company_if_from_web_form(self):
		if self.is_supplier_user() and not self.supplier_company:
			user = frappe.session.user
			supplier_employee_docname = frappe.get_all('Supplier Employee', filters={'email': user}, fields=['name'])
			if supplier_employee_docname:
				supplier = frappe.get_value('Supplier Employee', supplier_employee_docname[0].name, 'supplier_company')
			else:
				frappe.throw("We couldn't find to which supplier you belong to. Please contact ...")
			self.supplier_company = supplier