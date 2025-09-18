#!/usr/bin/env python3
"""
Server MCP per ricerca semantica ticket
Solo modalità stdio - da usare con mcpo per OpenWebUI
"""

import asyncio
import json
import logging
from typing import List

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    ServerCapabilities,
    ToolsCapability,
)

# Import moduli locali
from tools.search import search_similar_tickets
from tools.get_ticket import get_ticket_by_id

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Crea il server MCP
server = Server("ticket-search-server")

@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    """Lista tutti i tool disponibili"""
    return [
        Tool(
            name="search_similar_tickets",
            description="Cerca ticket simili tramite ricerca semantica sul contenuto del ticket. Analizza il testo e trova ticket con problemi o richieste simili.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query_text": {
                        "type": "string",
                        "description": "Testo da cercare nei ticket (descrizione del problema, parole chiave, etc.)"
                    },
                    "n_results": {
                        "type": "integer",
                        "description": "Numero massimo di risultati da restituire (default: 5)",
                        "default": 5,
                        "minimum": 1,
                        "maximum": 20
                    }
                },
                "required": ["query_text"]
            }
        ),
        Tool(
            name="get_ticket_by_id",
            description="Recupera un ticket specifico dal gestionale tramite il suo ID. Supporta formati come '3906', '3906/SPC-2024', '3906/2024'.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticket_id": {
                        "type": "string",
                        "description": "ID del ticket da recuperare (es. '3906', '3906/SPC-2024', '3906/2024')"
                    }
                },
                "required": ["ticket_id"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> List[TextContent]:
    """Gestisce le chiamate ai tool"""
    try:
        # Dizionario che mappa i nomi dei tool alle loro funzioni
        tool_handlers = {
            "search_similar_tickets": lambda: search_similar_tickets(
                arguments["query_text"],
                arguments.get("n_results", 5)
            ),
            "get_ticket_by_id": lambda: get_ticket_by_id(arguments["ticket_id"])
        }
        
        # Esegue il tool appropriato
        if name in tool_handlers:
            result = await tool_handlers[name]()
        else:
            raise ValueError(f"Tool sconosciuto: {name}")
        
        return [TextContent(type="text", text=result)]
    
    except Exception as e:
        logger.error(f"Errore in {name}: {e}")
        error_response = json.dumps({
            "error": str(e),
            "tool": name,
            "arguments": arguments
        }, ensure_ascii=False)
        return [TextContent(type="text", text=error_response)]

async def main():
    """Funzione principale per avviare il server"""
    
    # Solo modalità stdio
    logger.info("🚀 Avvio server MCP per ricerca ticket in modalità stdio...")
    logger.info("💡 Per OpenWebUI usa: mcpo --port 8002 -- python server.py")
    
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream, 
            write_stream, 
            InitializationOptions(
                server_name="ticket-search-server",
                server_version="1.0.0",
                capabilities=ServerCapabilities(
                    tools=ToolsCapability()
                )
            )
        )

def test_stdio():
    """Test per verificare che stdio funzioni"""
    import sys
    logger.info("📝 Test stdio per ticket search server...")
    logger.info("✅ Logging funziona")

if __name__ == "__main__":
    test_stdio()
    asyncio.run(main())