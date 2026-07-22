import logging
import sys
from flask import Flask, render_template, abort, request, jsonify
from utils.database import get_db_pool
from Service import (
    PerformanceService,
    DividendService,
    LedgerService,
    UserNotFoundException,
    PortfolioDataError
)

# --- Logging Configuration ---
logging.basicConfig(stream=sys.stdout,
                    level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

# --- Database and Service Initialization ---
try:
    db_pool = get_db_pool()
    performance_service = PerformanceService(db_pool)
    dividend_service = DividendService(db_pool)
    ledger_service = LedgerService(db_pool)
    logging.info("Database pool connected and Modular Portfolio Services initialized successfully.")
except Exception as e:
    logging.critical(f"Application startup failed: Could not connect to database pool. Error: {e}")
    sys.exit("Exiting: Database connection failed.")


@app.after_request
def add_header(response):
    """Disable caching for dynamic routes to prevent stale data on reload."""
    if not request.path.startswith('/static/'):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    return response


@app.route('/', methods=['GET'])
def home():
    """Renders the home page displaying overall performance for all users in base VND."""
    try:
        users_performance = performance_service.get_overall_performance_data()
        
        # Aggregate hero statistics across all investors
        total_system_wealth = sum(u.get('total_asset', 0) for u in users_performance)
        total_system_investment = sum(u.get('total_investment', 0) for u in users_performance)
        total_system_profit = total_system_wealth - total_system_investment
        total_system_profit_pct = (total_system_profit / total_system_investment * 100) if total_system_investment > 0 else 0.0
        total_system_tax = ledger_service.get_total_tax()

        return render_template(
            'home.html',
            users_performance=users_performance,
            total_system_wealth=total_system_wealth,
            total_system_investment=total_system_investment,
            total_system_profit=total_system_profit,
            total_system_profit_pct=total_system_profit_pct,
            total_system_tax=total_system_tax
        )
    except Exception as e:
        logging.error(f"An error occurred on the home page: {e}")
        abort(500, description="An internal error occurred. Please try again later.")


@app.route('/user/<int:user_id>', methods=['GET'])
def portfolio(user_id):
    """Renders the 2-tier user profile page for a specific user in base VND."""
    try:
        payload = performance_service.get_user_profile_payload(
            user_id=user_id,
            dividend_service=dividend_service,
            ledger_service=ledger_service
        )
        return render_template('user_profile.html', **payload)

    except UserNotFoundException as e:
        logging.warning(f"Data not found for user_id {user_id}: {e}")
        abort(404, description=str(e))
    except PortfolioDataError as e:
        logging.error(f"A portfolio data error occurred for user_id {user_id}: {e}")
        abort(500, description="An internal error occurred while fetching portfolio data.")
    except Exception as e:
        logging.critical(f"An unexpected error occurred for user_id {user_id}: {e}", exc_info=True)
        abort(500, description="An unexpected internal error occurred.")


@app.route('/api/v1/user/<int:user_id>/ledger', methods=['GET'])
def get_user_ledger_api(user_id: int):
    """REST API endpoint returning JSON double-entry journal entries for expert view."""
    try:
        limit = request.args.get('limit', default=None, type=int)
        entries = ledger_service.get_user_journal_entries(user_id=user_id, limit=limit)
        return jsonify({"status": "success", "user_id": user_id, "journal_entries": entries})
    except Exception as e:
        logging.error(f"Failed to fetch ledger API for user_id {user_id}: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


# Custom Jinja2 filters
@app.template_filter('thousands')
def thousands_filter(value):
    """Formats a number with thousand separators (comma formatted)."""
    try:
        return "{:,.0f}".format(float(value))
    except (ValueError, TypeError):
        return value


@app.template_filter('compact_vnd')
def compact_vnd_filter(value):
    """Formats large monetary numbers concisely (e.g., 42.95M đ or 42,956,000 đ)."""
    try:
        val = float(value)
        if abs(val) >= 1_000_000:
            return f"{val / 1_000_000:,.2f} Tr"
        return f"{val:,.0f} đ"
    except (ValueError, TypeError):
        return value


if __name__ == '__main__':
    app.run(port=5000)
