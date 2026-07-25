from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, FloatField, IntegerField, TextAreaField, DateField, FileField
from wtforms.validators import DataRequired, Email, Length, Optional, EqualTo

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=4)])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class ForgotPasswordForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email Address', validators=[DataRequired(), Email()])
    submit = SubmitField('Request Password Reset')

class UserForm(FlaskForm):
    employee_id = StringField('Employee ID', validators=[DataRequired(), Length(max=50)])
    name = StringField('Employee Name', validators=[DataRequired(), Length(max=120)])
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    password = PasswordField('Password', validators=[Optional(), Length(min=4)])
    email = StringField('Email', validators=[Optional(), Email(), Length(max=120)])
    mobile = StringField('Mobile Number', validators=[Optional(), Length(max=15)])
    role = SelectField('Role', choices=[
        ('Admin', 'Admin'),
        ('Manager', 'Manager'),
        ('Cashier', 'Cashier'),
        ('Waiter', 'Waiter'),
        ('Kitchen', 'Kitchen'),
        ('Store Manager', 'Store Manager')
    ], validators=[DataRequired()])
    status = SelectField('Status', choices=[('Active', 'Active'), ('Disabled', 'Disabled')], default='Active')
    shift = SelectField('Shift', choices=[('Day', 'Day (8 AM - 4 PM)'), ('Evening', 'Evening (4 PM - 12 AM)'), ('Night', 'Night (12 AM - 8 AM)')], default='Day')
    joining_date = DateField('Joining Date', format='%Y-%m-%d', validators=[Optional()])
    photo = FileField('Profile Photo')
    fingerprint_enabled = BooleanField('Enable Biometric Fingerprint (WebAuthn)')
    submit = SubmitField('Save User')

class ExpenseForm(FlaskForm):
    date = DateField('Date', format='%Y-%m-%d', validators=[DataRequired()])
    vendor = StringField('Vendor/Supplier', validators=[Optional(), Length(max=120)])
    invoice_number = StringField('Invoice Number', validators=[Optional(), Length(max=100)])
    category = SelectField('Category', choices=[
        ('Milk', 'Milk'),
        ('Vegetable', 'Vegetable'),
        ('Rice', 'Rice'),
        ('Oil', 'Oil'),
        ('Gas', 'Gas'),
        ('Sweet', 'Sweet'),
        ('Bakery', 'Bakery'),
        ('Cleaning', 'Cleaning'),
        ('Salary', 'Salary'),
        ('Transport', 'Transport'),
        ('Others', 'Others')
    ], validators=[DataRequired()])
    product_name = StringField('Product/Service Name', validators=[DataRequired(), Length(max=150)])
    quantity = FloatField('Quantity', default=0.0, validators=[Optional()])
    unit = SelectField('Unit', choices=[('Kg', 'Kg'), ('Litre', 'Litre'), ('Pcs', 'Pcs'), ('Pkts', 'Pkts'), ('Others', 'Others')], default='Kg')
    rate = FloatField('Rate', default=0.0, validators=[Optional()])
    gst = FloatField('GST Amount', default=0.0, validators=[Optional()])
    discount = FloatField('Discount Amount', default=0.0, validators=[Optional()])
    final_amount = FloatField('Final Amount', validators=[DataRequired()])
    payment_mode = SelectField('Payment Mode', choices=[('Cash', 'Cash'), ('UPI', 'UPI'), ('Card', 'Card'), ('Net Banking', 'Net Banking')], default='Cash')
    remarks = TextAreaField('Remarks', validators=[Optional()])
    bill_photo = FileField('Upload Bill/Receipt Photo')
    submit = SubmitField('Submit Expense')

