import logging
import sys
from flask import Flask, render_template, abort
from utils.database import connect_db
from Service import PortfolioService, UserNotFoundException, PortfolioDataError

# --- Logging Configuration ---
# Log to standard output, which is captured by most hosting providers.
logging.basicConfig(stream=sys.stdout,
                    level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

# --- Database and Service Initialization ---
try:
    db = connect_db()
    service = PortfolioService(db)
    logging.info(
        "Database connected and PortfolioService initialized successfully.")
except Exception as e:
    logging.critical(
        f"Application startup failed: Could not connect to database. Error: {e}")
    # If the database isn't available on startup, the app can't run.
    sys.exit("Exiting: Database connection failed.")


@app.route('/', methods=['GET'])
def home():
    """Renders the home page displaying overall performance for all users."""
    try:
        users_performance = service.get_overall_performance_data()
        return render_template(
            'home.html',
            users_performance=users_performance
        )
    except Exception as e:
        logging.error(f"An error occurred on the home page: {e}")
        abort(500, description="An internal error occurred. Please try again later.")


@app.route('/user/<int:user_id>', methods=['GET'])
def portfolio(user_id):
    """Renders the portfolio page for a specific user."""
    try:
        # Fetch all necessary data from the service
        user = service.get_user_by_id(user_id=user_id)
        performance_data = service.get_user_performance_data(user_id=user_id)
        portfolio_data = service.get_portfolio_holdings_data(user_id=user_id)
        cash_balance = float(service.get_user_cash_balance(user_id=user_id))
        profit_data = service.get_profit_data(user_id)
        transaction_data = service.get_transaction_data(user_id)
        injection_data = service.get_injection_data(user_id)

        # --- Chart and Data Processing ---

        performance_data['total_investment'] = performance_data.get(
            'total_investment', 0) / 1000
        performance_data['total_asset'] = performance_data.get(
            'total_asset', 0) / 1000

        # Calculate stock values for the pie chart
        stock_values = {
            holding['stock_code']: holding['current_price'] *
            holding['current_quantity']
            for holding in portfolio_data
        }
        stock_values['Cash'] = cash_balance

        chart_labels = list(stock_values.keys())
        chart_data = list(stock_values.values())

        # Process profit data for the profit chart
        profit_chart_labels = [data['date'] for data in profit_data]
        profit_chart_total_asset = [data['total_asset']
                                    for data in profit_data]
        profit_chart_total_asset_bank = [
            data['total_asset_bank'] for data in profit_data]
        profit_chart_total_asset_index = [
            data['total_asset_index'] for data in profit_data]
        profit_chart_total_investment = [
            data['total_investment'] for data in profit_data]
        profit_chart_profit_percent = profit_data[-1]['profit_percent'] if profit_data else 0

        return render_template('user_profile.html',
                               performance_data=performance_data,
                               transaction_data=transaction_data,
                               injection_data=injection_data,
                               user=user,
                               portfolio_data=portfolio_data,
                               chart_labels=chart_labels,
                               chart_data=chart_data,
                               profit_chart_labels=profit_chart_labels,
                               profit_chart_total_asset=profit_chart_total_asset,
                               profit_chart_total_asset_bank=profit_chart_total_asset_bank,
                               profit_chart_total_asset_index=profit_chart_total_asset_index,
                               profit_chart_total_investment=profit_chart_total_investment,
                               profit_chart_profit_percent=profit_chart_profit_percent)

    except UserNotFoundException as e:
        logging.warning(f"Data not found for user_id {user_id}: {e}")
        abort(404, description=str(e))
    except PortfolioDataError as e:
        logging.error(
            f"A portfolio data error occurred for user_id {user_id}: {e}")
        abort(500, description="An internal error occurred while fetching portfolio data.")
    except Exception as e:
        logging.critical(
            f"An unexpected error occurred for user_id {user_id}: {e}", exc_info=True)
        abort(500, description="An unexpected internal error occurred.")


# Custom Jinja2 filter
@app.template_filter('thousands')
def thousands_filter(value):
    """Formats a number with thousand separators and no decimal places."""
    try:
        # Cast to float and format with a comma for thousands separation, and no decimal places.
        return "{:,.0f}".format(float(value))
    except (ValueError, TypeError):
        # Return original value if conversion or formatting fails
        return value


if __name__ == '__main__':
    # For development, you can set debug=True
    # app.run(debug=True)
    app.run()
