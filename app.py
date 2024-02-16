from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from datetime import datetime
import re
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity
import pytest

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
app.config['JWT_SECRET_KEY'] = 'super-secret'  # Change this to a secure random key in production
db = SQLAlchemy(app)
jwt = JWTManager(app)

# Define Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    clients = relationship("ClientUser", back_populates="user")

class Company(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    employees = db.Column(db.Integer, nullable=False)
    users = relationship("User", back_populates="company")

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    user = relationship("User", back_populates="clients")
    company = relationship("Company", back_populates="clients")

class ClientUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = db.Column(db.DateTime)
    active = db.Column(db.Boolean, nullable=False, default=True)
    client = relationship("Client", back_populates="users")
    user = relationship("User", back_populates="clients")

# Define Endpoints
@app.route('/users', methods=['GET'])
def get_users():
    username = request.args.get('username')
    if username:
        users = User.query.filter_by(username=username).all()
    else:
        users = User.query.all()
    return jsonify([{'id': user.id, 'username': user.username, 'email': user.email} for user in users])

@app.route('/users', methods=['POST'])
def create_user():
    data = request.json
    new_user = User(username=data['username'], email=data['email'])
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'message': 'User created successfully'}), 201

@app.route('/clients', methods=['POST'])
@jwt_required()
def create_client():
    current_user = get_jwt_identity()
    if current_user['role'] != 'ROLE_ADMIN':
        return jsonify({'error': 'Only ROLE_ADMIN users can create clients'}), 403

    data = request.json
    # Validate company is not taken by other client
    existing_client = Client.query.filter_by(company_id=data['company_id']).first()
    if existing_client:
        return jsonify({'error': 'Company already taken by another client'}), 400
    
    new_client = Client(name=data['name'], email=data['email'], phone=data['phone'],
                        user_id=data['user_id'], company_id=data['company_id'])
    db.session.add(new_client)
    db.session.commit()
    return jsonify({'message': 'Client created successfully'}), 201

@app.route('/companies', methods=['GET'])
def get_companies():
    companies = Company.query.all()
    return jsonify([{'id': company.id, 'name': company.name, 'employees': company.employees} for company in companies])

# Custom SQL Queries
def find_companies_by_employee_range(min_employees, max_employees):
    return Company.query.filter(Company.employees.between(min_employees, max_employees)).all()

def find_clients_by_user(user_id):
    return Client.query.join(ClientUser).filter(ClientUser.user_id == user_id).all()

def find_clients_by_name(name):
    return Client.query.join(Company).filter(Company.name.like(f'%{name}%')).all()

def max_revenue_companies_by_industry():
    query = """
            SELECT c.* 
            FROM company c
            JOIN (
                SELECT industry, MAX(revenue) AS max_revenue
                FROM company
                GROUP BY industry
            ) max_rev ON c.industry = max_rev.industry AND c.revenue = max_rev.max_revenue
            """
    return db.session.execute(query).fetchall()

# Email Validation Regex
def validate_email(email):
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return False
    return True

# Unit and Functional Tests
@pytest.mark.parametrize("min_employees, max_employees", [(500, 2000)])
def test_find_companies_by_employee_range(min_employees, max_employees):
    companies = find_companies_by_employee_range(min_employees, max_employees)
    assert companies is not None

def test_role_user_cannot_create_user():
    # Write your test logic here
    pass

def test_client_creation():
    # Write your test logic here
    pass

def test_max_revenue_companies_by_industry():
    companies = max_revenue_companies_by_industry()
    assert any(company.name == 'Amazon' for company in companies)
    assert any(company.name == 'Google' for company in companies)





# Documentation
"""
### Endpoints Documentation

- **GET /users**
  - Description: Get a list of users. Can be filtered by username.
  - Parameters:
    - username (optional): Filter users by username.
  - Returns: List of users.

- **POST /users**
  - Description: Create a new user.
  - Request Body:
    - username: Username of the new user.
    - email: Email of the new user.
  - Returns: Success message.

- **POST /clients**
  - Description: Create a new client. Only accessible by ROLE_ADMIN users.
  - Request Body:
    - name: Name of the client.
    - email: Email of the client.
    - phone: Phone number of the client.
    - user_id: ID of the user associated with the client.
    - company_id: ID of the company associated with the client.
  - Returns: Success message or error if company is already taken.

- **GET /companies**
  - Description: Get a list of companies.
  - Returns: List of companies.

- **Custom SQL Queries**
  - find_companies_by_employee_range(min_employees, max_employees): Find companies by employees range.
  - find_clients_by_user(user_id): Find clients by user.
  - find_clients_by_name(name): Find clients by name.
  - max_revenue_companies_by_industry(): Find companies with max revenue in their industry.
"""

if __name__ == '__main__':
    app.run(debug=True)
