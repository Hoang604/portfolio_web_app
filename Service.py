from model.User import User
import mysql.connector
from mysql.connector.pooling import MySQLConnectionPool
import logging
import math
from collections import defaultdict
from decimal import Decimal
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
    def _get_connection(self, conn: Optional[mysql.connector.MySQLConnection] = None) -> Generator[mysql.connector.MySQLConnection, None, None]:
        if conn is not None:
            yield conn
        elif isinstance(self.db_or_pool, MySQLConnectionPool):
            pooled_conn = self.db_or_pool.get_connection()
            try:
                yield pooled_conn
            finally:
                pooled_conn.close()
        else:
            yield self.db_or_pool

    def get_user_portfolio_holdings(self, user: User, conn: Optional[mysql.connector.MySQLConnection] = None) -> list:
        """Retrieves detailed portfolio holdings in base VND."""
        if not user.id:
            return []

        sql_query = """
            SELECT
                s.code AS stock_code,
                s.company_name,
                ph.current_quantity,
                ph.average_cost,
                sp.price AS current_price,
                (ph.current_quantity * (sp.price - ph.average_cost)) AS total_profit_in_cash,
                CASE
                    WHEN ph.average_cost > 0 THEN ((sp.price - ph.average_cost) / ph.average_cost) * 100
                    ELSE 0
                END AS total_profit_in_percentage
            FROM
                portfolio_portfolioholding ph
            JOIN
                portfolio_stock s ON ph.stock_id = s.code
            LEFT JOIN
                portfolio_stockprice sp ON sp.stock_id = ph.stock_id
                AND sp.date = (
                    SELECT MAX(sp2.date)
                    FROM portfolio_stockprice sp2
                    WHERE sp2.stock_id = ph.stock_id
                )
            WHERE
                ph.user_id = %s AND ph.current_quantity > 0
            ORDER BY
                s.code;"""

        try:
            with self._get_connection(conn) as db_conn:
                with db_conn.cursor(dictionary=True) as cursor:
                    cursor.execute(sql_query, (user.id,))
                    results = cursor.fetchall()
                    for row in results:
                        if 'total_profit_in_percentage' in row and row['total_profit_in_percentage'] is not None:
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
        """Aggregates performance metrics for all users in base VND in a single SQL query (O(1) queries)."""
        sql_query = """
            SELECT
                u.id AS user_id,
                u.name,
                u.cash_balance,
                COALESCE(holdings_val.total_current_value, 0) AS total_current_value,
                COALESCE(latest_profit.total_investment, u.total_investment, 0) AS total_investment,
                COALESCE(latest_profit.total_asset, u.cash_balance + COALESCE(holdings_val.total_current_value, 0), 0) AS total_asset
            FROM
                portfolio_user u
            LEFT JOIN (
                SELECT
                    ph.user_id,
                    SUM(ph.current_quantity * sp.price) AS total_current_value
                FROM
                    portfolio_portfolioholding ph
                JOIN (
                    SELECT stock_id, MAX(date) AS max_date
                    FROM portfolio_stockprice
                    GROUP BY stock_id
                ) latest_sp ON ph.stock_id = latest_sp.stock_id
                JOIN portfolio_stockprice sp
                    ON sp.stock_id = latest_sp.stock_id AND sp.date = latest_sp.max_date
                WHERE
                    ph.current_quantity > 0
                GROUP BY
                    ph.user_id
            ) holdings_val ON u.id = holdings_val.user_id
            LEFT JOIN (
                SELECT
                    p.user_id,
                    p.total_investment,
                    p.total_asset
                FROM
                    portfolio_profit p
                JOIN (
                    SELECT user_id, MAX(date) AS max_date
                    FROM portfolio_profit
                    GROUP BY user_id
                ) max_p ON p.user_id = max_p.user_id AND p.date = max_p.max_date
            ) latest_profit ON u.id = latest_profit.user_id
            ORDER BY u.id ASC;
        """
        with self._get_connection() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(sql_query)
                rows = cursor.fetchall()
                performance_data = []
                for user_perf in rows:
                    user_perf['total_investment'] = float(user_perf.get('total_investment') or 0.0)
                    user_perf['total_asset'] = float(user_perf.get('total_asset') or 0.0)
                    user_perf['cash_balance'] = float(user_perf.get('cash_balance') or 0.0)
                    user_perf['total_current_value'] = float(user_perf.get('total_current_value') or 0.0)
                    user_perf['profit_in_cash'] = user_perf['total_asset'] - user_perf['total_investment']
                    if user_perf['total_investment'] > 0:
                        user_perf['profit_percent'] = (user_perf['profit_in_cash'] / user_perf['total_investment']) * 100
                    else:
                        user_perf['profit_percent'] = 0.0
                    performance_data.append(user_perf)
                return performance_data

    def get_profit_data(self, user_id: int, conn: Optional[mysql.connector.MySQLConnection] = None) -> list:
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
        with self._get_connection(conn) as db_conn:
            with db_conn.cursor(dictionary=True) as cursor:
                cursor.execute(sql_query, (user_id,))
                datas = cursor.fetchall()
                for i in range(len(datas)):
                    datas[i]['date'] = datas[i]['date'].strftime('%Y-%m-%d')
                    for col in ['total_investment', 'total_asset', 'total_asset_bank', 'total_asset_index']:
                        datas[i][col] = float(datas[i][col]) if datas[i][col] is not None else 0.0
                    datas[i]['profit_percent'] = float(datas[i]['profit_percent']) if datas[i]['profit_percent'] is not None else 0.0

                return datas

    def get_user_ledger_summary_and_postings(self, user_id: int, conn: Optional[mysql.connector.MySQLConnection] = None) -> tuple[float, float, float, list]:
        """Fetches cash_balance, user_total_tax, user_cash_dividend, and dividend/rights postings in a single connection pass."""
        summary_sql = """
            SELECT
                COALESCE(SUM(CASE WHEN p.account_name = 'Assets:Cash' THEN p.debit - p.credit ELSE 0 END), 0) AS cash_balance,
                COALESCE(SUM(CASE WHEN p.account_name IN ('Expenses:TransactionTax', 'Expenses:DividendTax') THEN p.debit ELSE 0 END), 0) AS total_tax
            FROM portfolio_postingorm p
            JOIN portfolio_journalentryorm je ON p.journal_entry_id = je.id
            WHERE je.user_id = %s
              AND p.account_name IN ('Assets:Cash', 'Expenses:TransactionTax', 'Expenses:DividendTax');
        """
        postings_sql = """
            SELECT
                je.entry_date, je.description, p.stock_id, p.account_name, p.debit, p.credit, p.quantity
            FROM portfolio_postingorm p
            JOIN portfolio_journalentryorm je ON p.journal_entry_id = je.id
            WHERE je.user_id = %s
              AND (
                  p.account_name = 'Revenue:DividendIncome'
                  OR (p.account_name = 'Assets:StockInventory' AND je.description LIKE 'Exercise rights issue%%')
              );
        """
        with self._get_connection(conn) as db_conn:
            with db_conn.cursor(dictionary=True) as cursor:
                cursor.execute(summary_sql, (user_id,))
                summary = cursor.fetchone() or {}
                cursor.execute(postings_sql, (user_id,))
                postings = cursor.fetchall()
                total_dividend = sum(
                    float(p['credit'] or 0.0)
                    for p in postings
                    if p['account_name'] == 'Revenue:DividendIncome'
                )
                return (
                    float(summary.get('cash_balance') or 0.0),
                    float(summary.get('total_tax') or 0.0),
                    total_dividend,
                    postings,
                )

    def get_capital_flow_data(self, user_id: int, conn: Optional[mysql.connector.MySQLConnection] = None) -> list:
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
        with self._get_connection(conn) as db_conn:
            with db_conn.cursor(dictionary=True) as cursor:
                cursor.execute(sql_query, (user_id, user_id))
                datas = cursor.fetchall()
                for i in range(len(datas)):
                    datas[i]['date'] = datas[i]['date'].strftime('%Y-%m-%d')
                    datas[i]['amount'] = float(datas[i]['amount'])
                return datas

    def get_transaction_data(self, user_id: int, conn: Optional[mysql.connector.MySQLConnection] = None) -> list:
        """Fetches transaction history for a user."""
        sql_query = """
            SELECT transaction_date, stock_id as stock_code, quantity, price_per_share, transaction_type
            FROM portfolio_transaction
            WHERE user_id = %s
            ORDER BY transaction_date DESC;
        """
        with self._get_connection(conn) as db_conn:
            with db_conn.cursor(dictionary=True) as cursor:
                cursor.execute(sql_query, (user_id,))
                datas = cursor.fetchall()
                for i in range(len(datas)):
                    datas[i]['transaction_date'] = datas[i]['transaction_date'].strftime('%Y-%m-%d')
                    datas[i]['quantity'] = float(datas[i]['quantity'])
                    datas[i]['price_per_share'] = float(datas[i]['price_per_share'])
                return datas

    def get_user_profile_payload(self, user_id: int, dividend_service, ledger_service) -> dict:
        """Consolidates complete user profile payload to render user_profile.html using a single DB connection."""
        with self._get_connection() as conn:
            user = User.get_by_id(user_id, conn)
            if not user:
                raise UserNotFoundException(f"User with ID {user_id} not found.")

            portfolio_data = self.get_user_portfolio_holdings(user, conn=conn)
            total_current_value = sum(
                float(h.get('current_quantity') or 0.0) * float(h.get('current_price') or 0.0)
                for h in portfolio_data
            )
            perf_data = {
                'user_id': user.id,
                'name': user.name,
                'cash_balance': float(user.cash_balance or 0.0),
                'total_current_value': total_current_value,
            }

            profit_data = self.get_profit_data(user_id, conn=conn)
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

            cash_balance, user_total_tax, user_cash_dividend, posting_rows = (
                self.get_user_ledger_summary_and_postings(user_id, conn=conn)
            )
            transaction_data = self.get_transaction_data(user_id, conn=conn)
            injection_data = self.get_capital_flow_data(user_id, conn=conn)
            dividend_data = dividend_service.get_user_dividends(
                user_id, conn=conn, posting_rows=posting_rows
            )

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

            return {
                'user': user,
                'performance_data': perf_data,
                'portfolio_data': portfolio_data,
                'cash_balance': cash_balance,
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
            }


