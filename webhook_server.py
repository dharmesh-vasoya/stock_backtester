from flask import Flask, request, jsonify, redirect  # Add 'redirect' to the import statement
import requests

from flask_sqlalchemy import SQLAlchemy
import pytz
from datetime import datetime
import logging
# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:changeme@localhost/database_name'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

access_token = None

# Login API
@app.route('/login')
def login():
    global access_token
    if access_token is None:
        # Redirect to Upstox authentication page
        client_id = "5ff3dc0a-92d4-4018-8c07-f68e9d170bb5"
        redirect_uri = "https://lepidusdexter.in:5555/auth_callback"  # Update with your domain
        state = "optional-state-value"
        auth_url = f"https://api.upstox.com/v2/login/authorization/dialog?response_type=code&client_id={client_id}&redirect_uri={redirect_uri}"
        logger.debug("Redirecting to Upstox authentication page")
        return redirect(auth_url)
    else:
        return jsonify({'message': 'Already logged in'})

# Callback API
@app.route('/auth_callback')
def auth_callback():
    global access_token
    logger.debug("Received authentication callback")
    auth_code = request.args.get('code')
    client_id = "5ff3dc0a-92d4-4018-8c07-f68e9d170bb5"
    client_secret = "tfzgjybh6b"
    redirect_uri = "https://lepidusdexter.in:5555/auth_callback"  # Update with your domain

    token_url = "https://api.upstox.com/v2/login/authorization/token"
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    token_data = {
        "code": auth_code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code"
    }
    logger.debug("Sending POST request to token URL")
    logger.debug(f"Token data: {token_data}")
    response = requests.post(token_url, headers=headers, data=token_data)
    logger.debug(f"Response status code: {response.status_code}")
    logger.debug(f"Response text: {response.text}")

    # Check if the request was successful
    if response.status_code == 200:
        # Parse the JSON response
        access_token = response.json().get('access_token')
        logger.info("Access token received successfully")
        return jsonify({'access_token': access_token}), 200
    else:
        # If there was an error, return the error message
        error_message = f"Failed to generate access token. Status code: {response.status_code}"
        logger.error(error_message)
        return jsonify({'error': error_message}), response.status_code


@app.route('/get_reliance_ltp')
def get_reliance_ltp():
    global access_token
    if access_token is None:
        logger.error("Access token not available. Please log in first.")
        return jsonify({'error': 'Access token not available. Please log in first.'}), 401

    # Define the URL for LTP quotes API
    ltp_url = "https://api.upstox.com/v2/market-quote/quotes"

    # Instrument key for Reliance (Example, you might need to get the correct instrument key)
    instrument_key = "NSE_EQ|RELIANCE"

    # Set headers
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/json'
    }

    # Set query parameters
    params = {
        'instrument_key': instrument_key
    }

    # Make GET request to get LTP
    response = requests.get(ltp_url, headers=headers, params=params)

    logger.debug(f"Request URL: {response.url}")
    logger.debug(f"Response status code: {response.status_code}")
    logger.debug(f"Response text: {response.text}")

    if response.status_code == 200:
        ltp_data = response.json().get('data', {}).get(instrument_key, {})
        if ltp_data:
            ltp = ltp_data.get('last_price')
            logger.info(f"LTP for Reliance: {ltp}")
            return jsonify({'reliance_ltp': ltp}), 200
        else:
            logger.error("Failed to retrieve LTP data for Reliance.")
            return jsonify({'error': 'Failed to retrieve LTP data for Reliance.'}), 500
    else:
        logger.error(f"Failed to fetch LTP for Reliance. Status code: {response.status_code}")
        return jsonify({'error': 'Failed to fetch LTP for Reliance.'}), response.status_code



def to_epoch(time_string):
    # Get current time in IST
    ist_timezone = pytz.timezone('Asia/Kolkata')
    current_time = datetime.now(ist_timezone)

    # Parse the time string
    parsed_time = datetime.strptime(time_string, "%I:%M %p")

    # Update the parsed time with current date and IST timezone
    updated_time = current_time.replace(hour=parsed_time.hour, minute=parsed_time.minute, second=0, microsecond=0)

    # Convert updated time to epoch
    epoch_time = int(updated_time.timestamp())

    return epoch_time, updated_time.strftime("%Y-%m-%d %H:%M:%S %Z")


class BacktestData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    stock = db.Column(db.String(50), nullable=False)
    buy_price = db.Column(db.Float, nullable=False)
    sell_price = db.Column(db.Float)
    buy_time_human = db.Column(db.String(50), nullable=False)  # Human-readable time with IST date
    buy_time_epoch = db.Column(db.Integer, nullable=False)  # Epoch time
    sell_time_human = db.Column(db.String(50))  # Human-readable time with IST date
    sell_time_epoch = db.Column(db.Integer)  # Epoch time


@app.route('/webhook', methods=['POST'])
def webhook_receiver():
    try:
        data = request.json
        app.logger.debug(f"Received webhook data: {data}")

        scan_name = data.get('scan_name')
        app.logger.debug(f"Scan name: {scan_name}")

        if scan_name == 'Super Trend Buy':
            process_buy_signal(data)
        elif scan_name == 'Super Trend Sell':
            process_sell_signal(data)

        return jsonify({'message': 'Webhook received successfully'}), 200
    except Exception as e:
        app.logger.error(f"An error occurred: {e}")
        return jsonify({'error': str(e)}), 500

def process_buy_signal(data):
    with app.app_context():
        stocks = data.get('stocks').split(',')
        trigger_prices = [float(price) for price in data.get('trigger_prices').split(',')]
        buy_time = data.get('triggered_at')

        for stock, price in zip(stocks, trigger_prices):
            app.logger.debug(f"Processing buy signal for stock: {stock}, price: {price}, time: {buy_time}")
            buy_epoch_time, buy_human_time = to_epoch(buy_time)
            buy_entry = BacktestData(stock=stock, buy_price=price, buy_time_human=buy_human_time, buy_time_epoch=buy_epoch_time)
            db.session.add(buy_entry)
            db.session.commit()
            app.logger.debug(f"Buy entry added to database")

def process_sell_signal(data):
    with app.app_context():
        stocks = data.get('stocks').split(',')
        sell_prices = [float(price) for price in data.get('trigger_prices').split(',')]
        sell_time = data.get('triggered_at')

        for stock, sell_price in zip(stocks, sell_prices):
            app.logger.debug(f"Processing sell signal for stock: {stock}, price: {sell_price}, time: {sell_time}")
            sell_epoch_time, sell_human_time = to_epoch(sell_time)
            sell_entry = BacktestData.query.filter_by(stock=stock, sell_price=None).first()
            if sell_entry:
                sell_entry.sell_price = sell_price
                sell_entry.sell_time_human = sell_human_time
                sell_entry.sell_time_epoch = sell_epoch_time
                db.session.commit()
                app.logger.debug(f"Sell entry updated in database")


def start_flask_app():
    #app.run(debug=True, port=5555, host='0.0.0.0')
    app.run(debug=True, port=5555, host='0.0.0.0', ssl_context=('fullchain.pem', 'privkey.pem'))


if __name__ == '__main__':
    start_flask_app()
