from app import create_app
from flask import Flask, render_template

app = create_app()


@app.route('/')
def index():
    return render_template('index.html', message="Welcome to Live Flash Auctioning System")

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')


if __name__ == "__main__":
    app.run(debug=True)
