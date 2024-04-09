from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import pytz
from datetime import datetime


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:changeme@localhost/database_name'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

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


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5555, host='0.0.0.0')

