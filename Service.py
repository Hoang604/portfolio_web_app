from model.User import User
import mysql.connector
from mysql.connector.pooling import MySQLConnectionPool
import logging
from typing import Optional, Union, Generator
from contextlib import contextmanager

# Custom Exceptions
class UserNotFoundException(Exception):
    pass


class PortfolioDataError(Exception):
    pass


class PerformanceService:
    """Deep module handling overall portfolio performance aggregation in base VND."""

    def __init__(self, db_or_pool: Union[mysql.connector.MySQLConnection, MySQLConnectionPool]):
        self.db_or_pool = db_or_pool

    @contextmanager
    def _get_connection(self) -> Generator[mysql.connector.MySQLConnection, None, None]:
        if isinstance(self.db_or_pool, MySQLConnectionPool):
            conn = self.db_or_pool.get_connection()
            try:
                yield conn
            finally:
                conn.close()
        else:
            yield self.db_or_pool

    def get_user_performance_view(self, user: User) -> dict:
        """Calculates a user's core performance data using exact VND values without 1000x multipliers."""
        if not user.id:
            logging.warning("Attempted to get overall performance for a user without an ID.")
            return {}

        sql_query = """
            SELECT
                u.id AS user_id,
                u.name,
                u.cash_balance,
                COALESCE(SUM(ph.current_quantity * latest_prices.price), 0) AS total_current_value
            FROM
                portfolio_user u
            LEFT JOIN
                portfolio_portfolioholding ph ON u.id = ph.user_id AND ph.current_quantity > 0
            LEFT JOIN
                (
                    SELECT stock_id, price
                    FROM (
                        SELECT
                            stock_id,
                            price,
                            ROW_NUMBER() OVER(PARTITION BY stock_id ORDER BY date DESC) as rn
                        FROM portfolio_stockprice
                        WHERE stock_id IN (
                            SELECT DISTINCT stock_id FROM portfolio_portfolioholding WHERE user_id = %s AND current_quantity > 0
                        )
                    ) AS ranked_prices
                    WHERE rn = 1
                ) AS latest_prices ON ph.stock_id = latest_prices.stock_id
            WHERE
                u.id = %s
            GROUP BY
                u.id, u.name, u.cash_balance;"""

        try:
            with self._get_connection() as conn:
                with conn.cursor(dictionary=True) as cursor:
                    cursor.execute(sql_query, (user.id, user.id))
                    result = cursor.fetchone()
                    return result if result else {}
        except mysql.connector.Error as err:
            logging.error(f"Database error while getting overall performance for User {user.name}: {err}")
            raise PortfolioDataError(f"Could not retrieve overall performance for User {user.name}") from err

    def get_user_portfolio_holdings(self, user: User) -> list:
        """Retrieves detailed portfolio holdings in base VND."""
        if not user.id:
            return []

        sql_query = """
            SELECT
                s.code AS stock_code,
                s.company_name,
                ph.current_quantity,
                ph.average_cost,
                latest_prices.price AS current_price,
                (ph.current_quantity * (latest_prices.price - ph.average_cost)) AS total_profit_in_cash,
                CASE
                    WHEN ph.average_cost > 0 THEN ((latest_prices.price - ph.average_cost) / ph.average_cost) * 100
                    ELSE 0
                END AS total_profit_in_percentage
            FROM
                portfolio_portfolioholding ph
            JOIN
                portfolio_stock s ON ph.stock_id = s.code
            LEFT JOIN
                (
                    SELECT stock_id, price
                    FROM (
                        SELECT
                            stock_id,
                            price,
                            ROW_NUMBER() OVER(PARTITION BY stock_id ORDER BY date DESC) as rn
                        FROM portfolio_stockprice
                        WHERE stock_id IN (
                            SELECT DISTINCT stock_id FROM portfolio_portfolioholding WHERE user_id = %s AND current_quantity > 0
                        )
                    ) AS ranked_prices
                    WHERE rn = 1
                ) AS latest_prices ON ph.stock_id = latest_prices.stock_id
            WHERE
                ph.user_id = %s AND ph.current_quantity > 0
            ORDER BY
                s.code;"""

        try:
            with self._get_connection() as conn:
                with conn.cursor(dictionary=True) as cursor:
                    cursor.execute(sql_query, (user.id, user.id))
                    results = cursor.fetchall()
                    for row in results:
                        if 'total_profit_in_percentage' in row:
                            row['total_profit_in_percentage'] = round(float(row['total_profit_in_percentage']), 2)
                        if 'current_price' in row and row['current_price'] is not None:
                            row['current_price'] = float(row['current_price'])
                        if 'average_cost' in row and row['average_cost'] is not None:
                            row['average_cost'] = float(row['average_cost'])
                        if 'current_quantity' in row and row['current_quantity'] is not None:
                            row['current_quantity'] = float(row['current_quantity'])
                        if 'total_profit_in_cash' in row and row['total_profit_in_cash'] is not None:
                            row['total_profit_in_cash'] = float(row['total_profit_in_cash'])
                    return results
        except mysql.connector.Error as err:
            logging.error(f"Database error while getting portfolio holdings for User {user.name}: {err}")
            raise PortfolioDataError(f"Could not retrieve portfolio holdings for User {user.name}") from err

    def get_overall_performance_data(self) -> list:
        """Aggregates performance metrics for all users in base VND."""
        with self._get_connection() as conn:
            users = User.get_all(conn)
            performance_data = []
            for user in users:
                try:
                    user_perf = self.get_user_performance_view(user)
                    if not user_perf:
                        continue

                    profit_data = self.get_profit_data(user.id)
                    if profit_data:
                        user_perf.update(profit_data[-1])

                    for key in ['date', 'total_asset_bank', 'total_asset_index']:
                        user_perf.pop(key, None)

                    user_perf['total_investment'] = float(user_perf.get('total_investment', 0))
                    user_perf['total_asset'] = float(user_perf.get('total_asset', 0))
                    user_perf['cash_balance'] = float(user_perf.get('cash_balance', 0))
                    user_perf['total_current_value'] = float(user_perf.get('total_current_value', 0))

                    user_perf['profit_in_cash'] = user_perf['total_asset'] - user_perf['total_investment']

                    if user_perf['total_investment'] > 0:
                        user_perf['profit_percent'] = (user_perf['profit_in_cash'] / user_perf['total_investment']) * 100
                    else:
                        user_perf['profit_percent'] = 0

                    performance_data.append(user_perf)
                except Exception as e:
                    logging.error(f"Failed to process overall performance for user {user.id}: {e}")

            return performance_data

    def get_profit_data(self, user_id: int) -> list:
        """Fetches historical profit data in exact VND."""
        sql_query = """
            SELECT
                date, total_investment, profit_percent, total_asset, total_asset_bank, total_asset_index
            FROM
                portfolio_profit
            WHERE
                user_id = %s
            ORDER BY date ASC;
        """
        with self._get_connection() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(sql_query, (user_id,))
                datas = cursor.fetchall()
                for i in range(len(datas)):
                    datas[i]['date'] = datas[i]['date'].strftime('%Y-%m-%d')
                    for col in ['total_investment', 'total_asset', 'total_asset_bank', 'total_asset_index']:
                        datas[i][col] = float(datas[i][col]) if datas[i][col] is not None else 0.0
                    datas[i]['profit_percent'] = float(datas[i]['profit_percent']) if datas[i]['profit_percent'] is not None else 0.0

                return datas

    def get_user_cash_balance(self, user_id: int) -> float:
        """Calculates cash balance for a user from posting entries."""
        sql_query = """
            SELECT COALESCE(SUM(p.debit - p.credit), 0) as cash_balance
            FROM portfolio_postingorm p
            JOIN portfolio_journalentryorm je ON p.journal_entry_id = je.id
            WHERE je.user_id = %s AND p.account_name = 'Assets:Cash';
        """
        with self._get_connection() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(sql_query, (user_id,))
                data = cursor.fetchone()
                return float(data['cash_balance']) if data and data['cash_balance'] is not None else 0.0

    def get_capital_flow_data(self, user_id: int) -> list:
        """Fetches capital injections and withdrawals combined via SQL UNION ALL."""
        sql_query = """
            SELECT injection_date as date, amount
            FROM portfolio_capitalinjection
            WHERE user_id = %s
            UNION ALL
            SELECT withdraw_date as date, -amount as amount
            FROM portfolio_capitalwithdrawal
            WHERE user_id = %s
            ORDER BY date DESC;
        """
        with self._get_connection() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(sql_query, (user_id, user_id))
                datas = cursor.fetchall()
                for i in range(len(datas)):
                    datas[i]['date'] = datas[i]['date'].strftime('%Y-%m-%d')
                    datas[i]['amount'] = float(datas[i]['amount'])
                return datas

    def get_transaction_data(self, user_id: int) -> list:
        """Fetches transaction history for a user."""
        sql_query = """
            SELECT transaction_date, stock_id as stock_code, quantity, price_per_share, transaction_type
            FROM portfolio_transaction
            WHERE user_id = %s
            ORDER BY transaction_date DESC;
        """
        with self._get_connection() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(sql_query, (user_id,))
                datas = cursor.fetchall()
                for i in range(len(datas)):
                    datas[i]['transaction_date'] = datas[i]['transaction_date'].strftime('%Y-%m-%d')
                    datas[i]['quantity'] = float(datas[i]['quantity'])
                    datas[i]['price_per_share'] = float(datas[i]['price_per_share'])
                return datas

    def get_user_profile_payload(self, user_id: int, dividend_service, ledger_service) -> dict:
        """Consolidates complete user profile payload to render user_profile.html."""
        with self._get_connection() as conn:
            user = User.get_by_id(user_id, conn)
            if not user:
                raise UserNotFoundException(f"User with ID {user_id} not found.")

            perf_data = self.get_user_performance_view(user)
            if not perf_data:
                raise PortfolioDataError(f"Could not retrieve performance data for user {user_id}")

            profit_data = self.get_profit_data(user_id)
            if profit_data:
                perf_data.update(profit_data[-1])

            for key in ['date', 'total_asset_bank', 'total_asset_index']:
                perf_data.pop(key, None)

            perf_data['total_investment'] = float(perf_data.get('total_investment', 0))
            perf_data['total_asset'] = float(perf_data.get('total_asset', 0))
            perf_data['cash_balance'] = float(perf_data.get('cash_balance', 0))
            perf_data['profit_in_cash'] = perf_data['total_asset'] - perf_data['total_investment']
            if perf_data['total_investment'] > 0:
                perf_data['profit_percent'] = (perf_data['profit_in_cash'] / perf_data['total_investment']) * 100
            else:
                perf_data['profit_percent'] = 0

            portfolio_data = self.get_user_portfolio_holdings(user)
            cash_balance = self.get_user_cash_balance(user_id)
            transaction_data = self.get_transaction_data(user_id)
            injection_data = self.get_capital_flow_data(user_id)
            dividend_data = dividend_service.get_user_dividends(user_id)
            user_total_tax = ledger_service.get_total_tax(user_id=user_id)
            user_cash_dividend = dividend_service.get_total_cash_dividend(user_id)

            # Chart values
            stock_values = {
                holding['stock_code']: float(holding['current_price']) * float(holding['current_quantity'])
                for holding in portfolio_data
            }
            stock_values['Cash'] = float(cash_balance)
            chart_labels = list(stock_values.keys())
            chart_data = list(stock_values.values())

            # Profit chart values
            profit_chart_labels = [data['date'] for data in profit_data]
            profit_chart_total_asset = [data['total_asset'] for data in profit_data]
            profit_chart_total_asset_bank = [data['total_asset_bank'] for data in profit_data]
            profit_chart_total_asset_index = [data['total_asset_index'] for data in profit_data]
            profit_chart_total_investment = [data['total_investment'] for data in profit_data]
            profit_chart_profit_percent = profit_data[-1]['profit_percent'] if profit_data else 0.0

            return {
                'user': user,
                'performance_data': perf_data,
                'portfolio_data': portfolio_data,
                'cash_balance': cash_balance,
                'profit_data': profit_data,
                'transaction_data': transaction_data,
                'injection_data': injection_data,
                'dividend_data': dividend_data,
                'user_total_tax': user_total_tax,
                'user_cash_dividend': user_cash_dividend,
                'chart_labels': chart_labels,
                'chart_data': chart_data,
                'profit_chart_labels': profit_chart_labels,
                'profit_chart_total_asset': profit_chart_total_asset,
                'profit_chart_total_asset_bank': profit_chart_total_asset_bank,
                'profit_chart_total_asset_index': profit_chart_total_asset_index,
                'profit_chart_total_investment': profit_chart_total_investment,
                'profit_chart_profit_percent': profit_chart_profit_percent,
            }


