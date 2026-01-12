"""
Terminal WebSocket API for ChatOS Sandbox
Provides real PTY terminal access via WebSocket
"""

import asyncio
import os
import pty
import select
import struct
import fcntl
import termios
import signal
from typing import Dict, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json

router = APIRouter(prefix="/api/terminal", tags=["terminal"])

# Store active terminal sessions
terminal_sessions: Dict[str, dict] = {}


class TerminalSession:
    """Manages a PTY terminal session"""
    
    def __init__(self, session_id: str, cwd: str = None):
        self.session_id = session_id
        self.cwd = cwd or os.path.expanduser("~/ChatOS-Sandbox")
        self.master_fd: Optional[int] = None
        self.pid: Optional[int] = None
        self.running = False
        
    def start(self) -> bool:
        """Start the terminal session"""
        try:
            # Ensure sandbox directory exists
            os.makedirs(self.cwd, exist_ok=True)
            
            # Create pseudo-terminal
            self.pid, self.master_fd = pty.fork()
            
            if self.pid == 0:
                # Child process - execute shell
                os.chdir(self.cwd)
                os.environ["TERM"] = "xterm-256color"
                os.environ["PS1"] = "\\[\\033[01;32m\\]sandbox\\[\\033[00m\\]:\\[\\033[01;34m\\]\\w\\[\\033[00m\\]$ "
                os.execlp("/bin/bash", "bash", "--norc", "-i")
            else:
                # Parent process
                self.running = True
                # Set non-blocking
                flags = fcntl.fcntl(self.master_fd, fcntl.F_GETFL)
                fcntl.fcntl(self.master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
                return True
                
        except Exception as e:
            print(f"Failed to start terminal: {e}")
            return False
    
    def resize(self, rows: int, cols: int):
        """Resize the terminal"""
        if self.master_fd:
            try:
                winsize = struct.pack("HHHH", rows, cols, 0, 0)
                fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, winsize)
            except Exception as e:
                print(f"Failed to resize terminal: {e}")
    
    def write(self, data: str):
        """Write data to the terminal"""
        if self.master_fd and self.running:
            try:
                os.write(self.master_fd, data.encode())
            except Exception as e:
                print(f"Failed to write to terminal: {e}")
    
    def read(self) -> Optional[str]:
        """Read data from the terminal (non-blocking)"""
        if not self.master_fd or not self.running:
            return None
            
        try:
            r, _, _ = select.select([self.master_fd], [], [], 0.01)
            if r:
                data = os.read(self.master_fd, 4096)
                if data:
                    return data.decode("utf-8", errors="replace")
        except OSError:
            self.running = False
        except Exception as e:
            print(f"Failed to read from terminal: {e}")
            
        return None
    
    def stop(self):
        """Stop the terminal session"""
        self.running = False
        if self.pid:
            try:
                os.kill(self.pid, signal.SIGTERM)
                os.waitpid(self.pid, 0)
            except:
                pass
        if self.master_fd:
            try:
                os.close(self.master_fd)
            except:
                pass


@router.websocket("/ws/{session_id}")
async def terminal_websocket(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for terminal communication"""
    await websocket.accept()
    
    # Create or get terminal session
    if session_id not in terminal_sessions:
        session = TerminalSession(session_id)
        if not session.start():
            await websocket.close(code=1011, reason="Failed to start terminal")
            return
        terminal_sessions[session_id] = {"session": session, "websocket": websocket}
    else:
        session = terminal_sessions[session_id]["session"]
        terminal_sessions[session_id]["websocket"] = websocket
    
    # Send initial prompt
    await websocket.send_text(json.dumps({
        "type": "output",
        "data": f"\x1b[32mChatOS Terminal\x1b[0m - Session: {session_id}\r\n"
    }))
    
    try:
        # Create tasks for reading from terminal and websocket
        async def read_terminal():
            while session.running:
                output = session.read()
                if output:
                    await websocket.send_text(json.dumps({
                        "type": "output",
                        "data": output
                    }))
                await asyncio.sleep(0.01)
        
        async def read_websocket():
            while session.running:
                try:
                    message = await asyncio.wait_for(
                        websocket.receive_text(),
                        timeout=0.1
                    )
                    data = json.loads(message)
                    
                    if data.get("type") == "input":
                        session.write(data.get("data", ""))
                    elif data.get("type") == "resize":
                        session.resize(
                            data.get("rows", 24),
                            data.get("cols", 80)
                        )
                except asyncio.TimeoutError:
                    continue
                except WebSocketDisconnect:
                    break
                except Exception as e:
                    print(f"WebSocket error: {e}")
                    break
        
        # Run both tasks concurrently
        await asyncio.gather(
            read_terminal(),
            read_websocket(),
            return_exceptions=True
        )
        
    except WebSocketDisconnect:
        pass
    finally:
        # Keep session alive for reconnection
        pass


@router.delete("/{session_id}")
async def close_terminal(session_id: str):
    """Close a terminal session"""
    if session_id in terminal_sessions:
        terminal_sessions[session_id]["session"].stop()
        del terminal_sessions[session_id]
        return {"status": "closed"}
    return {"status": "not_found"}


@router.get("/sessions")
async def list_sessions():
    """List active terminal sessions"""
    return {
        "sessions": [
            {"id": sid, "running": data["session"].running}
            for sid, data in terminal_sessions.items()
        ]
    }

