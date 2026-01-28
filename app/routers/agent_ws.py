"""
Agent WebSocket 엔드포인트

로컬 Agent와의 WebSocket 연결을 관리합니다.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Header
from typing import Dict, Optional
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# 연결된 Agent들 관리 {user_id: websocket}
connected_agents: Dict[str, WebSocket] = {}


@router.websocket("/ws/agent")
async def agent_websocket(websocket: WebSocket):
    """로컬 Agent WebSocket 연결"""
    await websocket.accept()
    
    user_id = None
    
    try:
        # 인증 확인
        headers = websocket.headers
        auth_header = headers.get("authorization", "")
        api_key = auth_header.replace("Bearer ", "") if auth_header.startswith("Bearer ") else ""
        user_id = headers.get("x-user-id", "")
        
        if not api_key or not user_id:
            await websocket.close(code=4001, reason="Unauthorized: Missing credentials")
            return
        
        # TODO: API 키 검증 (DB에서 확인)
        # For now, accept any connection for development
        
        # Agent 등록
        connected_agents[user_id] = websocket
        logger.info(f"✅ Agent connected: user_id={user_id}")
        
        # 연결 유지 및 메시지 수신
        while True:
            # Agent로부터 메시지 수신 (상태 업데이트 등)
            data = await websocket.receive_text()
            message = json.loads(data)
            
            logger.info(f"📨 Received from agent {user_id}: {message}")
            
            # 상태 업데이트 처리
            # TODO: 상태를 DB 또는 Redis에 저장하여 웹에서 조회 가능하도록
            
    except WebSocketDisconnect:
        logger.info(f"Agent disconnected: user_id={user_id}")
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
    finally:
        # Agent 연결 해제
        if user_id and user_id in connected_agents:
            connected_agents.pop(user_id, None)
            logger.info(f"Agent removed from registry: user_id={user_id}")


async def send_command_to_agent(user_id: str, command: str, data: dict = None):
    """특정 Agent에 명령 전송"""
    websocket = connected_agents.get(user_id)
    
    # [NEW] Fallback to unbound agent (First-Connect scenario)
    if not websocket:
        websocket = connected_agents.get("unbound")
        if websocket:
            logger.info(f"Target agent {user_id} not found. Using fallback 'unbound' agent.")
    
    if not websocket:
        raise HTTPException(status_code=404, detail=f"Agent not connected for user {user_id}")
    
    message = {
        "command": command,
        "data": data or {}
    }
    
    try:
        await websocket.send_text(json.dumps(message))
        logger.info(f"📤 Sent command to agent {user_id}: {command}")
    except Exception as e:
        logger.error(f"Failed to send command to agent {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send command: {str(e)}")


def is_agent_connected(user_id: str) -> bool:
    """Agent 연결 여부 확인"""
    return user_id in connected_agents
