import asyncio
import json
import re
import uuid

from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger

from app.client.mcp_client import PostgreSQLMCPClient


# =========================================================
# CONFIGURATION
# =========================================================

TIMEZONE = ZoneInfo("Asia/Kolkata")

STUDENT_TABLE = "students"
TEACHER_TABLE = "teachersnum"
CUSTOMER_TABLE = "customers"
POLICY_TABLE = "policies"

ALLOWED_TABLES = {
    STUDENT_TABLE,
    TEACHER_TABLE,
    CUSTOMER_TABLE,
    POLICY_TABLE
}

FEEDBACK_FILE = Path(__file__).resolve().parent / "feedback.txt"

DEFAULT_LIMIT = 100


# =========================================================
# POSTGRESQL MCP SCHEDULER
# =========================================================

class PostgreSQLScheduler:

    def __init__(self):

        self.client_manager = PostgreSQLMCPClient()
        self.client = self.client_manager.create_client()

        self.scheduler = AsyncIOScheduler(
            timezone=TIMEZONE
        )

        self.available_tools = set()

    # =====================================================
    # INPUT HANDLER
    # =====================================================

    async def get_input(self, message):

        return await asyncio.to_thread(
            input,
            message
        )

    # =====================================================
    # APPLICATION START
    # =====================================================

    async def run(self):

        async with self.client:

            print("\n========================================")
            print("       POSTGRESQL MINI MCP APPLICATION")
            print("========================================")

            try:

                await self.discover_tools()

                connection_result = await self.call_tool(
                    "check_database_connection"
                )

                if (
                    not isinstance(connection_result, dict)
                    or connection_result.get("status") != "SUCCESS"
                ):

                    raise RuntimeError(
                        "PostgreSQL connection failed."
                    )

                print("\nPostgreSQL connection successful.")

                self.scheduler.start()

                print("APScheduler started successfully.")

                while True:

                    self.show_menu()

                    user_input = (
                        await self.get_input(
                            "\nAsk anything: "
                        )
                    ).strip()

                    if not user_input:

                        print("Please enter a valid option.")

                        continue

                    try:

                        should_exit = await self.handle_input(
                            user_input
                        )

                        if should_exit:
                            break

                    except Exception as error:

                        print(f"\nERROR: {error}")

            finally:

                if self.scheduler.running:

                    self.scheduler.shutdown(
                        wait=False
                    )

                    print("\nScheduler stopped.")

    # =====================================================
    # MAIN MENU
    # =====================================================

    def show_menu(self):

        print("\n==================================================")
        print("                    MAIN MENU")
        print("==================================================")
        print("1. Student Details")
        print("2. Teacher Details")
        print("3. Customer Details")
        print("4. Policy Details")
        print("5. More Details")
        print("6. Feedback")
        print("7. Ask Anything")
        print("8. Schedule a Query")
        print("9. Exit")
        print("==================================================")

    # =====================================================
    # CENTRAL INPUT ROUTER
    # =====================================================

    async def handle_input(self, user_input):

        command = user_input.strip().lower()

        if command in {"9", "exit", "quit"}:

            print("\nApplication closed.")

            return True

        menu_actions = {

            "1": self.show_students,
            "2": self.show_teachers,
            "3": self.show_customers,
            "4": self.show_policies,
            "5": self.show_more_details,
            "6": self.save_feedback,
            "8": self.schedule_query

        }

        if command in menu_actions:

            await menu_actions[command]()

            return False

        # Option 7: immediate database query
        if command == "7":

            await self.ask_anything()

            return False

        # Natural-language feedback
        if command in {
            "feedback",
            "give feedback",
            "submit feedback"
        }:

            await self.save_feedback()

            return False

        # Natural-language schedule request
        if self.is_schedule_request(command):

            await self.schedule_query(
                prompt=user_input
            )

            return False

        # Any other natural-language query executes immediately.
        # Do not automatically schedule merely because a time
        # appears in the user's question.

        await self.ask_anything(user_input)

        return False

    # =====================================================
    # MCP TOOL DISCOVERY
    # =====================================================

    async def discover_tools(self):

        result = await self.client.list_tools()

        self.available_tools = {
            tool.name
            for tool in result.tools
        }

        print("\nMCP tools discovered:")

        for tool_name in sorted(self.available_tools):

            print(f"  - {tool_name}")

    # =====================================================
    # MCP TOOL EXECUTION
    # =====================================================

    async def call_tool(
        self,
        tool_name,
        arguments=None
    ):

        if tool_name not in self.available_tools:

            raise ValueError(
                f"MCP tool not available: {tool_name}"
            )

        response = await self.client.call_tool(
            tool_name,
            arguments or {}
        )

        return self.display_response(response)

    # =====================================================
    # MCP RESPONSE HANDLER
    # =====================================================

    def display_response(self, response):

        data = None

        for attribute in (
            "structured_content",
            "structuredContent"
        ):

            data = getattr(
                response,
                attribute,
                None
            )

            if data is not None:
                break

        if data is None:

            content = (
                getattr(response, "content", []) or []
            )

            for item in content:

                response_text = getattr(
                    item,
                    "text",
                    None
                )

                if not response_text:
                    continue

                try:

                    data = json.loads(response_text)

                except json.JSONDecodeError:

                    data = {
                        "message": response_text
                    }

                break

        if data is None:

            data = {
                "message": str(response)
            }

        print("\n================ RESULT ================")

        print(
            json.dumps(
                data,
                indent=2,
                default=str
            )
        )

        print("========================================")

        return data

    # =====================================================
    # STUDENT DETAILS
    # =====================================================

    async def show_students(self):

        print("\nFetching student details...")

        await self.execute_query({

            "operation": "GET_ALL",
            "table_name": STUDENT_TABLE,
            "limit": DEFAULT_LIMIT

        })

    # =====================================================
    # TEACHER DETAILS
    # =====================================================

    async def show_teachers(self):

        print("\nFetching teacher details...")

        await self.execute_query({

            "operation": "GET_ALL",
            "table_name": TEACHER_TABLE,
            "limit": DEFAULT_LIMIT

        })

    # =====================================================
    # CUSTOMER DETAILS
    # =====================================================

    async def show_customers(self):

        print("\nFetching customer details...")

        await self.call_tool(
            "list_customers"
        )

    # =====================================================
    # POLICY DETAILS
    # =====================================================

    async def show_policies(self):

        print("\nFetching policy details...")

        await self.call_tool(
            "list_policies"
        )

    # =====================================================
    # MORE DETAILS / TABLE SCHEMA
    # =====================================================

    async def show_more_details(self):

        print("\n========== MORE DETAILS ==========")

        print("1. Students")
        print("2. Teachers")
        print("3. Customers")
        print("4. Policies")

        choice = (
            await self.get_input(
                "\nSelect table: "
            )
        ).strip()

        table_mapping = {

            "1": STUDENT_TABLE,
            "2": TEACHER_TABLE,
            "3": CUSTOMER_TABLE,
            "4": POLICY_TABLE

        }

        table_name = table_mapping.get(choice)

        if not table_name:

            print("Invalid selection.")

            return

        await self.call_tool(
            "get_table_schema",
            {
                "table_name": table_name
            }
        )

    # =====================================================
    # FEEDBACK
    # =====================================================

    async def save_feedback(self):

        feedback = (
            await self.get_input(
                "\nEnter your feedback: "
            )
        ).strip()

        if not feedback:

            print("Feedback cannot be empty.")

            return

        with FEEDBACK_FILE.open(
            "a",
            encoding="utf-8"
        ) as file:

            file.write(
                f"[{datetime.now(TIMEZONE)}] {feedback}\n"
            )

        print("\nFeedback saved successfully.")

    # =====================================================
    # TABLE IDENTIFICATION
    # =====================================================

    def identify_table(self, prompt):

        text = prompt.lower()

        if re.search(r"\bstudents?\b", text):

            return STUDENT_TABLE

        if re.search(r"\bteachers?\b", text):

            return TEACHER_TABLE

        if re.search(r"\bcustomers?\b", text):

            return CUSTOMER_TABLE

        if re.search(r"\bpolicies\b|\bpolicy\b", text):

            return POLICY_TABLE

        return None

    # =====================================================
    # SEARCH TEXT CLEANING
    # =====================================================

    def clean_search_text(self, prompt):

        text = prompt.lower()

        stop_words = {

            "show", "display", "get", "give",
            "fetch", "find", "search", "tell",
            "provide", "details", "detail",
            "records", "record", "information",
            "info", "data", "please", "me",
            "the", "for", "of", "what", "is",
            "are", "about", "all", "only",
            "and", "to", "named", "whose",
            "student", "students",
            "teacher", "teachers",
            "customer", "customers",
            "policy", "policies"

        }

        words = re.findall(
            r"[a-zA-Z0-9]+",
            text
        )

        meaningful_words = [

            word
            for word in words
            if word not in stop_words

        ]

        return " ".join(
            meaningful_words
        ).strip()

    # =====================================================
    # OPERATION IDENTIFICATION
    # =====================================================

    def identify_operation(self, prompt):

        text = prompt.lower()

        if any(
            word in text
            for word in (
                "describe",
                "schema",
                "columns",
                "structure"
            )
        ):

            return "DESCRIBE"

        if any(
            phrase in text
            for phrase in (
                "how many",
                "count",
                "total number",
                "number of"
            )
        ):

            return "COUNT"

        if any(
            word in text
            for word in (
                "search",
                "find",
                "whose",
                "named"
            )
        ):

            return "SEARCH"

        if self.clean_search_text(prompt):

            return "SEARCH"

        return "GET_ALL"

    # =====================================================
    # QUERY PLAN
    # =====================================================

    def build_query_plan(
        self,
        prompt,
        table_name,
        operation
    ):

        query_plan = {

            "operation": operation,
            "table_name": table_name,
            "limit": DEFAULT_LIMIT

        }

        if operation == "SEARCH":

            search_text = self.clean_search_text(
                prompt
            )

            if not search_text:

                print("Please provide a search value.")

                return None

            query_plan["search_text"] = search_text

        return query_plan

    # =====================================================
    # EXECUTE STUDENT / TEACHER QUERY
    # =====================================================

    async def execute_query(self, query_plan):

        table_name = query_plan.get(
            "table_name"
        )

        if table_name not in {
            STUDENT_TABLE,
            TEACHER_TABLE
        }:

            raise ValueError(
                "Generic read query is restricted to "
                "Student and Teacher tables."
            )

        return await self.call_tool(
            "execute_read_query",
            {
                "query_plan": query_plan
            }
        )

    # =====================================================
    # CUSTOMER / POLICY QUERY ROUTER
    # =====================================================

    async def execute_customer_policy_query(
        self,
        prompt,
        table_name
    ):

        text = prompt.lower()

        # ---------------------------------------------
        # CUSTOMER OPERATIONS
        # ---------------------------------------------

        if table_name == CUSTOMER_TABLE:

            if re.search(
                r"\b(all|list|every)\b",
                text
            ):

                return await self.call_tool(
                    "list_customers"
                )

            id_match = re.search(
                r"\bcustomer[\s_-]*(?:id)?[\s:#-]*(\d+)\b",
                text
            )

            if id_match:

                return await self.call_tool(
                    "get_customer",
                    {
                        "customer_id": int(id_match.group(1))
                    }
                )

            name = self.clean_search_text(
                prompt
            )

            if not name:

                return await self.call_tool(
                    "list_customers"
                )

            return await self.call_tool(
                "get_customer_by_name",
                {
                    "customer_name": name
                }
            )

        # ---------------------------------------------
        # POLICY OPERATIONS
        # ---------------------------------------------

        if table_name == POLICY_TABLE:

            customer_id_match = re.search(
                r"\bcustomer[\s_-]*(?:id)?[\s:#-]*(\d+)\b",
                text
            )

            if customer_id_match and (
                "customer" in text
            ):

                return await self.call_tool(
                    "get_customer_policies",
                    {
                        "customer_id": int(
                            customer_id_match.group(1)
                        )
                    }
                )

            policy_id_match = re.search(
                r"\bpolicy[\s_-]*(?:id)?[\s:#-]*(\d+)\b",
                text
            )

            if policy_id_match:

                return await self.call_tool(
                    "get_policy",
                    {
                        "policy_id": int(
                            policy_id_match.group(1)
                        )
                    }
                )

            return await self.call_tool(
                "list_policies"
            )

        raise ValueError(
            "Unsupported database table."
        )

    # =====================================================
    # ASK ANYTHING - IMMEDIATE EXECUTION
    # =====================================================

    async def ask_anything(self, prompt=None):

        if prompt is None:

            prompt = await self.get_input(
                "\nAsk your database question: "
            )

        prompt = prompt.strip()

        if not prompt:

            print("Question cannot be empty.")

            return

        table_name = self.identify_table(
            prompt
        )

        if not table_name:

            print(
                "\nPlease mention students, teachers, "
                "customers or policies."
            )

            return

        print("\nExecuting query immediately...")

        # Customer and Policy use dedicated MCP tools.
        if table_name in {
            CUSTOMER_TABLE,
            POLICY_TABLE
        }:

            await self.execute_customer_policy_query(
                prompt,
                table_name
            )

            return

        # Student and Teacher use generic read query.
        operation = self.identify_operation(
            prompt
        )

        if operation == "DESCRIBE":

            await self.call_tool(
                "get_table_schema",
                {
                    "table_name": table_name
                }
            )

            return

        query_plan = self.build_query_plan(
            prompt,
            table_name,
            operation
        )

        if query_plan:

            await self.execute_query(
                query_plan
            )

    # =====================================================
    # SCHEDULING INTENT
    # =====================================================

    def is_schedule_request(self, prompt):

        return bool(
            re.search(
                r"\b(schedule|remind me)\b",
                prompt,
                flags=re.IGNORECASE
            )
        )

    # =====================================================
    # TIME EXTRACTION
    # =====================================================

    def extract_time(self, prompt):

        patterns = [

            r"\b(1[0-2]|0?[1-9])"
            r"(?::([0-5]\d))?\s*(AM|PM)\b",

            r"\b([01]?\d|2[0-3]):([0-5]\d)\b"

        ]

        for index, pattern in enumerate(patterns):

            match = re.search(
                pattern,
                prompt,
                re.IGNORECASE
            )

            if not match:
                continue

            try:

                if index == 0:

                    hour = int(match.group(1))
                    minute = int(match.group(2) or 0)
                    period = match.group(3).upper()

                    parsed = datetime.strptime(
                        f"{hour}:{minute:02d} {period}",
                        "%I:%M %p"
                    )

                else:

                    parsed = datetime.strptime(
                        match.group(0),
                        "%H:%M"
                    )

                return parsed.strftime("%H:%M")

            except ValueError:

                continue

        return None

    # =====================================================
    # REMOVE TIME FROM PROMPT
    # =====================================================

    def remove_time_from_prompt(self, prompt):

        patterns = [

            r"\b(?:at\s+)?(?:1[0-2]|0?[1-9])"
            r"(?::[0-5]\d)?\s*(?:AM|PM)\b",

            r"\b(?:at\s+)?(?:[01]?\d|2[0-3]):[0-5]\d\b"

        ]

        for pattern in patterns:

            prompt = re.sub(
                pattern,
                " ",
                prompt,
                flags=re.IGNORECASE
            )

        return re.sub(
            r"\s+",
            " ",
            prompt
        ).strip()

    # =====================================================
    # DATE PARSING
    # =====================================================

    def parse_date(self, date_input):

        value = date_input.strip().lower()

        today = datetime.now(TIMEZONE).date()

        if value == "today":

            return today

        if value == "tomorrow":

            return today + timedelta(days=1)

        if value in {
            "day after tomorrow",
            "day after"
        }:

            return today + timedelta(days=2)

        formats = [

            "%Y-%m-%d",
            "%d-%m-%Y",
            "%d/%m/%Y",
            "%d.%m.%Y",
            "%d/%m",
            "%d-%m",
            "%d %B %Y",
            "%d %b %Y",
            "%d %B",
            "%d %b"

        ]

        for fmt in formats:

            try:

                parsed = datetime.strptime(
                    value,
                    fmt
                )

                if "%Y" not in fmt:

                    parsed = parsed.replace(
                        year=today.year
                    )

                result = parsed.date()

                if (
                    "%Y" not in fmt
                    and result < today
                ):

                    result = result.replace(
                        year=today.year + 1
                    )

                return result

            except ValueError:

                continue

        return None

    # =====================================================
    # SCHEDULE A QUERY
    # =====================================================

    async def schedule_query(
        self,
        prompt=None,
        detected_time=None
    ):

        if prompt is None:

            prompt = (
                await self.get_input(
                    "\nWhat database query do you want to schedule? "
                )
            ).strip()

        prompt = re.sub(
            r"\b(?:schedule|remind me)\b",
            " ",
            prompt,
            flags=re.IGNORECASE
        ).strip()

        if detected_time is None:

            detected_time = self.extract_time(
                prompt
            )

        prompt = self.remove_time_from_prompt(
            prompt
        )

        if not prompt:

            print("Query cannot be empty.")

            return

        table_name = self.identify_table(
            prompt
        )

        if not table_name:

            print(
                "Please mention students, teachers, "
                "customers or policies."
            )

            return

        # Ask for time if not provided.
        while detected_time is None:

            time_input = await self.get_input(
                "\nEnter schedule time "
                "(Example: 6 PM, 6:30 PM, 18:30): "
            )

            detected_time = self.extract_time(
                time_input
            )

            if detected_time is None:

                print("Invalid time. Please try again.")

        # Ask for date.
        while True:

            date_input = await self.get_input(
                "\nEnter schedule date "
                "(today, tomorrow, 2 November): "
            )

            scheduled_date = self.parse_date(
                date_input
            )

            if scheduled_date:

                break

            print("Invalid date. Please try again.")

        hour, minute = map(
            int,
            detected_time.split(":")
        )

        run_at = datetime(
            scheduled_date.year,
            scheduled_date.month,
            scheduled_date.day,
            hour,
            minute,
            tzinfo=TIMEZONE
        )

        if run_at <= datetime.now(TIMEZONE):

            print(
                "This time has already passed. "
                "Choose a future time."
            )

            return

        job_id = f"query_{uuid.uuid4().hex[:12]}"

        job = self.scheduler.add_job(
            self.run_scheduled_query,
            trigger=DateTrigger(
                run_date=run_at,
                timezone=TIMEZONE
            ),
            args=[prompt],
            id=job_id,
            replace_existing=False
        )

        print("\n========================================")
        print("         SCHEDULED SUCCESSFULLY")
        print("========================================")
        print(f"Query : {prompt}")
        print(
            f"Date  : {run_at.strftime('%d %B %Y')}"
        )
        print(
            f"Time  : {run_at.strftime('%I:%M %p')}"
        )
        print(f"Job ID: {job.id}")
        print("Timezone: Asia/Kolkata")
        print("========================================")

    # =====================================================
    # RUN SCHEDULED QUERY
    # =====================================================

    async def run_scheduled_query(self, prompt):

        print("\n========================================")
        print("       SCHEDULED QUERY EXECUTION")
        print("========================================")
        print(f"Query: {prompt}")

        try:

            table_name = self.identify_table(
                prompt
            )

            if not table_name:

                print("Invalid scheduled database query.")

                return

            if table_name in {
                CUSTOMER_TABLE,
                POLICY_TABLE
            }:

                await self.execute_customer_policy_query(
                    prompt,
                    table_name
                )

                return

            operation = self.identify_operation(
                prompt
            )

            if operation == "DESCRIBE":

                await self.call_tool(
                    "get_table_schema",
                    {
                        "table_name": table_name
                    }
                )

                return

            query_plan = self.build_query_plan(
                prompt,
                table_name,
                operation
            )

            if query_plan:

                await self.execute_query(
                    query_plan
                )

        except Exception as error:

            print(
                f"\nScheduled query failed: {error}"
            )

    # =====================================================
    # SCHEDULED JOB LIST
    # =====================================================

    def show_scheduled_jobs(self):

        jobs = self.scheduler.get_jobs()

        if not jobs:

            print("\nNo scheduled jobs available.")

            return

        print("\n========== SCHEDULED JOBS ==========")

        for job in jobs:

            print(f"Job ID: {job.id}")
            print(f"Next Run: {job.next_run_time}")
            print("-----------------------------------")

    # =====================================================
    # APPLICATION ENTRY POINT
    # =====================================================


if __name__ == "__main__":

    application = PostgreSQLScheduler()

    asyncio.run(
        application.run()
    )