"""
QueryCampus: Standalone Interactive Reception Kiosk Server.
Hosts the HTML5/CSS3 Reception Kiosk on http://localhost:8000 and
exposes RAG inquiry and ticket escalation endpoints.
"""

import os
import json
import time
from pathlib import Path

# Add project root to sys.path
import sys
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.vector_store import ChromaVectorStore
from src.ingest import DocumentIngestor
from src.retrieval import CampusRetriever
from src.generator import CampusGenerator
from src.ticketing import TicketingSystem
from src.auth import get_demo_user

# Initialize RAG Pipeline
store = ChromaVectorStore()
if store.count() == 0:
    ingestor = DocumentIngestor()
    chunks = ingestor.load_directory()
    if chunks:
        store.add_chunks(chunks)

retriever = CampusRetriever(store)
generator = CampusGenerator()
ticketing = TicketingSystem()
demo_user = get_demo_user("student")

HTML_FILE = Path(__file__).resolve().parent / "reception_kiosk.html"

try:
    from starlette.applications import Starlette
    from starlette.responses import HTMLResponse, JSONResponse
    from starlette.routing import Route
    from starlette.middleware import Middleware
    from starlette.middleware.cors import CORSMiddleware
    import uvicorn

    async def serve_index(request):
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            content = f.read()
        return HTMLResponse(content)

    async def api_query(request):
        data = await request.json()
        query = data.get("query", "").strip()
        top_k = int(data.get("top_k", 2))
        model = data.get("model", "gemma3:4b")

        if not query:
            return JSONResponse({"error": "Empty query"}, status_code=400)

        t_start = time.perf_counter()
        hits, emb_t, ret_t = retriever.retrieve(query, top_k=top_k)
        confidence_info = retriever.check_confidence(hits)
        context = retriever.format_context(hits)

        res = generator.generate(query=query, context=context, model=model)
        total_t = time.perf_counter() - t_start

        # Detect Escalation
        detected_category = ticketing.detect_escalation_intent(query)
        escalation = detected_category if (detected_category or not confidence_info["is_confident"]) else None

        sources_data = []
        for h in hits:
            sources_data.append({
                "doc": h.get("metadata", {}).get("source", "Campus Handbook"),
                "page": h.get("metadata", {}).get("page", 1),
                "similarity": h.get("similarity", 0.0),
                "text": h.get("text", "")[:200] + "...",
            })

        return JSONResponse({
            "answer": res["text"],
            "sources": sources_data,
            "escalation": escalation,
            "latency_embed": emb_t,
            "latency_retrieval": ret_t,
            "latency_gen": res["latency"],
            "latency_total": total_t,
            "model": res.get("model", model),
        })

    async def api_ticket(request):
        data = await request.json()
        cat = data.get("category", "General Admin")
        title = data.get("title", "Student Inquiry")
        desc = data.get("description", "")
        prio = data.get("priority", "Medium")

        ticket = ticketing.create_ticket(
            user_email=demo_user.email,
            user_name=demo_user.name,
            category=cat,
            title=title,
            description=desc,
            priority=prio,
        )
        return JSONResponse({
            "status": "success",
            "ticket_number": ticket.ticket_number,
            "id": ticket.id,
        })

    async def api_stats(request):
        return JSONResponse({
            "indexed_chunks": store.count(),
            "tickets_count": len(ticketing.get_all_tickets()),
            "status": "online",
        })

    routes = [
        Route("/", serve_index, methods=["GET"]),
        Route("/api/query", api_query, methods=["POST"]),
        Route("/api/ticket", api_ticket, methods=["POST"]),
        Route("/api/stats", api_stats, methods=["GET"]),
    ]

    middleware = [
        Middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]),
    ]

    app = Starlette(debug=True, routes=routes, middleware=middleware)

    def main():
        port = int(os.getenv("PORT", "8000"))
        print(f"\n=======================================================")
        print(f"🏛️ QueryCampus • Bosscoder College Reception Kiosk (Aussie on Duty)!")
        print(f"📍 Open in your browser: http://localhost:{port}")
        print(f"=======================================================\n")
        uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")

except ImportError:
    import http.server
    import socketserver

    class KioskHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/" or self.path == "/index.html":
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                with open(HTML_FILE, "rb") as f:
                    self.wfile.write(f.read())
            else:
                super().do_GET()

    def main():
        port = int(os.getenv("PORT", "8000"))
        print(f"Running basic HTTP server at http://localhost:{port}")
        with socketserver.TCPServer(("", port), KioskHandler) as httpd:
            httpd.serve_forever()

if __name__ == "__main__":
    main()
