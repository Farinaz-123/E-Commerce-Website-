from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, IntegerField, TextAreaField, SelectField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError, NumberRange, Optional
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

class LoginForm(FlaskForm):
    """Form for user login"""
    username = StringField('Username', validators=[
        DataRequired(message='Username is required'),
        Length(min=3, max=20, message='Username must be between 3 and 20 characters')
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message='Password is required'),
        Length(min=6, message='Password must be at least 6 characters')
    ])
    submit = SubmitField('Login')

class RegisterForm(FlaskForm):
    """Form for user registration"""
    username = StringField('Username', validators=[
        DataRequired(message='Username is required'),
        Length(min=3, max=20, message='Username must be between 3 and 20 characters')
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message='Password is required'),
        Length(min=6, message='Password must be at least 6 characters')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(message='Please confirm your password'),
        EqualTo('password', message='Passwords must match')
    ])
    submit = SubmitField('Register')
    
    def validate_username(self, username):
        """Check if username already exists"""
        conn = sqlite3.connect('database.db')
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username.data,)).fetchone()
        conn.close()
        if user:
            raise ValidationError('Username already taken. Please choose a different one.')

class ReviewForm(FlaskForm):
    """Form for product reviews"""
    rating = SelectField('Rating', choices=[
        ('5', '⭐⭐⭐⭐⭐ Excellent'),
        ('4', '⭐⭐⭐⭐ Very Good'),
        ('3', '⭐⭐⭐ Good'),
        ('2', '⭐⭐ Fair'),
        ('1', '⭐ Poor')
    ], validators=[DataRequired(message='Please select a rating')])
    
    comment = TextAreaField('Your Review', validators=[
        DataRequired(message='Please write a review'),
        Length(min=10, max=500, message='Review must be between 10 and 500 characters')
    ])
    submit = SubmitField('Submit Review')

class UpdateProfileForm(FlaskForm):
    """Form for updating user profile"""
    username = StringField('New Username', validators=[
        Optional(),
        Length(min=3, max=20, message='Username must be between 3 and 20 characters')
    ])
    current_password = PasswordField('Current Password')
    new_password = PasswordField('New Password', validators=[
        Optional(),
        Length(min=6, message='Password must be at least 6 characters')
    ])
    confirm_new_password = PasswordField('Confirm New Password', validators=[
        Optional(),
        EqualTo('new_password', message='Passwords must match')
    ])
    submit = SubmitField('Update Profile')

class AddProductForm(FlaskForm):
    """Form for adding new products (Admin)"""
    name = StringField('Product Name', validators=[
        DataRequired(message='Product name is required'),
        Length(min=3, max=100, message='Product name must be between 3 and 100 characters')
    ])
    price = IntegerField('Price (in ₹)', validators=[
        DataRequired(message='Price is required'),
        NumberRange(min=1, message='Price must be greater than 0')
    ])
    description = TextAreaField('Description', validators=[
        DataRequired(message='Description is required'),
        Length(min=10, max=1000, message='Description must be between 10 and 1000 characters')
    ])
    category = StringField('Category', validators=[
        DataRequired(message='Category is required'),
        Length(min=2, max=50, message='Category must be between 2 and 50 characters')
    ])
    stock = IntegerField('Stock Quantity', validators=[
        DataRequired(message='Stock quantity is required'),
        NumberRange(min=0, message='Stock cannot be negative')
    ])
    image = FileField('Product Image', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'gif'], message='Only image files are allowed'),
        DataRequired(message='Please select an image')
    ])
    submit = SubmitField('Add Product')

class EditProductForm(FlaskForm):
    """Form for editing products (Admin)"""
    name = StringField('Product Name', validators=[
        DataRequired(message='Product name is required'),
        Length(min=3, max=100, message='Product name must be between 3 and 100 characters')
    ])
    price = IntegerField('Price (in ₹)', validators=[
        DataRequired(message='Price is required'),
        NumberRange(min=1, message='Price must be greater than 0')
    ])
    description = TextAreaField('Description', validators=[
        DataRequired(message='Description is required'),
        Length(min=10, max=1000, message='Description must be between 10 and 1000 characters')
    ])
    category = StringField('Category', validators=[
        DataRequired(message='Category is required'),
        Length(min=2, max=50, message='Category must be between 2 and 50 characters')
    ])
    stock = IntegerField('Stock Quantity', validators=[
        DataRequired(message='Stock quantity is required'),
        NumberRange(min=0, message='Stock cannot be negative')
    ])
    image = FileField('Product Image', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'gif'], message='Only image files are allowed'),
        Optional()
    ])
    submit = SubmitField('Update Product')

class SearchForm(FlaskForm):
    """Form for product search"""
    search_query = StringField('Search Products', validators=[
        Length(min=1, max=100, message='Search query must be between 1 and 100 characters')
    ])
    submit = SubmitField('Search')
