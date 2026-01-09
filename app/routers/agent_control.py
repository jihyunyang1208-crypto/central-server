"""
Agent 제어 API

로컬 Agent를 제어하는 REST API 엔드포인트
"""

from fastapi import APIRouter, Depends, HTTPException
from app.routers.agent_ws import send_command_to_agent, is_agent_connected
from app.core.security import get_current_user

router = APIRouter(prefix="/api/agent", tags=["Agent Control"])


@router.post("/start")
async def start_agent_workers(current_user = Depends(get_current_user)):
    """로컬 Agent에 워커 시작 명령"""
    user_id = str(current_user.id)
    
    if not is_agent_connected(user_id):
        raise HTTPException(
            status_code=503, 
            detail="Agent not connected. Please install and start the AutoTrader Agent on your PC."
        )
    
    try:
        await send_command_to_agent(user_id, "start_workers")
        return {"status": "command_sent", "message": "Start command sent to agent"}
    except HTTPException as e:
        raise e


@router.post("/stop")
async def stop_agent_workers(current_user = Depends(get_current_user)):
    """로컬 Agent에 워커 중지 명령"""
    user_id = str(current_user.id)
    
    if not is_agent_connected(user_id):
        raise HTTPException(
            status_code=503, 
            detail="Agent not connected"
        )
    
    try:
        await send_command_to_agent(user_id, "stop_workers")
        return {"status": "command_sent", "message": "Stop command sent to agent"}
    except HTTPException as e:
        raise e


@router.get("/status")
async def get_agent_status(current_user = Depends(get_current_user)):
    """Agent 연결 상태 확인"""
    user_id = str(current_user.id)
    is_connected = is_agent_connected(user_id)
    
    if is_connected:
        # Agent에 상태 요청
        try:
            await send_command_to_agent(user_id, "status")
        except:
            pass
    
    return {
        "connected": is_connected,
        "user_id": user_id,
        "message": "Agent connected" if is_connected else "Agent not connected"
    }