class DividendService:
    """Deep module handling corporate action and dividend schedule fetching."""

    def __init__(self, db_or_pool: Union[mysql.connector.MySQLConnection, MySQLConnectionPool]):
        self.db_or_pool = db_or_pool

    @contextmanager
    def _get_connection(self, conn: Optional[mysql.connector.MySQLConnection] = None) -> Generator[mysql.connector.MySQLConnection, None, None]:
        if conn is not None:
            yield conn
        elif isinstance(self.db_or_pool, MySQLConnectionPool):
            pooled_conn = self.db_or_pool.get_connection()
            try:
                yield pooled_conn
            finally:
                pooled_conn.close()
        else:
            yield self.db_or_pool

    def get_user_dividends(
        self,
        user_id: int,
        conn: Optional[mysql.connector.MySQLConnection] = None,
        posting_rows: Optional[list] = None,
    ) -> list:
        """Fetches dividend and rights issue events where the user held shares at ex_date, accounting for prior stock dividends and rights issues."""
        dividends_sql = """
            SELECT
                d.id, d.stock_id, d.ex_date, d.record_date, d.payment_date,
                d.dividend_type, d.cash_amount_per_share, d.stock_ratio_numerator, d.stock_ratio_denominator
            FROM portfolio_dividend d
            ORDER BY d.ex_date ASC, d.id ASC;
        """
        tx_sql = """
            SELECT
                t.user_id, t.stock_id, t.transaction_date,
                SUM(CASE WHEN t.transaction_type = 'BUY' THEN t.quantity ELSE -t.quantity END) AS net_qty
            FROM portfolio_transaction t
            GROUP BY t.user_id, t.stock_id, t.transaction_date
            ORDER BY t.transaction_date ASC;
        """
        postings_sql = """
            SELECT
                je.entry_date, je.description, p.stock_id, p.account_name, p.debit, p.credit, p.quantity
            FROM portfolio_postingorm p
            JOIN portfolio_journalentryorm je ON p.journal_entry_id = je.id
            WHERE je.user_id = %s
              AND (
                  p.account_name = 'Revenue:DividendIncome'
                  OR (p.account_name = 'Assets:StockInventory' AND je.description LIKE 'Exercise rights issue%%')
              );
        """
        with self._get_connection(conn) as db_conn:
            with db_conn.cursor(dictionary=True) as cursor:
                cursor.execute(dividends_sql)
                dividends = cursor.fetchall()
                if not dividends:
                    return []

                cursor.execute(tx_sql)
                tx_rows = cursor.fetchall()

                if posting_rows is None:
                    cursor.execute(postings_sql, (user_id,))
                    posting_rows = cursor.fetchall()

        tx_by_stock = defaultdict(list)
        for tx in tx_rows:
            tx_by_stock[tx['stock_id']].append(tx)

        cash_div_postings = defaultdict(float)
        rights_postings = {}
        for p in posting_rows:
            if p['account_name'] == 'Revenue:DividendIncome':
                cash_div_postings[(p['stock_id'], p['entry_date'])] += float(p['credit'] or 0.0)
            elif p['account_name'] == 'Assets:StockInventory':
                rights_postings[(p['stock_id'], p['entry_date'])] = (
                    float(p['quantity'] or 0.0),
                    float(p['debit'] or 0.0),
                )

        divs_by_stock = defaultdict(list)
        for d in dividends:
            divs_by_stock[d['stock_id']].append(d)

        user_results = []
        for stock_id, stock_divs in divs_by_stock.items():
            holdings = defaultdict(lambda: Decimal('0'))
            stock_txs = tx_by_stock.get(stock_id, [])
            tx_idx = 0
            n_txs = len(stock_txs)

            # Group dividends sharing the same ex_date so concurrent Stock & Rights events evaluate against the same pre-ex_date holdings
            ex_date_groups = []
            for d in stock_divs:
                if not ex_date_groups or ex_date_groups[-1][0] != d['ex_date']:
                    ex_date_groups.append((d['ex_date'], [d]))
                else:
                    ex_date_groups[-1][1].append(d)

            for ex_date, group_divs in ex_date_groups:
                while tx_idx < n_txs and stock_txs[tx_idx]['transaction_date'] <= ex_date:
                    row = stock_txs[tx_idx]
                    holdings[row['user_id']] += Decimal(str(row['net_qty']))
                    tx_idx += 1

                pending_additions = defaultdict(lambda: Decimal('0'))
                for d in group_divs:
                    user_held = holdings.get(user_id, Decimal('0'))
                    allocations = {}
                    if d['dividend_type'] in ('Stock', 'Rights') and d['stock_ratio_numerator'] and d['stock_ratio_denominator']:
                        num = Decimal(str(d['stock_ratio_numerator']))
                        den = Decimal(str(d['stock_ratio_denominator']))
                        if den > 0:
                            active_holders = {u: qty for u, qty in holdings.items() if qty > Decimal('0')}
                            total_pool = sum(active_holders.values(), Decimal('0'))
                            total_issued = int(math.floor(total_pool * (num / den)))
                            if total_issued > 0:
                                remainders = {}
                                for u, qty in active_holders.items():
                                    exact = qty * (num / den)
                                    int_part = int(math.floor(exact))
                                    allocations[u] = int_part
                                    remainders[u] = exact - Decimal(int_part)
                                rem_to_dist = total_issued - sum(allocations.values())
                                for u in sorted(remainders.keys(), key=lambda k: remainders[k], reverse=True)[:rem_to_dist]:
                                    allocations[u] += 1
                                for u, sh in allocations.items():
                                    pending_additions[u] += Decimal(sh)

                    if user_held > Decimal('0'):
                        r = dict(d)
                        r['held_qty_at_ex_date'] = float(user_held)
                        r['cash_amount_per_share'] = float(r['cash_amount_per_share']) if r['cash_amount_per_share'] else 0.0
                        r['received_amount'] = 0.0
                        r['received_shares'] = 0.0
                        r['paid_amount'] = 0.0

                        if r['dividend_type'] == 'Cash':
                            amt = 0.0
                            for dt in (r['payment_date'], r['record_date'], r['ex_date']):
                                if dt and (stock_id, dt) in cash_div_postings:
                                    amt = cash_div_postings[(stock_id, dt)]
                                    break
                            r['received_amount'] = amt
                        elif r['dividend_type'] == 'Rights':
                            matched_rights = None
                            for dt in (r['record_date'], r['payment_date'], r['ex_date']):
                                if dt and (stock_id, dt) in rights_postings:
                                    matched_rights = rights_postings[(stock_id, dt)]
                                    break
                            if matched_rights is not None:
                                r['received_shares'], r['paid_amount'] = matched_rights
                            else:
                                sh = float(allocations.get(user_id, 0))
                                r['received_shares'] = sh
                                r['paid_amount'] = sh * r['cash_amount_per_share']
                        else:
                            r['received_shares'] = float(allocations.get(user_id, 0))

                        for d_col in ('ex_date', 'record_date', 'payment_date'):
                            if r[d_col]:
                                r[d_col] = r[d_col].strftime('%Y-%m-%d')

                        user_results.append(r)

                for u, add_qty in pending_additions.items():
                    holdings[u] += add_qty

        user_results.sort(key=lambda x: (x['ex_date'], x['payment_date'] or '', x['id']), reverse=True)
        return user_results


