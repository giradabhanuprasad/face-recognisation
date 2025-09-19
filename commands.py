import click
from flask.cli import with_appcontext
from werkzeug.security import generate_password_hash  # Added for password hashing
from extensions import db
from models.user import User  # Assuming this is your Employee model
from models.attendance import Attendance  # Added explicit import
from flask_migrate import Migrate, upgrade
from datetime import datetime, timedelta

def init_app(app):
    """Register CLI commands with the Flask application."""
    app.cli.add_command(init_db_command)
    app.cli.add_command(create_admin_command)
    app.cli.add_command(reset_db_command)
    app.cli.add_command(create_test_data_command)

@click.command('init-db')
@with_appcontext
def init_db_command():
    """Initialize the database by creating all tables."""
    try:
        click.echo('Initializing database...')
        db.create_all()
        click.echo('Database initialized successfully.')
    except Exception as e:
        click.echo(f'Error initializing database: {str(e)}')
        raise

@click.command('create-admin')
@with_appcontext
def create_admin_command():
    """Create an admin user with provided credentials."""
    try:
        name = click.prompt('Enter admin name')  # Added name field
        email = click.prompt('Enter admin email')
        password = click.prompt('Enter admin password', hide_input=True, confirmation_prompt=True)
        
        if User.query.filter_by(email=email).first():
            click.echo('User with this email already exists.')
            return
        
        user = User(
            name=name,
            email=email,
            is_admin=True,
            role='admin'  # Added role field assuming it exists in model
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        click.echo('Admin user created successfully.')
    except Exception as e:
        db.session.rollback()
        click.echo(f'Error creating admin user: {str(e)}')

@click.command('reset-db')
@with_appcontext
def reset_db_command():
    """Reset the database by dropping all tables and recreating them."""
    if click.confirm('This will delete all data. Are you sure?'):
        try:
            click.echo('Dropping all tables...')
            db.drop_all()
            click.echo('Creating tables...')
            db.create_all()
            click.echo('Database reset successfully.')
        except Exception as e:
            click.echo(f'Error resetting database: {str(e)}')
            raise

