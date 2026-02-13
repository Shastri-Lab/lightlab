from __future__ import annotations

import json
import threading
from abc import ABC, abstractmethod

from .errors import GreyMatterError

# Per-command timeout (seconds)
_CMD_TIMEOUT = 10.0


class Transport(ABC):
    """Abstract transport for sending SCPI commands to a greymatter board."""

    @abstractmethod
    def send_command(self, cmd: str) -> str:
        """Send a SCPI command and return the response body.

        The response should already have the echo and prompt stripped.
        Raises GreyMatterError on communication failure.
        """
        ...

    @abstractmethod
    def close(self) -> None:
        """Release the underlying connection."""
        ...


class ZmqTransport(Transport):
    """Remote connection to a greymatter board via a ZMQ server.

    The server manages the serial connections and routes commands
    to the correct Pico board.
    """

    def __init__(self, address: str, pico: str | None = None,
                 port: int = 5556, timeout: float = _CMD_TIMEOUT):
        import zmq
        self._pico = pico
        self._lock = threading.Lock()
        self._context = zmq.Context()
        self._socket = self._context.socket(zmq.REQ)
        self._socket.setsockopt(zmq.RCVTIMEO, int(timeout * 1000))
        self._socket.setsockopt(zmq.SNDTIMEO, int(timeout * 1000))
        self._socket.setsockopt(zmq.LINGER, 1000)
        self._socket.connect(f"tcp://{address}:{port}")

    def send_command(self, cmd: str) -> str:
        import zmq

        with self._lock:
            request = json.dumps({"pico": self._pico, "cmd": cmd})
            try:
                self._socket.send_string(request)
                reply = json.loads(self._socket.recv_string())
            except zmq.Again:
                raise GreyMatterError("Server timeout")

            if reply.get("ok"):
                return reply.get("data", "")
            else:
                raise GreyMatterError(
                    reply.get("error", "Unknown server error")
                )

    def close(self) -> None:
        self._socket.close()
        self._context.destroy()