class LedgerService:
    """Deep module handling double-entry journal entry exploration for expert view."""

    def __init__(self, db_or_pool: Union[mysql.connector.MySQLConnection, MySQLConnectionPool]):
        self.db_or_pool = db_or_pool

    @contextmanager
    def _get_connection(self, conn: Optional[mysql.connector.MySQLConnection] = None) -> Generator[mysql.connector.MySQLConnection, None, None]:
        if conn is not None:
            yield conn
        elif isinstance(self.db_or_pool, MySQLConnectionPool):
            pooled_conn = self.db_or_pool.get_connection()
            try:
                yield pooled_conn
            finally:
                pooled_conn.close()
        else:
            yield self.db_or_pool

    def get_user_journal_entries(self, user_id: int, limit: Optional[int] = None) -> list:
        """Fetches double-entry journal entries and posting legs for expert modal."""
        if limit is not None:
            sql_query = """
                SELECT
                    je.id as entry_id, je.entry_date, je.description,
                    p.id as posting_id, p.account_name, p.account_type, p.debit, p.credit, p.stock_id, p.quantity
                FROM (
                    SELECT id, entry_date, description
                    FROM portfolio_journalentryorm
                    WHERE user_id = %s
                    ORDER BY entry_date DESC, id DESC
                    LIMIT %s
                ) je
                JOIN portfolio_postingorm p ON je.id = p.journal_entry_id
                ORDER BY je.entry_date DESC, je.id DESC, p.id ASC
            """
            params = (user_id, limit)
        else:
            sql_query = """
                SELECT
                    je.id as entry_id, je.entry_date, je.description,
                    p.id as posting_id, p.account_name, p.account_type, p.debit, p.credit, p.stock_id, p.quantity
                FROM portfolio_journalentryorm je
                JOIN portfolio_postingorm p ON je.id = p.journal_entry_id
                WHERE je.user_id = %s
                ORDER BY je.entry_date DESC, je.id DESC, p.id ASC
            """
            params = (user_id,)

        with self._get_connection() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(sql_query, params)
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
                        elif "rights issue" in desc.lower():
                            cat = "Quyền Mua CP"
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

    def get_total_tax(self) -> float:
        """Calculates total tax paid (transaction tax + dividend tax) across the overall system."""
        sql_query = """
            SELECT COALESCE(SUM(p.debit), 0) as total_tax
            FROM portfolio_postingorm p
            WHERE p.account_name IN ('Expenses:TransactionTax', 'Expenses:DividendTax');
        """
        with self._get_connection() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(sql_query)
                res = cursor.fetchone()
                return float(res['total_tax']) if res and res['total_tax'] else 0.0
