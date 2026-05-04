from pydantic import BaseModel, Field


class PrintAgentPullRequest(BaseModel):
    agent_id: str = Field(min_length=2, max_length=120)


class PrintAgentJobItem(BaseModel):
    product_id: int
    product_name: str
    quantity: int
    price: float
    extras: str = ""


class PrintAgentJobOrder(BaseModel):
    id: int
    status: str
    total_price: float
    items: list[PrintAgentJobItem]


class PrintAgentJobEnvelope(BaseModel):
    job_id: int
    attempt_count: int
    max_attempts: int
    order: PrintAgentJobOrder


class PrintAgentPullResponse(BaseModel):
    job: PrintAgentJobEnvelope | None


class PrintAgentJobResolveRequest(BaseModel):
    agent_id: str = Field(min_length=2, max_length=120)


class PrintAgentJobFailRequest(PrintAgentJobResolveRequest):
    error: str = Field(min_length=3, max_length=500)
