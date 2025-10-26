from model.User import User
import mysql.connector
import logging

# Custom Exceptions


class UserNotFoundException(Exception):
    pass


class PortfolioDataError(Exception):
    pass


class PortfolioService:
    """Service layer for handling portfolio business logic."""

    def __init__(self, mydb: mysql.connector):
        """Initializes the PortfolioService.

        Args:
            mydb: An active mysql.connector database connection.
        """
        self.db = mydb

    def get_user_by_id(self, user_id):
        """Retrieves a single user by their ID.

        Args:
            user_id: The ID of the user to retrieve.

        Returns:
            A User object if found, otherwise None.
        """
        return User.get_by_id(user_id, self.db)

    def _get_user_overall_performance_view(self, user: User) -> dict:
        """Calculates a user's core performance data using a single SQL query.

        This private method efficiently computes the total value of all stocks
        held by a user and combines it with their cash balance. It is designed
        to be called by public methods that build upon this data.

        Args:
            user: The User object for whom to calculate performance.

        Returns:
            A dictionary containing the user's core performance data, for example:
            {
                'user_id': 1,
                'name': 'John Doe',
                'cash_balance': 5000.00,
                'total_current_value': 15000.00
            }
            Returns an empty dict if the calculation fails.
        """
        if not user.id:
            logging.warning(
                "Attempted to get overall performance for a user without an ID.")
            return {}
        if not self.db:
            raise ConnectionError("Database connection is not available.")

        sql_query = """
            SELECT
                u.id AS user_id,
                u.name,
                u.cash_balance,
                COALESCE(SUM(ph.current_quantity * latest_prices.price * 1000), 0) AS total_current_value
            FROM
                portfolio_user u
            LEFT JOIN
                portfolio_portfolioholding ph ON u.id = ph.user_id
            LEFT JOIN
                (
                    SELECT stock_id, price
                    FROM (
                        SELECT
                            stock_id,
                            price,
                            ROW_NUMBER() OVER(PARTITION BY stock_id ORDER BY date DESC) as rn
                        FROM portfolio_stockprice
                    ) AS ranked_prices
                    WHERE rn = 1
                ) AS latest_prices ON ph.stock_id = latest_prices.stock_id
            WHERE
                u.id = %s
            GROUP BY
                u.id, u.name, u.cash_balance;"""

        try:
            cursor = self.db.cursor(dictionary=True)
            cursor.execute(sql_query, (user.id,))
            result = cursor.fetchone()
            return result if result else {}
        except mysql.connector.Error as err:
            logging.error(
                f"Database error while getting overall performance for User {user.name}: {err}")
            raise PortfolioDataError(
                f"Could not retrieve overall performance for User {user.name}") from err

    def _get_user_portfolio_holdings_view(self, user: User):
        """Retrieves the detailed portfolio holdings for a user with profit/loss.

        This method uses a single, efficient SQL query to fetch all currently held
        stocks (quantity > 0) for a given user. It joins holdings with the latest
        stock prices to calculate the current value, profit in cash, and profit
        percentage for each holding directly in the database.

        Args:
            user: The User object for whom to retrieve holdings.

        Returns:
            A list of dictionaries, where each dictionary represents a stock
            holding. For example:
            [
                {
                    'stock_code': 'AAPL',
                    'company_name': 'Apple Inc.',
                    'current_quantity': 10,
                    'average_cost': 150.00,
                    'current_price': 175.00,
                    'total_profit_in_cash': 250.00,
                    'total_profit_in_percentage': 16.67
                }, ...
            ]
            Returns an empty list if the user has no holdings or an error occurs.
        """
        if not user.id:
            logging.warning(
                "Attempted to get portfolio holdings for a user without an ID.")
            return []
        if not self.db:
            raise ConnectionError("Database connection is not available.")

        sql_query = """
            SELECT
                s.code AS stock_code,
                s.company_name,
                ph.current_quantity,
                ph.average_cost,
                (latest_prices.price * 1000) AS current_price,
                (ph.current_quantity * ((latest_prices.price * 1000) - ph.average_cost)) AS total_profit_in_cash,
                CASE
                    WHEN ph.average_cost > 0 THEN (((latest_prices.price * 1000) - ph.average_cost) / ph.average_cost) * 100
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
                    ) AS ranked_prices
                    WHERE rn = 1
                ) AS latest_prices ON ph.stock_id = latest_prices.stock_id
            WHERE
                ph.user_id = %s AND ph.current_quantity > 0
            ORDER BY
                s.code;"""

        try:
            cursor = self.db.cursor(dictionary=True)
            cursor.execute(sql_query, (user.id,))
            results = cursor.fetchall()
            # The percentage can be a Decimal type from DB, so we cast it to float
            for row in results:
                if 'total_profit_in_percentage' in row:
                    row['total_profit_in_percentage'] = round(
                        float(row['total_profit_in_percentage']), 2)
            return results
        except mysql.connector.Error as err:
            logging.error(
                f"Database error while getting portfolio holdings for User {user.name}: {err}")
            raise PortfolioDataError(
                f"Could not retrieve portfolio holdings for User {user.name}") from err

    def get_overall_performance_data(self):
        """Aggregates and calculates performance data for all users.

        This method iterates through all users, fetches their core performance
        data, combines it with historical profit data, and calculates final
        metrics like profit in cash and profit percentage.

        Returns:
            A list of dictionaries, each containing comprehensive performance
            data for a user. For example:
            [
                {
                    'user_id': 1,
                    'name': 'John Doe',
                    'cash_balance': 5000.00,
                    'total_current_value': 15000.00,
                    'total_investment': 12000.00,
                    'total_asset': 20000.00,
                    'profit_in_cash': 8000.00,
                    'profit_percent': 66.67
                }, ...
            ]
        """
        users = User.get_all(self.db)
        performance_data = []
        for user in users:
            try:
                user_perf = self._get_user_overall_performance_view(user)
                print(
                    f"User {user.id} - Preliminary Performance Data: {user_perf}")
                if not user_perf:
                    continue  # Skip user if no performance data is found

                profit_data = self.get_profit_data(user.id)
                print(
                    f"User {user.id} - Profit Data: {profit_data[-1]}")
                if profit_data:
                    user_perf.update(profit_data[-1])

                pop_keys = ['date', 'total_asset_bank', 'total_asset_index']
                for key in pop_keys:
                    if key in user_perf:
                        user_perf.pop(key)

                user_perf['total_investment'] = user_perf.get(
                    'total_investment', 0)
                user_perf['total_asset'] = user_perf.get('total_asset', 0)

                user_perf['profit_in_cash'] = user_perf['total_asset'] - \
                    user_perf['total_investment']

                if user_perf['total_investment'] > 0:
                    user_perf['profit_percent'] = (
                        user_perf['profit_in_cash'] / user_perf['total_investment']) * 100
                else:
                    user_perf['profit_percent'] = 0

                performance_data.append(user_perf)
            except (PortfolioDataError, Exception) as e:
                logging.error(
                    f"Failed to process overall performance for user {user.id}: {e}")

        return performance_data

    def get_user_performance_data(self, user_id):
        """Aggregates and calculates comprehensive performance data for a single user.

        Fetches the user's core performance data, merges it with historical
        profit information, and computes derived metrics like profit in cash and
        profit percentage.

        Args:
            user_id: The ID of the user.

        Returns:
            A dictionary containing the comprehensive performance data for the user.
            For example:
            {
                'user_id': 1,
                'name': 'John Doe',
                'cash_balance': 5000.00,
                'total_current_value': 15000.00,
                'total_investment': 12000.00,
                'total_asset': 20000.00,
                'profit_in_cash': 8000.00,
                'profit_percent': 66.67
            }

        Raises:
            UserNotFoundException: If no user is found for the given user_id.
            PortfolioDataError: If data cannot be retrieved or calculated.
        """
        user = User.get_by_id(user_id, self.db)
        if not user:
            raise UserNotFoundException(f"User with ID {user_id} not found.")

        try:
            performance_data = self._get_user_overall_performance_view(user)
            if not performance_data:
                raise PortfolioDataError(
                    f"Could not retrieve performance data for user {user_id}")

            profit_data = self.get_profit_data(user_id)
            if profit_data:
                performance_data.update(profit_data[-1])

            pop_keys = ['date', 'total_asset_bank', 'total_asset_index']
            for key in pop_keys:
                if key in performance_data:
                    performance_data.pop(key)

            performance_data['total_investment'] = performance_data.get(
                'total_investment', 0)
            performance_data['total_asset'] = performance_data.get(
                'total_asset', 0)

            performance_data['profit_in_cash'] = performance_data['total_asset'] - \
                performance_data['total_investment']

            if performance_data['total_investment'] > 0:
                performance_data['profit_percent'] = (
                    performance_data['profit_in_cash'] / performance_data['total_investment']) * 100
            else:
                performance_data['profit_percent'] = 0

            print(performance_data['profit_percent'])

            return performance_data
        except (PortfolioDataError, Exception) as e:
            logging.error(
                f"Failed to get performance data for user {user_id}: {e}")
            raise  # Re-raise the exception to be handled by the caller

    def get_user_cash_balance(self, user_id):
        """Retrieves the cash balance for a specific user.

        Args:
            user_id: The ID of the user.

        Returns:
            The user's cash balance as a float, or 0 if the user is not found.
        """
        # This method could also be updated to use UserNotFoundException if desired
        sql_query = """
            SELECT
                cash_balance
            FROM
                portfolio_user
            WHERE
                id = %s
        """
        cursor = self.db.cursor(dictionary=True)
        cursor.execute(sql_query, (user_id,))
        data = cursor.fetchone()
        if data:
            return data['cash_balance']
        else:
            # Or raise UserNotFoundException(f"User with ID {user_id} not found.")
            return 0

    def get_portfolio_holdings_data(self, user_id):
        """Public method to retrieve the detailed portfolio holdings for a user.

        This is a wrapper around the private _get_user_portfolio_holdings_view method.

        Args:
            user_id: The ID of the user.

        Returns:
            A list of dictionaries representing the user's stock holdings.

        Raises:
            UserNotFoundException: If no user is found for the given user_id.
        """
        user = User.get_by_id(user_id, self.db)
        if not user:
            raise UserNotFoundException(f"User with ID {user_id} not found.")
        return self._get_user_portfolio_holdings_view(user)

    def get_profit_data(self, user_id):
        """Fetches historical profit data for a user from the 'portfolio_profit' table.

        Args:
            user_id: The ID of the user.

        Returns:
            A list of dictionaries, each representing a profit snapshot. For example:
            [
                {
                    'date': '2025-10-26',
                    'total_investment': 12000.00,
                    'profit_percent': 66.67,
                    'total_asset': 20000.00,
                    'total_asset_bank': 18000.00,
                    'total_asset_index': 19000.00
                }, ...
            ]
        """
        sql_query = """
            SELECT
                date, (total_investment * 1000) as total_investment, profit_percent, (total_asset * 1000) as total_asset, (total_asset_bank * 1000) as total_asset_bank, (total_asset_index * 1000) as total_asset_index
            FROM
                portfolio_profit
            WHERE
                user_id = %s;
        """
        cursor = self.db.cursor(dictionary=True)
        cursor.execute(sql_query, (user_id,))
        datas = cursor.fetchall()
        for i in range(len(datas)):
            datas[i]['date'] = datas[i]['date'].strftime('%Y-%m-%d')

        return datas

    def get_injection_data(self, user_id):
        """Fetches all capital injections and withdrawals for a user.

        This method queries both the capital injection and withdrawal tables,
        combines the results, and sorts them by date in descending order.
        Withdrawals are represented as negative amounts.

        Args:
            user_id: The ID of the user.

        Returns:
            A sorted list of dictionaries, each representing a capital event.
            For example:
            [
                {'date': '2025-10-20', 'amount': 10000.00},
                {'date': '2025-09-15', 'amount': -2000.00}
            ]
        """
        sql_query = """
            SELECT
                injection_date as date, amount
            FROM
                portfolio_capitalinjection
            WHERE
                user_id = %s
            Order by injection_date DESC;
        """
        cursor = self.db.cursor(dictionary=True)
        cursor.execute(sql_query, (user_id,))
        datas = cursor.fetchall()
        for i in range(len(datas)):
            datas[i]['date'] = datas[i]['date'].strftime('%Y-%m-%d')

        sql_query = """
            SELECT
                withdraw_date as date, - amount as amount
            FROM
                portfolio_capitalwithdrawal
            WHERE
                user_id = %s
            Order by withdraw_date DESC;
        """
        cursor.execute(sql_query, (user_id,))
        withdrawal_datas = cursor.fetchall()
        for i in range(len(withdrawal_datas)):
            withdrawal_datas[i]['date'] = withdrawal_datas[i]['date'].strftime(
                '%Y-%m-%d')
        datas += withdrawal_datas
        datas.sort(key=lambda x: x['date'], reverse=True)

        return datas

    def get_transaction_data(self, user_id):
        """Fetches all stock transactions (buy/sell) for a specific user.

        Args:
            user_id: The ID of the user.

        Returns:
            A list of dictionaries, each representing a stock transaction.
            For example:
            [
                {
                    'transaction_date': '2025-10-25',
                    'stock_code': 'AAPL',
                    'quantity': 5,
                    'price_per_share': 170.00,
                    'transaction_type': 'buy'
                }, ...
            ]
        """
        sql_query = """
            SELECT
                transaction_date, stock_id as stock_code, quantity, price_per_share, transaction_type
            FROM
                portfolio_transaction
            WHERE
                user_id = %s
            Order by transaction_date DESC;
        """
        cursor = self.db.cursor(dictionary=True)
        cursor.execute(sql_query, (user_id,))
        datas = cursor.fetchall()
        for i in range(len(datas)):
            datas[i]['transaction_date'] = datas[i]['transaction_date'].strftime(
                '%Y-%m-%d')

        return datas
