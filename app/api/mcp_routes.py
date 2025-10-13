from fastapi import APIRouter, Depends
from app.core.dependencies import get_current_user

router = APIRouter()

@router.get("/")
def read_mcp(current_user: str = Depends(get_current_user)):
    return {"message": "MCP endpoint"}

@router.post("/")
def add_mcp(data: dict, current_user: str = Depends(get_current_user)):
    return {"message": "MCP data added", "data": data}

@router.delete("/{mcp_id}")
def delete_mcp(mcp_id: int, current_user: str = Depends(get_current_user
)):
    return {"message": f"MCP {mcp_id} deleted"}

@router.put("/{mcp_id}")
def update_mcp(mcp_id: int, data: dict, current_user: str = Depends(get_current_user)):
    return {"message": f"MCP {mcp_id} updated", "data": data}