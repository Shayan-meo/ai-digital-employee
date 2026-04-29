"""
A2A (Agent-to-Agent) Messaging - Platinum Tier Phase 2
Direct messaging between Cloud and Local agents as an upgrade to file-based handoffs

Features:
- Direct HTTP/gRPC messaging between agents
- Fallback to file-based communication if messaging unavailable
- Message queue for offline agents
- Keeps vault as audit record

Architecture:
  Cloud Agent <---> A2A Message Bus <---> Local Agent
       |                                      |
       v                                      v
  File-based (Git Sync) <------------> File-based

Usage:
    python a2a_messaging.py cloud  # Run as Cloud agent
    python a2a_messaging.py local  # Run as Local agent
"""

import logging
import time
import json
import threading
from pathlib import Path
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional, Callable, List, Dict
from dataclasses import dataclass, asdict
from enum import Enum
import urllib.request
import urllib.error

# Vault paths
VAULT_ROOT = Path(__file__).parent.resolve()
LOGS = VAULT_ROOT / "Logs"
MESSAGE_QUEUE = VAULT_ROOT / "Message_Queue"
LOGS.mkdir(exist_ok=True)
MESSAGE_QUEUE.mkdir(exist_ok=True)

# Configure logging
log_file = LOGS / f"a2a_messaging_{datetime.now():%Y-%m-%d}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Types of A2A messages."""
    TASK_ASSIGNED = "task_assigned"
    TASK_COMPLETED = "task_completed"
    DRAFT_CREATED = "draft_created"
    APPROVAL_REQUEST = "approval_request"
    STATUS_UPDATE = "status_update"
    HEALTH_CHECK = "health_check"
    SHUTDOWN = "shutdown"


class AgentRole(Enum):
    """Agent roles."""
    CLOUD = "cloud"
    LOCAL = "local"


@dataclass
class Message:
    """A2A message structure."""
    id: str
    type: MessageType
    from_agent: AgentRole
    to_agent: AgentRole
    payload: dict
    timestamp: str
    requires_ack: bool = True
    ack_received: bool = False
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "from_agent": self.from_agent.value,
            "to_agent": self.to_agent.value,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "requires_ack": self.requires_ack,
            "ack_received": self.ack_received,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Message":
        return cls(
            id=data["id"],
            type=MessageType(data["type"]),
            from_agent=AgentRole(data["from_agent"]),
            to_agent=AgentRole(data["to_agent"]),
            payload=data["payload"],
            timestamp=data["timestamp"],
            requires_ack=data.get("requires_ack", True),
            ack_received=data.get("ack_received", False),
        )


class MessageHandler:
    """Handles incoming messages."""
    
    def __init__(self, role: AgentRole):
        self.role = role
        self.callbacks: Dict[MessageType, List[Callable]] = {}
    
    def register(self, message_type: MessageType, callback: Callable):
        """Register a callback for a message type."""
        if message_type not in self.callbacks:
            self.callbacks[message_type] = []
        self.callbacks[message_type].append(callback)
        logger.info(f"Registered callback for {message_type.value}")
    
    def handle(self, message: Message):
        """Handle an incoming message."""
        logger.info(f"Received message: {message.type.value} from {message.from_agent.value}")
        
        if message.type in self.callbacks:
            for callback in self.callbacks[message.type]:
                try:
                    callback(message)
                except Exception as e:
                    logger.error(f"Callback error for {message.type.value}: {e}")
        else:
            logger.warning(f"No callback registered for {message.type.value}")
        
        # Also write to vault as audit record
        self.write_to_vault(message)
    
    def write_to_vault(self, message: Message):
        """Write message to vault for audit trail."""
        audit_dir = LOGS / "a2a_audit" / datetime.now().strftime("%Y-%m-%d")
        audit_dir.mkdir(parents=True, exist_ok=True)
        
        filepath = audit_dir / f"msg_{message.id}.json"
        filepath.write_text(json.dumps(message.to_dict(), indent=2), encoding="utf-8")
        logger.debug(f"Message audit written: {filepath}")