class DividendService:
    """Deep module handling corporate action and dividend schedule fetching."""

    def __init__(self, db_or_pool: Union[mysql.connector.MySQLConnection, MySQLConnectionPool]):
        self.db_or_pool = db_or_pool

    @contextmanager
    def _get_connection(self) -> Generator[mysql.connector.MySQLConnection, None, None]:
        if isinstance(self.db_or_pool, MySQLConnectionPool):
            conn = self.db_or_pool.get_connection()
            try:
                yield conn
            finally:
                conn.close()
        else:
            yield self.db_or_pool

    def get_total_cash_dividend(self, user_id: int) -> float:
        """Calculates total cash dividend income received for a user."""
        sql_query = """
            SELECT COALESCE(SUM(p.credit), 0) as total_dividend
            FROM portfolio_postingorm p
            JOIN portfolio_journalentryorm je ON p.journal_entry_id = je.id
            WHERE je.user_id = %s AND p.account_name = 'Revenue:DividendIncome';
        """
        with self._get_connection() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(sql_query, (user_id,))
                res = cursor.fetchone()
                return float(res['total_dividend']) if res and res['total_dividend'] else 0.0

    def get_user_dividends(self, user_id: int) -> list:
        """Fetches dividend events strictly for stocks where user held shares at the ex_date in a single SQL query (O(1) queries)."""
        sql_query = """
            SELECT
                d.id, d.stock_id, d.ex_date, d.record_date, d.payment_date,
                d.dividend_type, d.cash_amount_per_share, d.stock_ratio_numerator, d.stock_ratio_denominator,
                COALESCE(
                    (
                        SELECT SUM(p.credit)
                        FROM portfolio_postingorm p
                        JOIN portfolio_journalentryorm je ON p.journal_entry_id = je.id
                        WHERE je.user_id = %s 
                          AND p.stock_id = d.stock_id 
                          AND p.account_name = 'Revenue:DividendIncome'
                          AND (je.entry_date = d.payment_date OR je.entry_date = d.record_date OR je.entry_date = d.ex_date)
                    ), 0
                ) as received_amount,
                COALESCE(
                    (
                        SELECT SUM(CASE WHEN t.transaction_type = 'BUY' THEN t.quantity ELSE -t.quantity END)
                        FROM portfolio_transaction t
                        WHERE t.user_id = %s AND t.stock_id = d.stock_id AND t.transaction_date <= d.ex_date
                    ), 0
                ) as held_qty_at_ex_date
            FROM portfolio_dividend d
            WHERE (
                SELECT COALESCE(SUM(CASE WHEN t.transaction_type = 'BUY' THEN t.quantity ELSE -t.quantity END), 0)
                FROM portfolio_transaction t
                WHERE t.user_id = %s AND t.stock_id = d.stock_id AND t.transaction_date <= d.ex_date
            ) > 0
            ORDER BY d.ex_date DESC;
        """
        with self._get_connection() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(sql_query, (user_id, user_id, user_id))
                rows = cursor.fetchall()
                for r in rows:
                    for d_col in ['ex_date', 'record_date', 'payment_date']:
                        if r[d_col]:
                            r[d_col] = r[d_col].strftime('%Y-%m-%d')
                    if r['cash_amount_per_share']:
                        r['cash_amount_per_share'] = float(r['cash_amount_per_share'])
                    if 'received_amount' in r and r['received_amount'] is not None:
                        r['received_amount'] = float(r['received_amount'])

                    held_qty = float(r['held_qty_at_ex_date']) if r.get('held_qty_at_ex_date') is not None else 0.0
                    r['received_shares'] = 0.0
                    if r['dividend_type'] != 'Cash' and r['stock_ratio_numerator'] and r['stock_ratio_denominator']:
                        if held_qty > 0:
                            num = float(r['stock_ratio_numerator'])
                            den = float(r['stock_ratio_denominator'])
                            r['received_shares'] = round(held_qty * (num / den), 2)

                return rows


