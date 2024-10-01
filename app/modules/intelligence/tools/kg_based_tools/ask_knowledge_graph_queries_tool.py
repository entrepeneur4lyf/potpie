import asyncio
import os
from typing import Dict, List, Tuple

import aiohttp
from langchain.tools import StructuredTool
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    node_ids: List[str] = Field(description="A list of node ids to query")
    project_id: str = Field(
        description="The project id metadata for the project being evaluated"
    )
    query: str = Field(
        description="A natural language question to ask the knowledge graph"
    )


class MultipleKnowledgeGraphQueriesInput(BaseModel):
    queries: List[str] = Field(
        description="A list of natural language questions to ask the knowledge graph"
    )
    project_id: str = Field(
        description="The project id metadata for the project being evaluated"
    )


async def ask_multiple_knowledge_graph_queries(
    queries: List[QueryRequest],
) -> Dict[str, str]:
    kg_query_url = os.getenv("KNOWLEDGE_GRAPH_URL")
    headers = {"Content-Type": "application/json"}

    async def fetch_query(query_request: QueryRequest) -> Tuple[str, str]:
        data = query_request.dict()
        async with aiohttp.ClientSession() as session:
            async with session.post(
                kg_query_url, json=data, headers=headers
            ) as response:
                result = await response.json()
                return query_request.query, result

    tasks = [fetch_query(query) for query in queries]
    results = await asyncio.gather(*tasks)

    return dict(results)


def ask_knowledge_graph_query(
    queries: List[str], project_id: str, node_ids: List[str] = []
) -> Dict[str, str]:
    """
    Query the code knowledge graph using multiple natural language questions.
    The knowledge graph contains information about every function, class, and file in the codebase.
    This method allows asking multiple questions about the codebase in a single operation.

    Inputs:
    - queries (List[str]): A list of natural language questions that the user wants to ask the knowledge graph.
      Each question should be clear and concise, related to the codebase.
    - project_id (str): The ID of the project being evaluated, this is a UUID.

    Returns:
    - Dict[str, str]: A dictionary where keys are the original queries and values are the corresponding responses.
    """
    query_list = [
        QueryRequest(query=query, project_id=project_id, node_ids=node_ids)
        for query in queries
    ]
    return asyncio.run(ask_multiple_knowledge_graph_queries(query_list))


def get_ask_knowledge_graph_queries_tool() -> StructuredTool:
    return StructuredTool.from_function(
        func=ask_knowledge_graph_query,
        name="Ask Knowledge Graph Queries",
        description="""
    Query the code knowledge graph using multiple natural language questions.
    The knowledge graph contains information about every function, class, and file in the codebase.
    This tool allows asking multiple questions about the codebase in a single operation.

    Inputs:
    - queries (List[str]): A list of natural language questions to ask the knowledge graph. Each question should be
    clear and concise, related to the codebase, such as "What does the XYZ class do?" or "How is the ABC function used?"
    - project_id (str): The ID of the project being evaluated, this is a UUID.
    - node_ids (List[str]): A list of node ids to query, this is an optional parameter that can be used to query a specific node. use this only when you are sure that the answer to the question is related to that node.

    Use this tool when you need to ask multiple related questions about the codebase at once.
    Do not use this to query code directly.""",
        args_schema=MultipleKnowledgeGraphQueriesInput,
    )