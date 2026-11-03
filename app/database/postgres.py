import psycopg

from psycopg import sql
from psycopg.rows import dict_row

from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from config.settings import Settings


class PostgreSQLDatabase:

    # ==================================================
    # INITIALIZATION
    # ==================================================

    def __init__(self):

        self.config = {
            "host": Settings.DB_HOST,
            "port": Settings.DB_PORT,
            "dbname": Settings.DB_NAME,
            "user": Settings.DB_USER,
            "password": Settings.DB_PASSWORD,
            "connect_timeout": 5,
        }

        self.schema = "public"
        self.max_limit = 100

    # ==================================================
    # DATABASE CONNECTION
    # ==================================================

    def get_connection(self):
        """
        Read-only connection.
        Used for SELECT and database discovery.
        """

        connection = psycopg.connect(**self.config)

        connection.execute("SET TRANSACTION READ ONLY")

        return connection

    def get_write_connection(self):
        """
        Read-write connection.
        Used for INSERT operations.
        """

        return psycopg.connect(**self.config)

    # ==================================================
    # RESPONSE SERIALIZATION
    # ==================================================

    @staticmethod
    def serialize_records(records):

        serialized = []

        for record in records:

            item = {}

            for key, value in record.items():

                if isinstance(value, (date, datetime)):
                    item[key] = value.isoformat()

                elif isinstance(value, Decimal):
                    item[key] = float(value)

                else:
                    item[key] = value

            serialized.append(item)

        return serialized

    # ==================================================
    # CHECK DATABASE CONNECTION
    # ==================================================

    def check_connection(self):

        try:

            with self.get_connection() as connection:

                with connection.cursor() as cursor:

                    cursor.execute("SELECT 1")

                    result = cursor.fetchone()

            return {
                "status": "SUCCESS",
                "database": Settings.DB_NAME,
                "connection": "ACTIVE",
                "result": result[0]
            }

        except psycopg.Error as error:

            return {
                "status": "FAILED",
                "database": Settings.DB_NAME,
                "connection": "INACTIVE",
                "message": str(error)
            }

    # ==================================================
    # DATABASE DIAGNOSTICS
    # ==================================================

    def database_diagnostics(self):

        try:

            with self.get_connection() as connection:

                with connection.cursor(
                    row_factory=dict_row
                ) as cursor:

                    cursor.execute("""
                        SELECT
                            current_database() AS database_name,
                            current_schema() AS current_schema,
                            current_user AS connected_user,
                            inet_server_addr() AS server_address,
                            inet_server_port() AS server_port;
                    """)

                    database_info = cursor.fetchone()

                    cursor.execute("""
                        SELECT
                            schemaname,
                            tablename
                        FROM pg_catalog.pg_tables
                        WHERE schemaname NOT IN (
                            'pg_catalog',
                            'information_schema'
                        )
                        ORDER BY schemaname, tablename;
                    """)

                    all_tables = cursor.fetchall()

                    cursor.execute("""
                        SELECT table_name
                        FROM information_schema.tables
                        WHERE table_schema = %s
                          AND table_type = 'BASE TABLE'
                        ORDER BY table_name;
                    """, (self.schema,))

                    schema_tables = [
                        row["table_name"]
                        for row in cursor.fetchall()
                    ]

            return {
                "status": "SUCCESS",
                "connection": database_info,
                "configured_schema": self.schema,
                "configured_schema_tables": schema_tables,
                "all_user_tables": all_tables,
                "total_tables": len(all_tables)
            }

        except psycopg.Error as error:

            return {
                "status": "FAILED",
                "message": str(error)
            }

    # ==================================================
    # DYNAMIC TABLE DISCOVERY
    # ==================================================

    def list_tables(self):

        try:

            with self.get_connection() as connection:

                with connection.cursor() as cursor:

                    cursor.execute("""
                        SELECT table_name
                        FROM information_schema.tables
                        WHERE table_schema = %s
                          AND table_type = 'BASE TABLE'
                        ORDER BY table_name;
                    """, (self.schema,))

                    tables = [
                        row[0]
                        for row in cursor.fetchall()
                    ]

            return {
                "status": "SUCCESS",
                "schema": self.schema,
                "count": len(tables),
                "tables": tables
            }

        except psycopg.Error as error:

            return {
                "status": "FAILED",
                "message": str(error),
                "tables": []
            }

    # ==================================================
    # DYNAMIC COLUMN DISCOVERY
    # ==================================================

    def get_table_schema(self, table_name):

        try:

            with self.get_connection() as connection:

                with connection.cursor(
                    row_factory=dict_row
                ) as cursor:

                    if not self.validate_table(
                        cursor,
                        table_name
                    ):

                        return {
                            "status": "NOT_FOUND",
                            "message": f"Table '{table_name}' was not found."
                        }

                    cursor.execute("""
                        SELECT
                            column_name,
                            data_type,
                            is_nullable,
                            column_default
                        FROM information_schema.columns
                        WHERE table_schema = %s
                          AND table_name = %s
                        ORDER BY ordinal_position;
                    """, (self.schema, table_name))

                    columns = cursor.fetchall()

            return {
                "status": "SUCCESS",
                "table": table_name,
                "columns": columns
            }

        except psycopg.Error as error:

            return {
                "status": "FAILED",
                "message": str(error)
            }

    # ==================================================
    # VALIDATE TABLE
    # ==================================================

    def validate_table(self, cursor, table_name):

        cursor.execute("""
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = %s
                  AND table_name = %s
                  AND table_type = 'BASE TABLE'
            ) AS table_exists;
        """, (self.schema, table_name))

        result = cursor.fetchone()

        return result["table_exists"]

    # ==================================================
    # GET VALID COLUMNS
    # ==================================================

    def get_valid_columns(self, cursor, table_name):

        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = %s
              AND table_name = %s;
        """, (self.schema, table_name))

        return {
            row["column_name"]
            for row in cursor.fetchall()
        }

    # ==================================================
    # GENERIC READ QUERY ENGINE
    # ==================================================

    def execute_read_query(self, query_plan):

        try:

            operation = query_plan.get(
                "operation", ""
            ).upper()

            table_name = query_plan.get("table_name")

            if not table_name:

                return {
                    "status": "FAILED",
                    "message": "Table name is required."
                }

            with self.get_connection() as connection:

                with connection.cursor(
                    row_factory=dict_row
                ) as cursor:

                    if not self.validate_table(
                        cursor,
                        table_name
                    ):

                        return {
                            "status": "NOT_FOUND",
                            "message": f"Table '{table_name}' does not exist."
                        }

                    valid_columns = self.get_valid_columns(
                        cursor,
                        table_name
                    )

                    table = sql.Identifier(
                        self.schema,
                        table_name
                    )

                    records = []

                    # DESCRIBE
                    if operation == "DESCRIBE":

                        cursor.execute("""
                            SELECT
                                column_name,
                                data_type,
                                is_nullable,
                                column_default
                            FROM information_schema.columns
                            WHERE table_schema = %s
                              AND table_name = %s
                            ORDER BY ordinal_position;
                        """, (self.schema, table_name))

                        records = cursor.fetchall()

                    # COUNT
                    elif operation == "COUNT":

                        query = sql.SQL("""
                            SELECT COUNT(*) AS total_records
                            FROM {};
                        """).format(table)

                        cursor.execute(query)

                        records = cursor.fetchall()

                    # GET ALL
                    elif operation == "GET_ALL":

                        limit = self.validate_limit(
                            query_plan.get("limit")
                        )

                        query = sql.SQL("""
                            SELECT *
                            FROM {}
                            LIMIT %s;
                        """).format(table)

                        cursor.execute(query, (limit,))

                        records = cursor.fetchall()

                    # DISTINCT
                    elif operation == "DISTINCT":

                        column = query_plan.get(
                            "distinct_column"
                        )

                        self.validate_column(
                            column,
                            valid_columns
                        )

                        query = sql.SQL("""
                            SELECT DISTINCT {}
                            FROM {}
                            ORDER BY {}
                            LIMIT %s;
                        """).format(
                            sql.Identifier(column),
                            table,
                            sql.Identifier(column)
                        )

                        cursor.execute(
                            query,
                            (self.max_limit,)
                        )

                        records = cursor.fetchall()

                    # GROUP BY
                    elif operation == "GROUP_BY":

                        column = query_plan.get("group_by")

                        self.validate_column(
                            column,
                            valid_columns
                        )

                        query = sql.SQL("""
                            SELECT {},
                                   COUNT(*) AS total_records
                            FROM {}
                            GROUP BY {}
                            ORDER BY {}
                            LIMIT %s;
                        """).format(
                            sql.Identifier(column),
                            table,
                            sql.Identifier(column),
                            sql.Identifier(column)
                        )

                        cursor.execute(
                            query,
                            (self.max_limit,)
                        )

                        records = cursor.fetchall()

                    # AGGREGATE
                    elif operation == "AGGREGATE":

                        aggregate = query_plan.get(
                            "aggregate"
                        ) or {}

                        function = (
                            aggregate.get("function")
                            or query_plan.get("function")
                            or ""
                        ).upper()

                        column = (
                            aggregate.get("column")
                            or query_plan.get("column")
                        )

                        allowed_functions = {
                            "AVG",
                            "SUM",
                            "MIN",
                            "MAX"
                        }

                        if function not in allowed_functions:

                            raise ValueError(
                                "Unsupported aggregate function."
                            )

                        self.validate_column(
                            column,
                            valid_columns
                        )

                        query = sql.SQL("""
                            SELECT {}({}) AS result
                            FROM {};
                        """).format(
                            sql.SQL(function),
                            sql.Identifier(column),
                            table
                        )

                        cursor.execute(query)

                        records = cursor.fetchall()

                    # SEARCH
                    elif operation == "SEARCH":

                        search_text = query_plan.get(
                            "search_text", ""
                        )

                        if not isinstance(search_text, str):

                            raise ValueError(
                                "Search text must be a string."
                            )

                        search_text = search_text.strip()

                        if not search_text:

                            raise ValueError(
                                "Search text is required."
                            )

                        cursor.execute("""
                            SELECT column_name
                            FROM information_schema.columns
                            WHERE table_schema = %s
                              AND table_name = %s
                              AND data_type IN (
                                  'character varying',
                                  'character',
                                  'text'
                              );
                        """, (self.schema, table_name))

                        text_columns = [
                            row["column_name"]
                            for row in cursor.fetchall()
                        ]

                        if not text_columns:

                            raise ValueError(
                                "No searchable text columns found."
                            )

                        conditions = [
                            sql.SQL("{} ILIKE %s").format(
                                sql.Identifier(column)
                            )
                            for column in text_columns
                        ]

                        where_clause = sql.SQL(" OR ").join(
                            conditions
                        )

                        query = sql.SQL("""
                            SELECT *
                            FROM {}
                            WHERE {}
                            LIMIT %s;
                        """).format(
                            table,
                            where_clause
                        )

                        parameters = [
                            f"%{search_text}%"
                        ] * len(text_columns)

                        parameters.append(self.max_limit)

                        cursor.execute(query, parameters)

                        records = cursor.fetchall()

                    # FILTER
                    elif operation == "FILTER":

                        filters = query_plan.get(
                            "filters", []
                        )

                        if not filters:

                            raise ValueError(
                                "At least one filter is required."
                            )

                        conditions = []
                        parameters = []

                        allowed_operators = {
                            "=", "!=", ">", "<",
                            ">=", "<=", "LIKE", "ILIKE"
                        }

                        for condition in filters:

                            column = condition.get("column")

                            operator = condition.get(
                                "operator", ""
                            ).upper()

                            value = condition.get("value")

                            self.validate_column(
                                column,
                                valid_columns
                            )

                            if operator not in allowed_operators:

                                raise ValueError(
                                    "Unsupported filter operator."
                                )

                            conditions.append(
                                sql.SQL("{} {} %s").format(
                                    sql.Identifier(column),
                                    sql.SQL(operator)
                                )
                            )

                            parameters.append(value)

                        query = sql.SQL("""
                            SELECT *
                            FROM {}
                            WHERE {}
                            LIMIT %s;
                        """).format(
                            table,
                            sql.SQL(" AND ").join(conditions)
                        )

                        parameters.append(self.max_limit)

                        cursor.execute(query, parameters)

                        records = cursor.fetchall()

                    # SORT
                    elif operation == "SORT":

                        order_by = query_plan.get("order_by")

                        if isinstance(order_by, dict):

                            column = order_by.get("column")

                            direction = order_by.get(
                                "direction", "ASC"
                            ).upper()

                        else:

                            column = order_by

                            direction = query_plan.get(
                                "direction", "ASC"
                            ).upper()

                        self.validate_column(
                            column,
                            valid_columns
                        )

                        if direction not in ("ASC", "DESC"):

                            raise ValueError(
                                "Invalid sort direction."
                            )

                        limit = self.validate_limit(
                            query_plan.get("limit")
                        )

                        query = sql.SQL("""
                            SELECT *
                            FROM {}
                            ORDER BY {} {}
                            LIMIT %s;
                        """).format(
                            table,
                            sql.Identifier(column),
                            sql.SQL(direction)
                        )

                        cursor.execute(query, (limit,))

                        records = cursor.fetchall()

                    else:

                        raise ValueError(
                            f"Unsupported operation: {operation}"
                        )

            return {
                "status": "SUCCESS",
                "table": table_name,
                "operation": operation,
                "count": len(records),
                "records": self.serialize_records(records)
            }

        except (
            psycopg.Error,
            ValueError,
            TypeError,
            AttributeError
        ) as error:

            return {
                "status": "FAILED",
                "message": str(error)
            }

    # ==================================================
    # CUSTOMER MANAGEMENT
    # ==================================================

    def create_customer(
        self,
        customer_name,
        email,
        phone="",
        address=""
    ):

        try:

            customer_name = customer_name.strip()
            email = email.strip()

            if not customer_name:

                return {
                    "status": "FAILED",
                    "message": "Customer name is required."
                }

            if not email:

                return {
                    "status": "FAILED",
                    "message": "Customer email is required."
                }

            with self.get_write_connection() as connection:

                with connection.cursor(
                    row_factory=dict_row
                ) as cursor:

                    cursor.execute("""
                        INSERT INTO public.customers (
                            customer_name,
                            email,
                            phone,
                            address
                        )
                        VALUES (%s, %s, %s, %s)
                        RETURNING
                            customer_id,
                            customer_name,
                            email,
                            phone,
                            address,
                            created_at;
                    """, (
                        customer_name,
                        email,
                        phone or None,
                        address or None
                    ))

                    customer = cursor.fetchone()

            return {
                "status": "SUCCESS",
                "message": "Customer created successfully.",
                "customer": self.serialize_records(
                    [customer]
                )[0]
            }

        except psycopg.errors.UniqueViolation:

            return {
                "status": "FAILED",
                "message": "A customer with this email already exists."
            }

        except psycopg.Error as error:

            return {
                "status": "FAILED",
                "error_type": type(error).__name__,
                "message": str(error)
            }

    # ==================================================
    # GET CUSTOMER BY ID
    # ==================================================

    def get_customer(self, customer_id):

        try:

            with self.get_connection() as connection:

                with connection.cursor(
                    row_factory=dict_row
                ) as cursor:

                    cursor.execute("""
                        SELECT
                            customer_id,
                            customer_name,
                            email,
                            phone,
                            address,
                            created_at
                        FROM public.customers
                        WHERE customer_id = %s;
                    """, (customer_id,))

                    customer = cursor.fetchone()

            if customer is None:

                return {
                    "status": "NOT_FOUND",
                    "message": f"Customer {customer_id} was not found."
                }

            return {
                "status": "SUCCESS",
                "customer": self.serialize_records(
                    [customer]
                )[0]
            }

        except psycopg.Error as error:

            return {
                "status": "FAILED",
                "message": str(error)
            }

    # ==================================================
    # GET CUSTOMER BY NAME
    # ==================================================

    def get_customer_by_name(self, customer_name):

        try:

            customer_name = customer_name.strip()

            if not customer_name:

                return {
                    "status": "FAILED",
                    "message": "Customer name is required."
                }

            with self.get_connection() as connection:

                with connection.cursor(
                    row_factory=dict_row
                ) as cursor:

                    cursor.execute("""
                        SELECT
                            customer_id,
                            customer_name,
                            email,
                            phone,
                            address,
                            created_at
                        FROM public.customers
                        WHERE customer_name ILIKE %s
                        ORDER BY customer_id
                        LIMIT %s;
                    """, (
                        f"%{customer_name}%",
                        self.max_limit
                    ))

                    customers = cursor.fetchall()

            if not customers:

                return {
                    "status": "NOT_FOUND",
                    "message": f"No customer found for '{customer_name}'.",
                    "count": 0,
                    "customers": []
                }

            return {
                "status": "SUCCESS",
                "count": len(customers),
                "customers": self.serialize_records(customers)
            }

        except psycopg.Error as error:

            return {
                "status": "FAILED",
                "message": str(error)
            }

    # ==================================================
    # LIST CUSTOMERS
    # ==================================================

    def list_customers(self):

        try:

            with self.get_connection() as connection:

                with connection.cursor(
                    row_factory=dict_row
                ) as cursor:

                    cursor.execute("""
                        SELECT
                            customer_id,
                            customer_name,
                            email,
                            phone,
                            address,
                            created_at
                        FROM public.customers
                        ORDER BY customer_id
                        LIMIT %s;
                    """, (self.max_limit,))

                    customers = cursor.fetchall()

            return {
                "status": "SUCCESS",
                "count": len(customers),
                "customers": self.serialize_records(customers)
            }

        except psycopg.Error as error:

            return {
                "status": "FAILED",
                "message": str(error)
            }

    # ==================================================
    # CREATE INSURANCE POLICY
    # ==================================================

    def create_policy(
        self,
        customer_id,
        policy_name,
        policy_type,
        premium_amount,
        coverage_amount,
        start_date,
        expiry_date
    ):

        try:

            if customer_id <= 0:

                return {
                    "status": "FAILED",
                    "message": "Invalid customer ID."
                }

            if not policy_name.strip():

                return {
                    "status": "FAILED",
                    "message": "Policy name is required."
                }

            if not policy_type.strip():

                return {
                    "status": "FAILED",
                    "message": "Policy type is required."
                }

            premium = Decimal(str(premium_amount))
            coverage = Decimal(str(coverage_amount))

            if not premium.is_finite() or not coverage.is_finite():

                return {
                    "status": "FAILED",
                    "message": "Amounts must be finite numbers."
                }

            if premium <= 0 or coverage <= 0:

                return {
                    "status": "FAILED",
                    "message": "Amounts must be greater than zero."
                }

            parsed_start = date.fromisoformat(str(start_date))
            parsed_expiry = date.fromisoformat(str(expiry_date))

            if parsed_expiry < parsed_start:

                return {
                    "status": "FAILED",
                    "message": "Expiry date cannot be earlier than start date."
                }

            with self.get_write_connection() as connection:

                with connection.cursor(
                    row_factory=dict_row
                ) as cursor:

                    cursor.execute("""
                        INSERT INTO public.policies (
                            customer_id,
                            policy_name,
                            policy_type,
                            premium_amount,
                            coverage_amount,
                            start_date,
                            expiry_date
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        RETURNING
                            policy_id,
                            customer_id,
                            policy_name,
                            policy_type,
                            premium_amount,
                            coverage_amount,
                            start_date,
                            expiry_date,
                            status,
                            created_at;
                    """, (
                        customer_id,
                        policy_name,
                        policy_type,
                        premium,
                        coverage,
                        parsed_start,
                        parsed_expiry
                    ))

                    policy = cursor.fetchone()

            return {
                "status": "SUCCESS",
                "message": "Policy created successfully.",
                "policy": self.serialize_records(
                    [policy]
                )[0]
            }

        except psycopg.errors.ForeignKeyViolation:

            return {
                "status": "FAILED",
                "message": (
                    f"Customer ID {customer_id} does not exist. "
                    "Create the customer before creating a policy."
                )
            }

        except (
            psycopg.Error,
            InvalidOperation,
            TypeError,
            ValueError
        ) as error:

            return {
                "status": "FAILED",
                "error_type": type(error).__name__,
                "message": str(error)
            }

    # ==================================================
    # GET POLICY BY ID
    # ==================================================

    def get_policy(self, policy_id):

        try:

            with self.get_connection() as connection:

                with connection.cursor(
                    row_factory=dict_row
                ) as cursor:

                    cursor.execute("""
                        SELECT
                            p.policy_id,
                            p.customer_id,
                            c.customer_name,
                            p.policy_name,
                            p.policy_type,
                            p.premium_amount,
                            p.coverage_amount,
                            p.start_date,
                            p.expiry_date,
                            p.status,
                            p.created_at
                        FROM public.policies AS p
                        INNER JOIN public.customers AS c
                            ON c.customer_id = p.customer_id
                        WHERE p.policy_id = %s;
                    """, (policy_id,))

                    policy = cursor.fetchone()

            if policy is None:

                return {
                    "status": "NOT_FOUND",
                    "message": f"Policy {policy_id} was not found."
                }

            return {
                "status": "SUCCESS",
                "policy": self.serialize_records(
                    [policy]
                )[0]
            }

        except psycopg.Error as error:

            return {
                "status": "FAILED",
                "message": str(error)
            }

    # ==================================================
    # LIST ALL POLICIES
    # ==================================================

    def list_policies(self):

        try:

            with self.get_connection() as connection:

                with connection.cursor(
                    row_factory=dict_row
                ) as cursor:

                    cursor.execute("""
                        SELECT
                            p.policy_id,
                            p.customer_id,
                            c.customer_name,
                            p.policy_name,
                            p.policy_type,
                            p.premium_amount,
                            p.coverage_amount,
                            p.start_date,
                            p.expiry_date,
                            p.status,
                            p.created_at
                        FROM public.policies AS p
                        INNER JOIN public.customers AS c
                            ON c.customer_id = p.customer_id
                        ORDER BY p.policy_id
                        LIMIT %s;
                    """, (self.max_limit,))

                    policies = cursor.fetchall()

            return {
                "status": "SUCCESS",
                "count": len(policies),
                "policies": self.serialize_records(policies)
            }

        except psycopg.Error as error:

            return {
                "status": "FAILED",
                "message": str(error)
            }

    # ==================================================
    # GET POLICIES BY CUSTOMER ID
    # ==================================================

    def get_customer_policies(self, customer_id):

        try:

            with self.get_connection() as connection:

                with connection.cursor(
                    row_factory=dict_row
                ) as cursor:

                    cursor.execute("""
                        SELECT
                            p.policy_id,
                            p.customer_id,
                            c.customer_name,
                            p.policy_name,
                            p.policy_type,
                            p.premium_amount,
                            p.coverage_amount,
                            p.start_date,
                            p.expiry_date,
                            p.status,
                            p.created_at
                        FROM public.policies AS p
                        INNER JOIN public.customers AS c
                            ON c.customer_id = p.customer_id
                        WHERE p.customer_id = %s
                        ORDER BY p.policy_id
                        LIMIT %s;
                    """, (
                        customer_id,
                        self.max_limit
                    ))

                    policies = cursor.fetchall()

                    if not policies:

                        cursor.execute("""
                            SELECT 1
                            FROM public.customers
                            WHERE customer_id = %s;
                        """, (customer_id,))

                        customer_exists = (
                            cursor.fetchone() is not None
                        )

                    else:

                        customer_exists = True

            if not customer_exists:

                return {
                    "status": "NOT_FOUND",
                    "message": f"Customer {customer_id} was not found.",
                    "count": 0,
                    "policies": []
                }

            return {
                "status": "SUCCESS",
                "customer_id": customer_id,
                "count": len(policies),
                "policies": self.serialize_records(policies)
            }

        except psycopg.Error as error:

            return {
                "status": "FAILED",
                "message": str(error)
            }

    # ==================================================
    # COLUMN VALIDATION
    # ==================================================

    @staticmethod
    def validate_column(column, valid_columns):

        if not column or column not in valid_columns:

            raise ValueError(
                f"Invalid column: {column}"
            )

    # ==================================================
    # LIMIT VALIDATION
    # ==================================================

    def validate_limit(self, limit):

        if limit is None:
            return self.max_limit

        try:

            limit = int(limit)

        except (ValueError, TypeError):

            raise ValueError(
                "Limit must be an integer."
            )

        if limit < 1:

            raise ValueError(
                "Limit must be positive."
            )

        return min(limit, self.max_limit)