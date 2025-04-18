from typing import Annotated, Literal, Dict, List, Any
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda
from langchain_core.pydantic_v1 import BaseModel, Field
from typing_extensions import TypedDict
from langgraph.graph import END, StateGraph, START
from langgraph.graph.message import AnyMessage, add_messages
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define a SubmitFinalAnswer tool for the agent
class SubmitFinalAnswer(BaseModel):
    """Submit the final answer to the user based on the query results."""
    final_answer: str = Field(..., description="The final answer to the user")

# State type for the graph
class State(TypedDict):
    messages: Annotated[List[AnyMessage], add_messages]

class SQLAgent:
    def __init__(self, db_manager, api_key=None):
        self.db_manager = db_manager
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY must be provided either directly or as an environment variable")
        
        # Initialize the LLM
        self.llm = ChatGroq(model="llama3-70b-8192", api_key=self.api_key)
        
        # Create the agent graph
        self.app = self._create_agent_graph()
    
    def _create_tools(self):
        """Create tools for the agent"""
        db_manager = self.db_manager
        
        @tool
        def list_tables() -> str:
            """List all tables in the database"""
            schema_info = db_manager.get_schema_info()
            if schema_info["status"] == "success":
                tables = list(schema_info["schema"].keys())
                return ", ".join(tables)
            else:
                return f"Error: {schema_info['message']}"
        
        @tool
        def get_schema(table_names: str) -> str:
            """Get schema information for specified tables. 
            Example input: 'employees, orders'"""
            tables = [t.strip() for t in table_names.split(",")]
            schema_info = db_manager.get_schema_info()
            
            if schema_info["status"] != "success":
                return f"Error: {schema_info['message']}"
            
            result = ""
            for table in tables:
                if table in schema_info["schema"]:
                    table_info = schema_info["schema"][table]
                    result += f"\nCREATE TABLE {table} (\n"
                    for col in table_info["columns"]:
                        result += f"\t{col['name']} {col['type']}, \n"
                    result += ");\n"
                    
                    # Add sample data
                    result += "\n/*\n3 rows from table:\n"
                    # Column headers
                    if table_info["sample_data"]:
                        result += "\t".join(table_info["sample_data"][0].keys()) + "\n"
                        # Data rows
                        for row in table_info["sample_data"]:
                            result += "\t".join(str(val) for val in row.values()) + "\n"
                    result += "*/\n"
                else:
                    result += f"Table '{table}' not found.\n"
            
            return result
        
        @tool
        def db_query_tool(query: str) -> str:
            """Execute a SQL query against the database and return the result.
            If the query is invalid or returns no result, an error message will be returned.
            In case of an error, the user is advised to rewrite the query and try again.
            """
            result = db_manager.execute_query(query)
            if result["status"] != "success":
                return f"Error: {result['message']}. Please rewrite your query and try again."
            
            # Format the results as a string
            if not result["results"]:
                return "The query returned no results."
            
            output = ""
            # Headers
            if result["results"]:
                headers = list(result["results"][0].keys())
                output += "\t".join(headers) + "\n"
                # Rows
                for row in result["results"]:
                    output += "\t".join(str(val) for val in row.values()) + "\n"
            
            return output
        
        return [list_tables, get_schema, db_query_tool]
    
    def _create_agent_graph(self):
        """Create the LangGraph for the agent"""
        tools = self._create_tools()
        
        # Set up the system prompts
        query_gen_system = """You are a SQL expert with a strong attention to detail.

Given an input question, output a syntactically correct SQLite query to run, then look at the results of the query and return the answer.

DO NOT call any tool besides SubmitFinalAnswer to submit the final answer.

When generating the query:

Output the SQL query that answers the input question without a tool call.

Unless the user specifies a specific number of examples they wish to obtain, always limit your query to at most 5 results.
You can order the results by a relevant column to return the most interesting examples in the database.
Never query for all the columns from a specific table, only ask for the relevant columns given the question.

If you get an error while executing a query, rewrite the query and try again.

If you get an empty result set, you should try to rewrite the query to get a non-empty result set.
NEVER make stuff up if you don't have enough information to answer the query... just say you don't have enough information.

If you have enough information to answer the input question, simply invoke the appropriate tool to submit the final answer to the user.

DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.) to the database. Do not return any sql query except answer."""
        
        query_check_system = """You are a SQL expert with a strong attention to detail.
Double check the SQLite query for common mistakes, including:
- Using NOT IN with NULL values
- Using UNION when UNION ALL should have been used
- Using BETWEEN for exclusive ranges
- Data type mismatch in predicates
- Properly quoting identifiers
- Using the correct number of arguments for functions
- Casting to the correct data type
- Using the proper columns for joins

If there are any of the above mistakes, rewrite the query. If there are no mistakes, just reproduce the original query.

You will call the appropriate tool to execute the query after running this check."""
        
        # Create the prompts
        query_gen_prompt = ChatPromptTemplate.from_messages([
            ("system", query_gen_system), 
            ("placeholder", "{messages}")
        ])
        
        query_check_prompt = ChatPromptTemplate.from_messages([
            ("system", query_check_system), 
            ("placeholder", "{messages}")
        ])
        
        # Create chains with tools
        query_gen = query_gen_prompt | self.llm.bind_tools([SubmitFinalAnswer])
        query_check = query_check_prompt | self.llm.bind_tools(tools)
        
        # Create nodes for the graph
        def first_tool_call(state: State) -> Dict[str, List[AIMessage]]:
            return {
                "messages": [
                    AIMessage(
                        content="",
                        tool_calls=[{
                            "name": "list_tables",
                            "args": {},
                            "id": "tool_init"
                        }]
                    )
                ]
            }
        
        def handle_tool_error(state: State) -> Dict:
            error = state.get("error")
            tool_calls = state["messages"][-1].tool_calls
            return {
                "messages": [
                    ToolMessage(
                        content=f"Error: {repr(error)}\n please fix your mistakes.",
                        tool_call_id=tc["id"],
                    )
                    for tc in tool_calls
                ]
            }
        
        def create_tool_node_with_fallback(tools):
            from langgraph.prebuilt import ToolNode
            return ToolNode(tools).with_fallbacks([RunnableLambda(handle_tool_error)], exception_key="error")
        
        def query_gen_node(state: State):
            message = query_gen.invoke(state)
            
            # Check for wrong tool calls
            tool_messages = []
            if message.tool_calls:
                for tc in message.tool_calls:
                    if tc["name"] != "SubmitFinalAnswer":
                        tool_messages.append(
                            ToolMessage(
                                content=f"Error: The wrong tool was called: {tc['name']}. Please fix your mistakes. Remember to only call SubmitFinalAnswer to submit the final answer. Generated queries should be outputted WITHOUT a tool call.",
                                tool_call_id=tc["id"],
                            )
                        )
            else:
                tool_messages = []
            return {"messages": [message] + tool_messages}
        
        def model_check_query(state: State) -> Dict[str, List[AIMessage]]:
            """Use this tool to double-check if your query is correct before executing it."""
            return {"messages": [query_check.invoke({"messages": [state["messages"][-1]]})]}
        
        def model_get_schema(state: State) -> Dict[str, List[AIMessage]]:
            model_with_schema_tool = self.llm.bind_tools([tools[1]])  # get_schema tool
            return {"messages": [model_with_schema_tool.invoke(state["messages"])]}
        
        def should_continue(state: State) -> Literal[END, "correct_query", "query_gen"]:
            messages = state["messages"]
            last_message = messages[-1]
            if getattr(last_message, "tool_calls", None) and any(tc["name"] == "SubmitFinalAnswer" for tc in last_message.tool_calls):
                return END
            if last_message.content.startswith("Error:"):
                return "query_gen"
            else:
                return "correct_query"
        
        # Create the graph
        workflow = StateGraph(State)
        
        # Add nodes
        workflow.add_node("first_tool_call", first_tool_call)
        workflow.add_node("list_tables", create_tool_node_with_fallback([tools[0]]))
        workflow.add_node("model_get_schema", model_get_schema)
        workflow.add_node("get_schema", create_tool_node_with_fallback([tools[1]]))
        workflow.add_node("query_gen", query_gen_node)
        workflow.add_node("correct_query", model_check_query)
        workflow.add_node("execute_query", create_tool_node_with_fallback([tools[2]]))
        
        # Add edges
        workflow.add_edge(START, "first_tool_call")
        workflow.add_edge("first_tool_call", "list_tables")
        workflow.add_edge("list_tables", "model_get_schema")
        workflow.add_edge("model_get_schema", "get_schema")
        workflow.add_edge("get_schema", "query_gen")
        workflow.add_conditional_edges(
            "query_gen",
            should_continue,
        )
        workflow.add_edge("correct_query", "execute_query")
        workflow.add_edge("execute_query", "query_gen")
        
        # Compile the graph
        return workflow.compile()
    
    def run(self, query):
        """Run the agent with the given query"""
        logger.info(f"Running query: {query}")
        result = self.app.invoke({"messages": [HumanMessage(content=query)]})
        
        # Extract the final answer
        for message in reversed(result["messages"]):
            if hasattr(message, "tool_calls") and message.tool_calls:
                for tool_call in message.tool_calls:
                    if tool_call["name"] == "SubmitFinalAnswer":
                        return {"status": "success", "answer": tool_call["args"]["final_answer"]}
        
        # If no final answer found, return the last message
        return {"status": "error", "answer": "Failed to generate an answer."}