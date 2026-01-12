"""
Discount utilities for validating and applying discount codes
"""
from datetime import datetime
from typing import Optional, Dict, Any
from utils.database_utils import execute_query


def get_discount_by_id(discount_id: int) -> Optional[Dict[str, Any]]:
    """
    Get discount details by ID.
    
    Args:
        discount_id: Discount ID
    
    Returns:
        Discount record or None if not found
    """
    results = execute_query(
        "SELECT * FROM discounts WHERE id = ?",
        (discount_id,)
    )
    return results[0] if results else None


def get_discount_by_code(code: str) -> Optional[Dict[str, Any]]:
    """
    Get discount details by code.
    
    Args:
        code: Discount code (case-insensitive)
    
    Returns:
        Discount record or None if not found
    """
    results = execute_query(
        "SELECT * FROM discounts WHERE LOWER(code) = LOWER(?)",
        (code,)
    )
    return results[0] if results else None


def is_discount_valid(discount: Dict[str, Any]) -> bool:
    """
    Check if a discount is currently valid (within date range).
    
    Args:
        discount: Discount record from DB
    
    Returns:
        True if discount is active, False otherwise
    """
    now = datetime.utcnow().isoformat()
    
    # Check start date
    if discount.get("starts_at") and discount["starts_at"] > now:
        return False
    
    # Check end date
    if discount.get("ends_at") and discount["ends_at"] < now:
        return False
    
    return True


def calculate_discount(discount: Dict[str, Any], amount: float) -> float:
    """
    Calculate discount amount based on percent or flat amount.
    
    Args:
        discount: Discount record
        amount: Original payment amount
    
    Returns:
        Discount amount (positive value to subtract)
    """
    if discount.get("percent"):
        # Percentage discount
        discount_amount = amount * (discount["percent"] / 100.0)
    elif discount.get("amount"):
        # Flat amount discount
        discount_amount = discount["amount"]
    else:
        discount_amount = 0.0
    
    # Discount cannot exceed original amount
    return min(discount_amount, amount)


def apply_discount_to_payment(
    code: str,
    amount: float
) -> tuple[bool, float, Optional[str]]:
    """
    Validate discount code and calculate final amount after discount.
    
    Args:
        code: Discount code to apply
        amount: Original payment amount
    
    Returns:
        Tuple of (success, final_amount, error_message)
        - success: True if discount was applied, False if error
        - final_amount: Amount after discount (original if no discount)
        - error_message: Error description if success is False, None otherwise
    """
    if not code:
        return True, amount, None
    
    # Look up discount
    discount = get_discount_by_code(code)
    if not discount:
        return False, amount, "Discount code not found"
    
    # Check if discount is valid
    if not is_discount_valid(discount):
        return False, amount, "Discount code has expired or not yet active"
    
    # Calculate discount
    discount_amount = calculate_discount(discount, amount)
    final_amount = amount - discount_amount
    
    return True, final_amount, None
