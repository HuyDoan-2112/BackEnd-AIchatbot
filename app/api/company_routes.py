from fastapi import APIRouter, Depends
from app.core.dependencies import get_current_user

router = APIRouter()
@router.get("/")
def get_company(current_user: str = Depends(get_current_user)):
    return {"message": "Company endpoint"}
@router.post("/")
def create_company(name: str, current_user: str = Depends(get_current_user)):
    new_company = {"company_id": 1, "name": name}
    return new_company
@router.put("/{company_id}")
def update_company(company_id: int, name: str, current_user: str = Depends(get_current_user)):
    updated_company = {"company_id": company_id, "name": name}
    return updated_company
@router.delete("/{company_id}")
def delete_company(company_id: int, current_user: str = Depends(get_current_user)):
    return {"message": f"Company {company_id} deleted"}