import asyncio
import json
import re
import sys

from pathlib import Path

from app.client.mcp_client import PostgreSQLMCPClient


class PostgreSQLMCPHost:

    def __init__(self):
        self.client_manager = PostgreSQLMCPClient()
        self.available_tables = []
        self.available_tools = set()
        self.tool_schemas = {}

    # =====================================================
    # START APPLICATION
    # =====================================================

    async def run(self):

        client = self.client_manager.create_client()

        async with client:

            print("\n" + "=" * 50)
            print("          POSTGRESQL MINI MCP")
            print("=" * 50)

            # Discover MCP tools
            await self.discover_tools(client)

            # Discover database tables
            await self.discover_tables(client)

            # Main menu
            while True:

                self.show_main_menu()

                choice = input("\nAsk anything: ").strip()

                if choice == "1":
                    await self.student_menu(client)

                elif choice == "2":
                    await self.teacher_menu(client)

                elif choice == "3":
                    await self.customer_menu(client)

                elif choice == "4":
                    await self.policy_menu(client)

                elif choice == "5":
                    await self.more_details_menu(client)

                elif choice == "6":
                    await self.feedback_menu(client)

                elif choice == "7":
                    await self.ask_anything_menu(client)

                elif choice == "8":
                    await self.schedule_menu()

                elif choice == "9":
                    print("\nApplication stopped.")
                    break

                else:
                    print("\nInvalid choice. Please select 1-9.")

    # =====================================================
    # MAIN MENU
    # =====================================================

    def show_main_menu(self):

        print("\n")
        print("=" * 50)
        print("              MAIN MENU")
        print("=" * 50)

        print("1. Student Details")
        print("2. Teacher Details")
        print("3. Customer Details")
        print("4. Policy Details")
        print("5. More Details")
        print("6. Feedback")
        print("7. Ask Anything")
        print("8. Schedule a Query")
        print("9. Exit")

        print("=" * 50)

    # =====================================================
    # DISCOVER MCP TOOLS
    # =====================================================

    async def discover_tools(self, client):

        tools_response = await client.list_tools()

        self.available_tools = {
            tool.name for tool in tools_response.tools
        }

        self.tool_schemas = {
            tool.name: getattr(tool, "inputSchema", {}) or {}
            for tool in tools_response.tools
        }

        print("\nMCP tools connected successfully.")

        print("\nAVAILABLE MCP TOOLS:")

        for tool_name in sorted(self.available_tools):
            print(" -", tool_name)

    # =====================================================
    # DISCOVER DATABASE TABLES
    # =====================================================

    async def discover_tables(self, client):

        if "list_tables" not in self.available_tools:

            print("\nWARNING: list_tables tool not registered.")
            return

        response = await client.call_tool(
            "list_tables",
            {}
        )

        result = self.get_result(response)

        if isinstance(result, dict):

            if result.get("status") == "SUCCESS":

                self.available_tables = result.get(
                    "tables", []
                )

                print("\nAVAILABLE DATABASE TABLES:")

                for table in self.available_tables:
                    print(" -", table)

    # =====================================================
    # STUDENT MENU
    # =====================================================

    async def student_menu(self, client):

        print("\n========== STUDENT DETAILS ==========")

        print("1. View All Students")
        print("2. Search Student")
        print("3. Count Students")
        print("4. Back")

        choice = input("\nAsk anything : ").strip()

        if choice == "1":
            await self.process_prompt(
                client,
                "show all students"
            )

        elif choice == "2":

            name = input("Enter student name: ").strip()

            await self.process_prompt(
                client,
                f"find {name} in students"
            )

        elif choice == "3":
            await self.process_prompt(
                client,
                "count students"
            )

        elif choice == "4":
            return

        else:
            print("\nInvalid choice.")

    # =====================================================
    # TEACHER MENU
    # =====================================================

    async def teacher_menu(self, client):

        print("\n========== TEACHER DETAILS ==========")

        print("1. View All Teachers")
        print("2. Search Teacher")
        print("3. Count Teachers")
        print("4. Back")

        choice = input("\nEnter choice: ").strip()

        if choice == "1":

            await self.process_prompt(
                client,
                "show all teachers"
            )

        elif choice == "2":

            name = input("Enter teacher name: ").strip()

            await self.process_prompt(
                client,
                f"find {name} in teachers"
            )

        elif choice == "3":

            await self.process_prompt(
                client,
                "count teachers"
            )

        elif choice == "4":
            return

        else:
            print("\nInvalid choice.")

    # =====================================================
    # CUSTOMER MENU
    # =====================================================

    async def customer_menu(self, client):

        while True:

            print("\n========== CUSTOMER DETAILS ==========")

            print("1. Add Customer")
            print("2. View Customer")
            print("3. View All Customers")
            print("4. Back")

            choice = input("\nEnter choice: ").strip()

            if choice == "1":

                await self.create_customer_menu(client)

            elif choice == "2":

                await self.get_customer_menu(client)

            elif choice == "3":

                await self.call_tool(
                    client,
                    "list_customers",
                    {}
                )

            elif choice == "4":
                break

            else:
                print("\nInvalid choice.")

    # =====================================================
    # CREATE CUSTOMER
    # =====================================================

    async def create_customer_menu(self, client):

        print("\n========== ADD CUSTOMER ==========")

        customer_name = input(
            "Customer Name: "
        ).strip()

        email = input(
            "Email: "
        ).strip()

        phone = input(
            "Phone: "
        ).strip()

        address = input(
            "Address: "
        ).strip()

        if not customer_name or not email:

            print("\nCustomer name and email are required.")
            return

        arguments = {
            "customer_name": customer_name,
            "email": email,
            "phone": phone,
            "address": address
        }

        await self.call_tool(
            client,
            "create_customer",
            arguments
        )

    # =====================================================
    # GET CUSTOMER
    # =====================================================

    async def get_customer_menu(self, client):

        print("\n========== VIEW CUSTOMER ==========")

        print("1. Search by Customer ID")
        print("2. Search by Customer Name")

        choice = input("\nEnter choice: ").strip()

        if choice == "1":

            customer_id = input(
                "Enter Customer ID: "
            ).strip()

            if not customer_id.isdigit():
                print("\nCustomer ID must be numeric.")
                return

            await self.call_tool(
                client,
                "get_customer",
                {
                    "customer_id": int(customer_id)
                }
            )

        elif choice == "2":

            customer_name = input(
                "Enter Customer Name: "
            ).strip()

            await self.call_tool(
                client,
                "get_customer_by_name",
                {
                    "customer_name": customer_name
                }
            )

        else:
            print("\nInvalid choice.")

    # =====================================================
    # POLICY MENU
    # =====================================================

    async def policy_menu(self, client):

        while True:

            print("\n========== POLICY DETAILS ==========")

            print("1. Add Policy")
            print("2. View Policy")
            print("3. View All Policies")
            print("4. View Customer Policies")
            print("5. Back")

            choice = input("\nEnter choice: ").strip()

            if choice == "1":

                await self.create_policy_menu(client)

            elif choice == "2":

                await self.get_policy_menu(client)

            elif choice == "3":

                await self.call_tool(
                    client,
                    "list_policies",
                    {}
                )

            elif choice == "4":

                await self.get_customer_policies_menu(client)

            elif choice == "5":
                break

            else:
                print("\nInvalid choice.")

    # =====================================================
    # CREATE POLICY
    # =====================================================

    async def create_policy_menu(self, client):

        print("\n========== ADD POLICY ==========")

        customer_id = input(
            "Customer ID: "
        ).strip()

        policy_name = input(
            "Policy Name: "
        ).strip()

        policy_type = input(
            "Policy Type: "
        ).strip()

        premium_amount = input(
            "Premium Amount: "
        ).strip()

        coverage_amount = input(
            "Coverage Amount: "
        ).strip()

        start_date = input(
            "Start Date (YYYY-MM-DD): "
        ).strip()

        expiry_date = input(
            "Expiry Date (YYYY-MM-DD): "
        ).strip()

        try:

            if not customer_id.isdigit():
                raise ValueError("Customer ID must be numeric.")

            premium = float(premium_amount)
            coverage = float(coverage_amount)

            if premium <= 0 or coverage <= 0:
                raise ValueError(
                    "Premium and coverage must be greater than zero."
                )

        except ValueError as error:

            print(f"\nInvalid input: {error}")
            return

        arguments = {
            "customer_id": int(customer_id),
            "policy_name": policy_name,
            "policy_type": policy_type,
            "premium_amount": premium,
            "coverage_amount": coverage,
            "start_date": start_date,
            "expiry_date": expiry_date
        }

        await self.call_tool(
            client,
            "create_policy",
            arguments
        )

    # =====================================================
    # GET POLICY
    # =====================================================

    async def get_policy_menu(self, client):

        policy_id = input(
            "\nEnter Policy ID: "
        ).strip()

        if not policy_id.isdigit():

            print("\nPolicy ID must be numeric.")
            return

        await self.call_tool(
            client,
            "get_policy",
            {
                "policy_id": int(policy_id)
            }
        )

    # =====================================================
    # GET CUSTOMER POLICIES
    # =====================================================

    async def get_customer_policies_menu(self, client):

        customer_id = input(
            "\nEnter Customer ID: "
        ).strip()

        if not customer_id.isdigit():

            print("\nCustomer ID must be numeric.")
            return

        await self.call_tool(
            client,
            "get_customer_policies",
            {
                "customer_id": int(customer_id)
            }
        )

    # =====================================================
    # MORE DETAILS
    # =====================================================

    async def more_details_menu(self, client):

        print("\n========== MORE DETAILS ==========")

        print("1. List Database Tables")
        print("2. Describe Table")
        print("3. Database Connection Status")
        print("4. Back")

        choice = input("\nEnter choice: ").strip()

        if choice == "1":

            await self.discover_tables(client)

        elif choice == "2":

            table_name = input(
                "Enter Table Name: "
            ).strip()

            await self.process_prompt(
                client,
                f"describe {table_name}"
            )

        elif choice == "3":

            await self.call_tool(
                client,
                "check_database_connection",
                {}
            )

        elif choice == "4":
            return

        else:
            print("\nInvalid choice.")

    # =====================================================
    # FEEDBACK MENU
    # =====================================================

    async def feedback_menu(self, client):

        print("\n========== FEEDBACK ==========")

        feedback_tools = [
            name for name in self.available_tools
            if "feedback" in name.lower()
        ]

        if not feedback_tools:

            print(
                "\nNo Feedback MCP tool is registered."
            )

            print(
                "Register your existing Feedback tool in mcp_server.py."
            )

            return

        if len(feedback_tools) == 1:

            tool_name = feedback_tools[0]

        else:

            print("\nAvailable Feedback tools:")

            for index, name in enumerate(
                feedback_tools, start=1
            ):
                print(f"{index}. {name}")

            choice = input("\nSelect tool: ").strip()

            if not choice.isdigit():
                print("\nInvalid choice.")
                return

            index = int(choice) - 1

            if index < 0 or index >= len(feedback_tools):
                print("\nInvalid choice.")
                return

            tool_name = feedback_tools[index]

        arguments = self.collect_tool_arguments(tool_name)

        await self.call_tool(
            client,
            tool_name,
            arguments
        )

    # =====================================================
    # COLLECT TOOL ARGUMENTS DYNAMICALLY
    # =====================================================

    def collect_tool_arguments(self, tool_name):

        schema = self.tool_schemas.get(
            tool_name, {}
        )

        properties = schema.get(
            "properties", {}
        )

        required = schema.get(
            "required", []
        )

        arguments = {}

        print(f"\nEnter details for {tool_name}:")

        for field, details in properties.items():

            description = details.get(
                "description", field
            )

            value = input(
                f"{description}: "
            ).strip()

            if field in required and not value:

                raise ValueError(
                    f"{field} is required."
                )

            if value:

                arguments[field] = value

        return arguments

    # =====================================================
    # ASK ANYTHING
    # =====================================================

    async def ask_anything_menu(self, client):

        print("\n========== ASK ANYTHING ==========")

        print("Examples:")
        print("- Show all students")
        print("- Show all teachers")
        print("- Find Ravi in students")
        print("- Count students")
        print("- Describe customers")
        print("- List all tables")

        prompt = input(
            "\nAsk anything: "
        ).strip()

        if prompt:

            await self.process_prompt(
                client,
                prompt
            )

    # =====================================================
    # SCHEDULER MENU
    # =====================================================

    async def schedule_menu(self):

        print("\n========== SCHEDULE A QUERY ==========")

        print("1. Start Existing Scheduler")
        print("2. Back")

        choice = input("\nEnter choice: ").strip()

        if choice == "1":

            print("\nStarting existing scheduler.py...")

            project_root = Path(__file__).resolve().parents[2]

            try:

                process = await asyncio.create_subprocess_exec(
                    sys.executable,
                    "-m",
                    "app.schedular.scheduler",
                    cwd=str(project_root)
                )

                await process.wait()

                if process.returncode != 0:

                    print(
                        "\nScheduler exited with an error."
                    )

            except Exception as error:

                print(
                    f"\nUnable to start scheduler: {error}"
                )

        elif choice == "2":
            return

        else:
            print("\nInvalid choice.")

    # =====================================================
    # PROCESS NATURAL LANGUAGE PROMPT
    # =====================================================

    async def process_prompt(self, client, prompt):

        prompt_lower = prompt.lower().strip()

        # Refresh database tables
        if any(word in prompt_lower for word in [
            "refresh tables",
            "reload tables",
            "discover tables"
        ]):

            await self.discover_tables(client)
            return

        # Database connection
        if "database status" in prompt_lower:

            await self.call_tool(
                client,
                "check_database_connection",
                {}
            )
            return

        # Identify operation
        operation = self.identify_operation(
            prompt_lower
        )

        if not operation:

            print("\nUnable to identify operation.")
            return

        # List tables
        if operation == "LIST_TABLES":

            await self.discover_tables(client)
            return

        # Identify table
        table_name = self.identify_table(
            prompt_lower
        )

        if not table_name:

            print("\nUnable to identify requested table.")

            print(
                "Available tables:",
                ", ".join(self.available_tables)
            )

            return

        # Describe table
        if operation == "DESCRIBE":

            await self.execute_tool(
                client,
                operation,
                table_name
            )
            return

        # Build query plan
        query_plan = self.build_query_plan(
            operation,
            table_name,
            prompt_lower
        )

        print("\nQUERY PLAN")

        print("Operation:", operation)
        print("Table:", table_name)

        await self.execute_tool(
            client,
            operation,
            table_name,
            query_plan
        )

    # =====================================================
    # IDENTIFY OPERATION
    # =====================================================

    def identify_operation(self, prompt):

        patterns = {

            "LIST_TABLES": [
                "list tables",
                "show tables",
                "available tables",
                "discover tables"
            ],

            "DESCRIBE": [
                "describe",
                "columns",
                "table structure",
                "schema of",
                "structure of"
            ],

            "COUNT": [
                "how many",
                "count",
                "total number",
                "number of"
            ],

            "DISTINCT": [
                "distinct",
                "unique values",
                "unique subjects"
            ],

            "GROUP_BY": [
                "group by",
                "department wise",
                "category wise",
                "subject wise"
            ],

            "AGGREGATE": [
                "average",
                "avg",
                "sum",
                "maximum",
                "minimum",
                "highest",
                "lowest"
            ],

            "SORT": [
                "sort",
                "order by",
                "ascending",
                "descending",
                "alphabetically",
                "highest first",
                "lowest first"
            ],

            "FILTER": [
                "greater than",
                "more than",
                "above",
                "less than",
                "below",
                "equal to",
                "where"
            ],

            "SEARCH": [
                "find",
                "search",
                "details",
                "looking for"
            ],

            "GET_ALL": [
                "show all",
                "get all",
                "display all",
                "list all",
                "show me",
                "display"
            ]
        }

        for operation, keywords in patterns.items():

            if any(word in prompt for word in keywords):

                return operation

        return None

    # =====================================================
    # IDENTIFY TABLE
    # =====================================================

    def identify_table(self, prompt):

        matched_tables = []

        for table in self.available_tables:

            table_lower = table.lower()

            if re.search(
                rf"\b{re.escape(table_lower)}\b",
                prompt
            ):

                matched_tables.append(table)

        if len(matched_tables) == 1:

            return matched_tables[0]

        if len(matched_tables) > 1:

            print("\nMultiple tables identified:")

            print(", ".join(matched_tables))

            return None

        return None

    # =====================================================
    # BUILD QUERY PLAN
    # =====================================================

    def build_query_plan(
        self,
        operation,
        table_name,
        prompt
    ):

        query_plan = {

            "operation": operation,
            "table_name": table_name,
            "filters": [],
            "columns": ["*"],
            "limit": 100,
            "order_by": None,
            "group_by": None,
            "aggregate": None,
            "distinct_column": None
        }

        if operation == "COUNT":

            query_plan["columns"] = ["COUNT(*)"]

        elif operation == "SEARCH":

            query_plan["search_text"] = prompt

        elif operation == "FILTER":

            query_plan["filters"] = self.extract_filters(
                prompt
            )

        elif operation == "SORT":

            query_plan["order_by"] = self.extract_sort(
                prompt
            )

        elif operation == "AGGREGATE":

            query_plan["aggregate"] = self.extract_aggregate(
                prompt
            )

        elif operation == "DISTINCT":

            query_plan["distinct_column"] = (
                self.extract_distinct_column(prompt)
            )

        elif operation == "GROUP_BY":

            query_plan["group_by"] = (
                self.extract_group_column(prompt)
            )

        return query_plan

    # =====================================================
    # EXTRACT FILTERS
    # =====================================================

    def extract_filters(self, prompt):

        filters = []

        patterns = [

            (r"(\w+)\s+(?:is\s+)?greater than\s+(\d+)", ">"),

            (r"(\w+)\s+(?:is\s+)?more than\s+(\d+)", ">"),

            (r"(\w+)\s+(?:is\s+)?above\s+(\d+)", ">"),

            (r"(\w+)\s+(?:is\s+)?less than\s+(\d+)", "<"),

            (r"(\w+)\s+(?:is\s+)?below\s+(\d+)", "<"),

            (r"(\w+)\s+(?:is\s+)?equal to\s+(\d+)", "=")
        ]

        for pattern, operator in patterns:

            match = re.search(pattern, prompt)

            if match:

                filters.append({

                    "column": match.group(1),
                    "operator": operator,
                    "value": int(match.group(2))
                })

                break

        return filters

    # =====================================================
    # EXTRACT SORT
    # =====================================================

    def extract_sort(self, prompt):

        match = re.search(
            r"(?:sort|order by)\s+(\w+)",
            prompt
        )

        if not match:
            return None

        direction = (

            "DESC"
            if "descending" in prompt or "highest first" in prompt
            else "ASC"
        )

        return {

            "column": match.group(1),
            "direction": direction
        }

    # =====================================================
    # EXTRACT AGGREGATE
    # =====================================================

    def extract_aggregate(self, prompt):

        functions = {

            "average": "AVG",
            "avg": "AVG",
            "sum": "SUM",
            "maximum": "MAX",
            "highest": "MAX",
            "minimum": "MIN",
            "lowest": "MIN"
        }

        for word, function in functions.items():

            if word in prompt:

                return {

                    "function": function,
                    "column": None
                }

        return None

    # =====================================================
    # EXTRACT DISTINCT COLUMN
    # =====================================================

    def extract_distinct_column(self, prompt):

        match = re.search(
            r"(?:distinct|unique)\s+(\w+)",
            prompt
        )

        if match:
            return match.group(1)

        return None

    # =====================================================
    # EXTRACT GROUP COLUMN
    # =====================================================

    def extract_group_column(self, prompt):

        patterns = [

            r"group by\s+(\w+)",
            r"(\w+)\s+wise"
        ]

        for pattern in patterns:

            match = re.search(pattern, prompt)

            if match:
                return match.group(1)

        return None

    # =====================================================
    # EXECUTE GENERIC READ QUERY
    # =====================================================

    async def execute_tool(
        self,
        client,
        operation,
        table_name,
        query_plan=None
    ):

        if "execute_read_query" not in self.available_tools:

            print("\nexecute_read_query MCP tool is not registered.")
            return

        arguments = {

            "query_plan": query_plan or {

                "operation": operation,
                "table_name": table_name
            }
        }

        await self.call_tool(
            client,
            "execute_read_query",
            arguments
        )

    # =====================================================
    # CALL MCP TOOL
    # =====================================================

    async def call_tool(
        self,
        client,
        tool_name,
        arguments
    ):

        if tool_name not in self.available_tools:

            print(f"\nMCP tool not registered: {tool_name}")
            print("Check mcp_server.py.")
            return

        try:

            print(f"\nCalling MCP tool: {tool_name}")

            response = await client.call_tool(
                tool_name,
                arguments
            )

            self.display_response(response)

        except Exception as error:

            print("\nMCP TOOL EXECUTION FAILED")
            print("Reason:", error)

    # =====================================================
    # PARSE MCP RESPONSE
    # =====================================================

    def get_result(self, response):

        result = getattr(
            response,
            "structured_content",
            None
        )

        if result is None:

            result = getattr(
                response,
                "structuredContent",
                None
            )

        if result is None:

            for item in getattr(response, "content", []):

                if hasattr(item, "text"):

                    try:

                        return json.loads(item.text)

                    except (ValueError, TypeError):
                        pass

        return result

    # =====================================================
    # DISPLAY RESPONSE
    # =====================================================

    def display_response(self, response):

        print("\n" + "=" * 50)
        print("           APPLICATION RESPONSE")
        print("=" * 50)

        is_error = getattr(
            response,
            "is_error",
            getattr(response, "isError", False)
        )

        if is_error:

            print("MCP TOOL EXECUTION FAILED")

            for item in getattr(response, "content", []):

                if hasattr(item, "text"):
                    print(item.text)

            return

        result = self.get_result(response)

        if result is None:

            print("No structured response received.")
            return

        if isinstance(result, dict):

            print(
                json.dumps(
                    result,
                    indent=4,
                    default=str
                )
            )

        else:

            print(result)

    # =====================================================
    # APPLICATION EXAMPLES
    # =====================================================

    def show_examples(self):

        examples = [

            "List all tables",
            "Describe teachers",
            "How many teachers?",
            "Show all students",
            "Find Ravi in students",
            "Show all customers",
            "Show all policies",
            "Count students"
        ]

        print("\nSUPPORTED REQUEST EXAMPLES:")

        for example in examples:
            print("-", example)


# =========================================================
# APPLICATION ENTRY POINT
# =========================================================

if __name__ == "__main__":

    host = PostgreSQLMCPHost()

    asyncio.run(host.run())