class SupplierForm(FlaskForm):
    name = StringField('Supplier Name', validators=[DataRequired(), Length(max=120)])
    gst_number = StringField('GST Number', validators=[Optional(), Length(max=15)])
    phone = StringField('Phone', validators=[Optional(), Length(max=15)])
    email = StringField('Email', validators=[Optional(), Email(), Length(max=120)])
    address = TextAreaField('Address', validators=[Optional()])
    outstanding_balance = FloatField('Outstanding Balance', default=0.0)
    submit = SubmitField('Save Supplier')

class ProductForm(FlaskForm):
    name = StringField('Product Name', validators=[DataRequired(), Length(max=120)])
    code = StringField('Product Code', validators=[DataRequired(), Length(max=50)])
    barcode = StringField('Barcode (Optional)', validators=[Optional(), Length(max=100)])
    category_id = SelectField('Category', coerce=int, validators=[DataRequired()])
    purchase_price = FloatField('Purchase Price', validators=[DataRequired()])
    selling_price = FloatField('Selling Price', validators=[DataRequired()])
    gst_percent = FloatField('GST %', default=0.0)
    supplier_id = SelectField('Supplier', coerce=int, validators=[Optional()])
    current_stock = FloatField('Current Stock', default=0.0)
    min_stock = FloatField('Minimum Stock/Alert', default=10.0)
    max_stock = FloatField('Maximum Stock Limit', default=100.0)
    unit = SelectField('Unit', choices=[('Kg', 'Kg'), ('Litre', 'Litre'), ('Pcs', 'Pcs'), ('Pkts', 'Pkts')], default='Kg')
    description = TextAreaField('Description', validators=[Optional()])
    photo = FileField('Product Image')
    storage_location = StringField('Storage Location (e.g., Cold Room)', validators=[Optional(), Length(max=100)])
    expiry_date = DateField('Expiry Date', format='%Y-%m-%d', validators=[Optional()])
    submit = SubmitField('Save Product')

class MenuItemForm(FlaskForm):
    name = StringField('Item Name', validators=[DataRequired(), Length(max=120)])
    code = StringField('Item Code', validators=[DataRequired(), Length(max=50)])
    category = SelectField('Category', choices=[
        ('Breakfast', 'Breakfast'),
        ('Lunch', 'Lunch'),
        ('Dinner', 'Dinner'),
        ('Snacks', 'Snacks'),
        ('Sweets', 'Sweets'),
        ('Cold Drinks', 'Cold Drinks'),
        ('Fast Food', 'Fast Food')
    ], validators=[DataRequired()])
    gst_percent = FloatField('GST %', default=5.0)
    price = FloatField('Price (Base)', validators=[DataRequired()])
    image = FileField('Food Image')
    description = TextAreaField('Description', validators=[Optional()])
    status = SelectField('Status', choices=[('Available', 'Available'), ('Out of Stock', 'Out of Stock')], default='Available')
    submit = SubmitField('Save Menu Item')

class RestaurantTableForm(FlaskForm):
    table_number = StringField('Table Number/Name', validators=[DataRequired(), Length(max=20)])
    capacity = IntegerField('Seating Capacity', default=4, validators=[DataRequired()])
    status = SelectField('Status', choices=[
        ('Vacant', 'Vacant (Green)'),
        ('Occupied', 'Occupied (Red)'),
        ('Preparing', 'Preparing (Orange)'),
        ('Ready', 'Ready (Yellow)'),
        ('Billing', 'Billing (Purple)'),
        ('Paid', 'Paid (Blue)')
    ], default='Vacant')
    submit = SubmitField('Save Table')

class CustomerForm(FlaskForm):
    name = StringField('Customer Name', validators=[DataRequired(), Length(max=120)])
    phone = StringField('Phone/Mobile', validators=[DataRequired(), Length(min=10, max=15)])
    birthday = DateField('Birthday', format='%Y-%m-%d', validators=[Optional()])
    address = TextAreaField('Address', validators=[Optional()])
    loyalty_points = IntegerField('Loyalty Points', default=0)
    submit = SubmitField('Save Customer')
