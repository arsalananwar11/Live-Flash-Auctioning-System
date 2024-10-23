from flask import Blueprint, render_template
from app.services.main_service import MainService

main = Blueprint('main', __name__)

@main.route('/')
def index():
    message = MainService().get_message()
    return render_template('index.html', message=message)

@main.route('/status')
def status():
    message = MainService().get_message("The system is live and responding to requests!")
    return render_template('index.html', message=message)