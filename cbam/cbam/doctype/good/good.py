# Copyright (c) 2024, phamos GmbH and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from cbam.send_email.create_email import create_email
from cbam.send_email.create_new_supplier_user import create_new_supplier_user

class Good(Document):
	def before_validate(self):
		self.set_confirmation_web_form_to_none()
		self.check_confirmation_checkbox()

	def validate(self):
		self.delete_old_employee_if_supplier_changed()
		self.get_main_contact_employee()
		self.reset_status_if_employee_changed()
		if self.is_data_confirmed == True and self.manufacture == "I am able to provide the emission data of this product":
			self.status = "Done"
		if self.manufacture == "The mass of this product needs to be split into several parts, due to shared responsibilities. I will assign the responsible parties" and not self.good_splitted:
			self.split_good()
		elif self.manufacture == "I am not able to provide emission data and will delegate this request":
			self.forward_goods()
		elif self.manufacture == "This item was not purchased from us. I want to reject this request back to the sender.":
			self.reject_goods()
		self.add_to_supplier_cht()
		self.add_to_employee_cht()
		self.add_to_customs_import_cht()

	def reject_goods(self):
		self.status = "Rejected"
		#send email alert to the owner of good
		self.send_email("Rejected")


	def forward_goods(self):
		self.forwarded_from_employee = self.employee
		if self.forward_to == "Another Supplier":
			self.forwarded_from_supplier = self.supplier
			self.supplier = self.forward_to_supplier
			self.set_main_contact()
			self.send_email("Another supplier is responsible")
		else:
			self.employee = self.forward_to_employee
			self.send_email("Another employee is responsible")
		self.status = "Sent for completing"
		self.forward_to_supplier = ""
		self.forward_to_employee = ""
		self.manufacture = "I am able to provide the emission data of this product"
		self.is_data_confirmed = False

	def on_trash(self):
		self.delete_all_good_item()

	def delete_old_employee_if_supplier_changed(self):
		has_supplier_changed = self.has_value_changed("supplier")
		is_employee_of_supplier = self.employee in frappe.get_all("Supplier Employee Item", {"parenttype": "Supplier", "parent": self.supplier, "parentfield": "employees"}, ["employee_number"], pluck="employee_number")
		if has_supplier_changed and not is_employee_of_supplier and not self.is_new():
			self.employee = None

	def get_main_contact_employee(self):
		if self.supplier and not self.employee:
			self.set_main_contact()

	def reset_status_if_employee_changed(self):
		if self.has_value_changed("employee") and not self.is_new():
			self.status = "Raw Data"

	def set_main_contact(self):
		supplier_doc = frappe.get_doc("Supplier", self.supplier)
		for child in supplier_doc.employees:
			if child.is_main_contact in ["1", 1, True]:
				main_contact = child.employee_number
				self.employee = main_contact

	def handle_total_raw_mass(self):
		total_raw_mass = sum(
			getattr(self, attr, 0) or 0
			for attr in [
				'split_raw_mass_1',
				'split_raw_mass_2',
				'split_raw_mass_3',
				'split_raw_mass_4',
				'split_raw_mass_5'
			]
		)
		if total_raw_mass != self.raw_mass:
			original_raw_mass = self.raw_mass

			frappe.throw(f"The raw mass total of the components is not equal to the raw mass of the original good. <br><br> The total should be {original_raw_mass}, not {total_raw_mass}. <br><br> Please change the raw masses of the components and ensure that they add up to a total of {original_raw_mass}.")

	def split_good(self):
		self.handle_total_raw_mass()
		for i in range(5):
			good_no = i+1
			if getattr(self, f"split_raw_mass_{good_no}") > 0:
				self.create_new_good_doc(good_no)

		self.status = "Split"
		self.good_splitted = 1

	def create_new_good_doc(self, good_no):
		new_good = frappe.new_doc("Good")
		new_good.status = "Sent for completing"
		new_good.parent_good = self.name
		new_good.hand_over_date = self.hand_over_date
		new_good.article_number = self.article_number
		new_good.invoice_number = self.invoice_number
		new_good.customs_tariff_number = self.customs_tariff_number
		new_good.good_description = self.good_description
		new_good.internal_customs_import_number = self.internal_customs_import_number
		new_good.country_of_origin = self.country_of_origin
		new_good.shipping_country = self.shipping_country
		new_good.customs_procedure = self.customs_procedure
		new_good.master_reference_number_mrn = self.master_reference_number_mrn + "-" + f"0{good_no-1}"
		new_good.raw_mass = getattr(self, f"split_raw_mass_{good_no}")
		responsiblity = getattr(self, f"responsibility_{good_no}")
		if responsiblity == "I'm the responsible Person":
			new_good.supplier = self.supplier
			new_good.employee = self.employee
		elif responsiblity == "Another employee is responsible":
			new_good.supplier = self.supplier
			new_good.employee = getattr(self, f"responsible_employee_{good_no}")
		elif responsiblity == "Another supplier is responsible":
			new_good.supplier = getattr(self, f"responsible_supplier_{good_no}")
		else:
			frappe.throw("Please select a responsibility")
		new_good.get_main_contact_employee()
		new_good.insert()

		self.append("good_components", {
			"good_number": new_good.name,
			"supplier": new_good.supplier,
			"employee": new_good.employee,
			"status": "Raw Data"
		})
		new_good.send_email(responsiblity)

	def add_to_supplier_cht(self):
		if self.has_value_changed("supplier") and not self.is_new():
			delete_good_item(self.name, "Supplier")
		if not frappe.db.exists("Good Item", {"good_number": self.name, "parenttype": "Supplier"}):
			supplier = frappe.get_doc("Supplier", self.supplier)
			supplier.append("goods", {
				"good_number": self.name,
				"supplier": self.supplier,
				"employee": self.employee,
				"status": self.status
			})
			supplier.save()
		else:
			self.update_good_items()

	def add_to_employee_cht(self):
		if self.has_value_changed("employee") and not self.is_new():
			delete_good_item(self.name, "Supplier Employee")
		if not frappe.db.exists("Good Item", {"good_number": self.name, "parenttype": "Supplier Employee"}):
			employee = frappe.get_doc("Supplier Employee", self.employee)
			employee.append("goods", {
				"good_number": self.name,
				"supplier": self.supplier,
				"employee": self.employee,
				"status": self.status
			})
			employee.save()
		else:
			self.update_good_items()

	def add_to_customs_import_cht(self):
		if self.has_value_changed("internal_customs_import_number") and not self.is_new():
			delete_good_item(self.name, "Customs Import")
		if not frappe.db.exists("Good Item", {"good_number": self.name, "parenttype": "Customs Import"}):
			customs_import = frappe.get_doc("Customs Import", self.internal_customs_import_number)
			customs_import.append("goods", {
				"good_number": self.name,
				"supplier": self.supplier,
				"employee": self.employee,
				"status": self.status
			})
			customs_import.save()
		else:
			self.update_good_items()

	def update_good_items(self):
		frappe.db.set_value("Good Item", {"good_number": self.name}, {
			"supplier": self.supplier,
			"employee": self.employee,
			"status": self.status
			})

	def delete_all_good_item(self):
		good_items = frappe.get_all("Good Item", filters={'good_number': self.name}, fields=["name"], pluck="name")
		for good_item in good_items:
			frappe.db.delete("Good Item", {
				"name": good_item
			})
		frappe.db.commit()

	def check_confirmation_checkbox(self):
		user_email = frappe.session.user
		try:
			user = frappe.get_doc("User", user_email)
		except frappe.DoesNotExistError:
			frappe.throw(_("User not found"))
		role_list = [r.role for r in user.roles]
		if "Supplier" in role_list and self.confirmation_web_form == "true" and self.is_data_confirmed != True:
			frappe.throw("Please check the 'Data Confirmed' checkbox before submitting the form.")

	def set_confirmation_web_form_to_none(self):
		has_value_changed = self.has_value_changed("confirmation_web_form")
		if not has_value_changed and self.confirmation_web_form:
			self.confirmation_web_form = None

	def send_email(self, responsiblity=None, employee=None):
		if responsiblity and responsiblity != "I'm the responsible Person":
			template = ""
			employee_email = frappe.db.get_value("Supplier Employee", self.employee, "email")
			user_exists = frappe.db.exists("User", employee_email)
			settings = frappe.get_single("CBAM Settings")

			if responsiblity == "Another employee is responsible":
				template = settings.tier_1_registered_employee_template
				if not user_exists:
					template = settings.tier_1_unregistered_employee_template
					create_new_supplier_user(self.employee)

			elif responsiblity == "Another supplier is responsible":
				template = settings.tier_n1_registered_template
				if not user_exists:
					create_new_supplier_user(self.employee)
					template = settings.tier_n1_unregistered_template
			elif responsiblity == "Rejected":
				template = settings.supplier_good_rejection_notification_template

			notification = frappe.get_doc("Notification", template)
			notification.send(self)




def delete_good_item(good, parenttype):
	good_item_list = frappe.get_all("Good Item", filters={'good_number': good, 'parenttype': parenttype}, fields=["name"], pluck="name")
	good_item = ', '.join(good_item_list)
	frappe.db.delete("Good Item", {
		"name": good_item
	})
	frappe.db.commit()
