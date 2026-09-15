# Pydantic V2 Request Body Validation Models

## 1. Schema Validation Definition
```python
from pydantic import BaseModel, Field
from typing import List, Optional

class BookingSyncPayload(BaseModel):
    bk_booking_ref: str = Field(..., min_length=5, max_length=50)
    bk_customer_name: str = Field(..., min_length=2)
    bk_total_amount: float = Field(..., ge=0.0)
    bk_event_date: str
    menu_items: Optional[List[dict]] = []
```
- Guarantees strict type safety and schema validation for all sync server HTTP inputs.