class LedgerService:
    """Deep module handling double-entry journal entry exploration for expert view."""

    def __init__(self, db_or_pool: Union[mysql.connector.MySQLConnection, MySQLConnectionPool]):
        self.db_or_pool = db_or_pool

    @contextmanager
    def _get_connection(self) -> Generator[mysql.connector.MySQLConnection, None, None]:
        if isinstance(self.db_or_pool, MySQLConnectionPool):
            conn = self.db_or_pool.get_connection()
            try:
                yield conn
            finally:
                conn.close()
        else:
            yield self.db_or_pool

    def get_user_journal_entries(self, user_id: int, limit: Optional[int] = None) -> list:
        """Fetches double-entry journal entries and posting legs for expert modal."""
        sql_query = """
            SELECT
                je.id as entry_id, je.entry_date, je.description,
                p.id as posting_id, p.account_name, p.account_type, p.debit, p.credit, p.stock_id, p.quantity
            FROM portfolio_journalentryorm je
            JOIN portfolio_postingorm p ON je.id = p.journal_entry_id
            WHERE je.user_id = %s
            ORDER BY je.entry_date DESC, je.id DESC, p.id ASC
        """
        params = [user_id]
        if limit is not None:
            sql_query += " LIMIT %s"
            params.append(limit * 5)

        with self._get_connection() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(sql_query, tuple(params))
                rows = cursor.fetchall()

                entries_dict = {}
                for r in rows:
                    e_id = r['entry_id']
                    if e_id not in entries_dict:
                        desc = r['description'] or ''
                        cat = "Khác"
                        if "BUY" in desc:
                            cat = "Mua Cổ Phiếu"
                        elif "SELL" in desc:
                            cat = "Bán Cổ Phiếu"
                        elif "Injection" in desc:
                            cat = "Góp Vốn"
                        elif "Withdrawal" in desc:
                            cat = "Rút Vốn"
                        elif "dividend" in desc.lower():
                            cat = "Cổ Tức"

                        entries_dict[e_id] = {
                            'entry_id': e_id,
                            'entry_date': r['entry_date'].strftime('%Y-%m-%d') if r['entry_date'] else '',
                            'description': desc,
                            'category': cat,
                            'postings': []
                        }
                    entries_dict[e_id]['postings'].append({
                        'posting_id': r['posting_id'],
                        'account_name': r['account_name'],
                        'account_type': r['account_type'],
                        'debit': float(r['debit']),
                        'credit': float(r['credit']),
                        'stock_id': r['stock_id'],
                        'quantity': float(r['quantity']) if r['quantity'] else None
                    })

                return list(entries_dict.values())

    def get_total_tax(self, user_id: Optional[int] = None) -> float:
        """Calculates total tax paid (transaction tax + dividend tax) for a user or overall system."""
        if user_id:
            sql_query = """
                SELECT COALESCE(SUM(p.debit), 0) as total_tax
                FROM portfolio_postingorm p
                JOIN portfolio_journalentryorm je ON p.journal_entry_id = je.id
                WHERE je.user_id = %s AND p.account_name IN ('Expenses:TransactionTax', 'Expenses:DividendTax');
            """
            params = (user_id,)
        else:
            sql_query = """
                SELECT COALESCE(SUM(p.debit), 0) as total_tax
                FROM portfolio_postingorm p
                WHERE p.account_name IN ('Expenses:TransactionTax', 'Expenses:DividendTax');
            """
            params = ()

        with self._get_connection() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(sql_query, params)
                res = cursor.fetchone()
                return float(res['total_tax']) if res and res['total_tax'] else 0.0
