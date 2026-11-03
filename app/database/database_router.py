import psycopg
from config.settings import Settings


class DatabaseRouter:

    def get_connection(self, database_name):

        if database_name not in Settings.DATABASES:
            raise ValueError(
                f"Database '{database_name}' is not configured."
            )

        config = Settings.DATABASES[database_name]

        return psycopg.connect(
            host=config["host"],
            port=config["port"],
            dbname=config["dbname"],
            user=config["user"],
            password=config["password"],
            connect_timeout=5
        )

    def validate_table(self, database_name, table_name):

        if database_name not in Settings.ALLOWED_TABLES:
            raise ValueError("Database is not permitted.")

        allowed_tables = Settings.ALLOWED_TABLES[database_name]

        if table_name not in allowed_tables:
            raise ValueError(
                f"Table '{table_name}' is not permitted."
            )

        return True

    def get_databases(self):

        return list(Settings.DATABASES.keys())

    def get_tables(self, database_name):

        if database_name not in Settings.ALLOWED_TABLES:
            raise ValueError("Database is not permitted.")

        return Settings.ALLOWED_TABLES[database_name]