class A2AServer:
    """HTTP server for receiving A2A messages."""
    
    def __init__(self, host: str, port: int, message_handler: MessageHandler):
        self.host = host
        self.port = port
        self.handler = message_handler
        self.server: Optional[HTTPServer] = None
    
    def start(self):
        """Start the HTTP server."""
        class RequestHandler(BaseHTTPRequestHandler):
            def do_POST(self):
                content_length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_length)
                
                try:
                    data = json.loads(body.decode('utf-8'))
                    message = Message.from_dict(data)
                    
                    logger.info(f"Received A2A message: {message.id}")
                    self.handler.handle(message)
                    
                    # Send ACK
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    response = {"status": "ok", "message_id": message.id}
                    self.wfile.write(json.dumps(response).encode('utf-8'))
                    
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    self.send_response(400)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    response = {"status": "error", "error": str(e)}
                    self.wfile.write(json.dumps(response).encode('utf-8'))
            
            def do_GET(self):
                if self.path == "/health":
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    response = {"status": "healthy", "timestamp": datetime.now().isoformat()}
                    self.wfile.write(json.dumps(response).encode('utf-8'))
                else:
                    self.send_response(404)
                    self.end_headers()
            
            def log_message(self, format, *args):
                logger.debug(f"HTTP: {format % args}")
        
        self.server = HTTPServer((self.host, self.port), RequestHandler)
        logger.info(f"A2A server starting on {self.host}:{self.port}")
        self.server.serve_forever()
    
    def stop(self):
        """Stop the HTTP server."""
        if self.server:
            self.server.shutdown()
            logger.info("A2A server stopped")


