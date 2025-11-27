"""
RAGTool: Retrieval Augmented Generation tool for fetching relevant course materials.
"""

import json
from typing import Any, Dict
from .base_tool import Tool


class RAGTool(Tool):
    """
    Tool for retrieving relevant course materials using hybrid RAG.

    Uses dense embeddings (70%) + BM25 keyword search (30%) for retrieval.
    """

    name: str = "Retrieve Course Materials"
    description: str = "Retrieve relevant course materials from uploaded PDFs using hybrid search (semantic + keyword)"
    action_type: str = "retrieve_materials"
    input_format: str = '{"query": "topic or question", "user_id": "user123", "course_id": "course456", "top_k": 8}'

    def __init__(self, **data):
        super().__init__(**data)
        # Import here to avoid circular dependencies
        from agentpro_app.rag import hybrid_retrieve
        self.hybrid_retrieve = hybrid_retrieve

    def run(self, input_data: Any) -> str:
        """
        Execute RAG retrieval.

        Args:
            input_data: Dict with query, user_id, course_id, top_k (optional)

        Returns:
            JSON string with retrieval results
        """
        try:
            # Parse input
            if isinstance(input_data, str):
                params = json.loads(input_data)
            elif isinstance(input_data, dict):
                params = input_data
            else:
                return json.dumps({"error": "Invalid input format. Expected dict or JSON string"})

            query = params.get("query")
            user_id = params.get("user_id")
            course_id = params.get("course_id")
            top_k = params.get("top_k", 8)

            if not all([query, user_id, course_id]):
                return json.dumps({"error": "Missing required fields: query, user_id, course_id"})

            # Execute retrieval
            hits = self.hybrid_retrieve(query, user_id, course_id, top_k=top_k)

            if not hits:
                return json.dumps({
                    "status": "no_results",
                    "message": "No relevant materials found. Please upload course materials.",
                    "hits": []
                })

            # Format results
            formatted_hits = []
            for i, hit in enumerate(hits, 1):
                formatted_hits.append({
                    "rank": i,
                    "text": hit.get("text", "")[:500],  # Truncate for readability
                    "title": hit.get("meta", {}).get("title", "Document"),
                    "page": hit.get("meta", {}).get("page", "?"),
                    "score": round(hit.get("score", 0.0), 3)
                })

            avg_score = sum(h["score"] for h in formatted_hits) / len(formatted_hits)
            quality = "high" if avg_score > 0.7 else "medium" if avg_score > 0.4 else "low"

            return json.dumps({
                "status": "success",
                "hits": formatted_hits,
                "count": len(formatted_hits),
                "avg_score": round(avg_score, 3),
                "quality": quality
            }, indent=2)

        except Exception as e:
            return json.dumps({"error": f"RAG retrieval failed: {str(e)}"})
