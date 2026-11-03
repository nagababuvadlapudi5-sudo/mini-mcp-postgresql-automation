from typing import Any
import traceback

from mcp.server.mcpserver import MCPServer
from app.database.postgres import PostgreSQLDatabase


# =========================================================
# INITIALIZATION
# =========================================================

mcp = MCPServer("PostgreSQL Mini MCP")
database = PostgreSQLDatabase()


# =========================================================
# COMMON ERROR HANDLER
# =========================================================

def handle_error(error: Exception) -> dict[str, Any]:
    traceback.print_exc()

    return {
        "status": "FAILED",
        "error_type": type(error).__name__,
        "message": str(error)
    }


# =========================================================
# DATABASE CONNECTION
# =========================================================

@mcp.tool()
def check_database_connection() -> dict[str, Any]:
    """Check PostgreSQL database connection."""

    print("\n[MCP] Checking database connection...")

    try:
        result = database.check_connection()
        print(result)
        return result

    except Exception as error:
        return handle_error(error)


# =========================================================
# DATABASE TABLE INFORMATION
# =========================================================

@mcp.tool()
def list_tables() -> dict[str, Any]:
    """List all tables in PostgreSQL."""

    print("\n[MCP] Listing database tables...")

    try:
        result = database.list_tables()
        print(result)
        return result

    except Exception as error:
        return handle_error(error)


@mcp.tool()
def get_table_schema(table_name: str) -> dict[str, Any]:
    """Get the schema of a specific table."""

    print(f"\n[MCP] Getting schema for: {table_name}")

    try:
        result = database.get_table_schema(table_name)
        print(result)
        return result

    except Exception as error:
        return handle_error(error)


# =========================================================
# READ-ONLY QUERY SUPPORT
# =========================================================

@mcp.tool()
def execute_read_query(
    query_plan: dict[str, Any]
) -> dict[str, Any]:
    """Execute a read-only PostgreSQL query."""

    print("\n[MCP] Received query plan:")
    print(query_plan)

    try:
        result = database.execute_read_query(query_plan)
        print("[MCP] Database response:", result)
        return result

    except Exception as error:
        return handle_error(error)


# =========================================================
# CUSTOMER MANAGEMENT
# =========================================================

@mcp.tool()
def create_customer(
    customer_name: str,
    email: str,
    phone: str = "",
    address: str = ""
) -> dict[str, Any]:
    """Create a new customer."""

    print("\n[MCP] Creating customer:", customer_name)

    try:
        if not customer_name.strip():
            return {
                "status": "FAILED",
                "message": "Customer name is required."
            }

        if not email.strip():
            return {
                "status": "FAILED",
                "message": "Customer email is required."
            }

        return database.create_customer(
            customer_name=customer_name,
            email=email,
            phone=phone,
            address=address
        )

    except Exception as error:
        return handle_error(error)


@mcp.tool()
def get_customer(customer_id: int) -> dict[str, Any]:
    """Get customer details using customer ID."""

    print(f"\n[MCP] Getting customer: {customer_id}")

    try:
        if customer_id <= 0:
            return {
                "status": "FAILED",
                "message": "Invalid customer ID."
            }

        return database.get_customer(customer_id)

    except Exception as error:
        return handle_error(error)


@mcp.tool()
def get_customer_by_name(
    customer_name: str
) -> dict[str, Any]:
    """Search for a customer by name."""

    print(f"\n[MCP] Searching customer: {customer_name}")

    try:
        if not customer_name.strip():
            return {
                "status": "FAILED",
                "message": "Customer name is required."
            }

        return database.get_customer_by_name(customer_name)

    except Exception as error:
        return handle_error(error)


@mcp.tool()
def list_customers() -> dict[str, Any]:
    """Retrieve all customers."""

    print("\n[MCP] Listing all customers...")

    try:
        return database.list_customers()

    except Exception as error:
        return handle_error(error)


# =========================================================
# POLICY MANAGEMENT
# =========================================================

@mcp.tool()
def create_policy(
    customer_id: int,
    policy_name: str,
    policy_type: str,
    premium_amount: float,
    coverage_amount: float,
    start_date: str,
    expiry_date: str
) -> dict[str, Any]:
    """Create a new insurance policy for an existing customer."""

    print("\n[MCP] Creating insurance policy...")
    print("Customer ID:", customer_id)

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

        if premium_amount <= 0:
            return {
                "status": "FAILED",
                "message": "Premium must be greater than zero."
            }

        if coverage_amount <= 0:
            return {
                "status": "FAILED",
                "message": "Coverage must be greater than zero."
            }

        return database.create_policy(
            customer_id=customer_id,
            policy_name=policy_name,
            policy_type=policy_type,
            premium_amount=premium_amount,
            coverage_amount=coverage_amount,
            start_date=start_date,
            expiry_date=expiry_date
        )

    except Exception as error:
        return handle_error(error)


@mcp.tool()
def get_policy(policy_id: int) -> dict[str, Any]:
    """Get policy details using policy ID."""

    print(f"\n[MCP] Getting policy: {policy_id}")

    try:
        if policy_id <= 0:
            return {
                "status": "FAILED",
                "message": "Invalid policy ID."
            }

        return database.get_policy(policy_id)

    except Exception as error:
        return handle_error(error)


@mcp.tool()
def list_policies() -> dict[str, Any]:
    """Retrieve all insurance policies."""

    print("\n[MCP] Listing all policies...")

    try:
        return database.list_policies()

    except Exception as error:
        return handle_error(error)


@mcp.tool()
def get_customer_policies(
    customer_id: int
) -> dict[str, Any]:
    """Retrieve all policies belonging to a customer."""

    print(f"\n[MCP] Getting policies for customer: {customer_id}")

    try:
        if customer_id <= 0:
            return {
                "status": "FAILED",
                "message": "Invalid customer ID."
            }

        return database.get_customer_policies(customer_id)

    except Exception as error:
        return handle_error(error)


# =========================================================
# MCP SERVER STARTUP
# =========================================================

if __name__ == "__main__":

    print("\n===================================")
    print(" Starting PostgreSQL Mini MCP")
    print("===================================")

    print("Available Modules:")
    print("1. Database Connection")
    print("2. Database Table Information")
    print("3. Read-Only SQL Queries")
    print("4. Customer Management")
    print("5. Policy Management")

    mcp.run()