class A2AClient:
    """HTTP client for sending A2A messages."""
    
    def __init__(self, target_host: str, target_port: int, timeout: int = 30):
        self.target_host = target_host
        self.target_port = target_port
        self.timeout = timeout
        self.message_queue: List[Message] = []
    
    def send(self, message: Message) -> bool:
        """Send a message to the target agent."""
        url = f"http://{self.target_host}:{self.target_port}"
        
        try:
            data = json.dumps(message.to_dict()).encode('utf-8')
            req = urllib.request.Request(
                url,
                data=data,
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                result = json.loads(response.read().decode('utf-8'))
                
                if result.get("status") == "ok":
                    message.ack_received = True
                    logger.info(f"Message sent and acknowledged: {message.id}")
                    return True
                else:
                    logger.warning(f"Message sent but not acknowledged: {message.id}")
                    self.queue_message(message)
                    return False
                    
        except urllib.error.URLError as e:
            logger.warning(f"Failed to send message (target offline): {e}")
            self.queue_message(message)
            return False
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            self.queue_message(message)
            return False
    
    def queue_message(self, message: Message):
        """Queue message for later delivery."""
        self.message_queue.append(message)
        
        # Also save to file queue
        queue_file = MESSAGE_QUEUE / f"msg_{message.id}.json"
        queue_file.write_text(json.dumps(message.to_dict(), indent=2), encoding="utf-8")
        logger.info(f"Message queued: {message.id}")
    
    def flush_queue(self) -> int:
        """Try to send queued messages. Returns number of successful sends."""
        successful = 0
        remaining = []
        
        for message in self.message_queue:
            if self.send(message):
                successful += 1
            else:
                remaining.append(message)
        
        self.message_queue = remaining
        logger.info(f"Flushed {successful} queued messages, {len(remaining)} remaining")
        return successful


class A2AMessaging:
    """Main A2A messaging system."""
    
    def __init__(
        self,
        role: AgentRole,
        listen_host: str = "0.0.0.0",
        listen_port: int = 8765,
        target_host: Optional[str] = None,
        target_port: int = 8765,
    ):
        self.role = role
        self.listen_host = listen_host
        self.listen_port = listen_port
        self.target_host = target_host
        self.target_port = target_port
        
        self.handler = MessageHandler(role)
        self.server = A2AServer(listen_host, listen_port, self.handler)
        self.client = A2AClient(target_host, target_port) if target_host else None
        
        self.server_thread: Optional[threading.Thread] = None
    
    def start_server(self):
        """Start the A2A server in a background thread."""
        self.server_thread = threading.Thread(target=self.server.start, daemon=True)
        self.server_thread.start()
        logger.info(f"A2A server started in background (port {self.listen_port})")
    
    def stop_server(self):
        """Stop the A2A server."""
        self.server.stop()
        if self.server_thread:
            self.server_thread.join(timeout=5)
    
    def send_message(
        self,
        message_type: MessageType,
        to_agent: AgentRole,
        payload: dict,
        requires_ack: bool = True,
    ) -> bool:
        """Send an A2A message."""
        if not self.client:
            logger.warning("No target configured, writing to file queue only")
            return False
        
        message = Message(
            id=f"{self.role.value}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{int(time.time()*1000)}",
            type=message_type,
            from_agent=self.role,
            to_agent=to_agent,
            payload=payload,
            timestamp=datetime.now().isoformat(),
            requires_ack=requires_ack,
        )
        
        return self.client.send(message)
    
    def on_message(self, message_type: MessageType, callback: Callable):
        """Register a callback for incoming messages."""
        self.handler.register(message_type, callback)
    
    def run(self):
        """Run the A2A messaging system (blocking)."""
        self.start_server()
        
        logger.info("A2A messaging system running. Press Ctrl+C to stop.")
        try:
            while True:
                if self.client:
                    self.client.flush_queue()
                time.sleep(60)
        except KeyboardInterrupt:
            logger.info("A2A messaging system stopping...")
            self.stop_server()


# Example usage and callbacks
def create_cloud_agent() -> A2AMessaging:
    """Create Cloud agent with default callbacks."""
    agent = A2AMessaging(
        role=AgentRole.CLOUD,
        listen_host="0.0.0.0",
        listen_port=8765,
        target_host="localhost",  # Local agent address (in production: remote IP)
        target_port=8766,
    )
    
    # Register callbacks
    def on_approval_request(msg: Message):
        logger.info(f"Cloud received approval request: {msg.payload}")
    
    def on_task_completed(msg: Message):
        logger.info(f"Cloud received task completed: {msg.payload}")
    
    agent.on_message(MessageType.APPROVAL_REQUEST, on_approval_request)
    agent.on_message(MessageType.TASK_COMPLETED, on_task_completed)
    
    return agent


def create_local_agent() -> A2AMessaging:
    """Create Local agent with default callbacks."""
    agent = A2AMessaging(
        role=AgentRole.LOCAL,
        listen_host="0.0.0.0",
        listen_port=8766,  # Different port from Cloud
        listen_port=8766,
        target_host="localhost",  # Cloud agent address (in production: cloud VM IP)
        target_port=8765,
    )
    
    # Register callbacks
    def on_draft_created(msg: Message):
        logger.info(f"Local received draft created: {msg.payload}")
        # In production: notify user, update dashboard
    
    def on_status_update(msg: Message):
        logger.info(f"Local received status update: {msg.payload}")
    
    agent.on_message(MessageType.DRAFT_CREATED, on_draft_created)
    agent.on_message(MessageType.STATUS_UPDATE, on_status_update)
    
    return agent


def main():
    """CLI for A2A messaging."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python a2a_messaging.py [cloud|local]")
        return
    
    command = sys.argv[1].lower()
    
    if command == "cloud":
        logger.info("Starting Cloud A2A Agent")
        agent = create_cloud_agent()
        agent.run()
    
    elif command == "local":
        logger.info("Starting Local A2A Agent")
        agent = create_local_agent()
        agent.run()
    
    else:
        print(f"Unknown command: {command}")
        print("Usage: python a2a_messaging.py [cloud|local]")


if __name__ == "__main__":
    main()
