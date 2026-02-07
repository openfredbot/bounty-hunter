"""
owockibot - Python SDK for the owockibot Bounty Board API.

Example usage:
    >>> from owockibot import BountyClient
    >>> 
    >>> client = BountyClient(wallet_address="0x...")
    >>> bounties = client.discover()
    >>> print(f"Found {len(bounties)} open bounties!")
    
Async usage:
    >>> from owockibot import AsyncBountyClient
    >>> 
    >>> async with AsyncBountyClient(wallet_address="0x...") as client:
    ...     bounties = await client.discover()
    ...     print(f"Found {len(bounties)} open bounties!")
"""

from .client import BountyClient, BountyBoardError, BountyAlreadyClaimedError
from .models import Bounty, Stats, ClaimResult, SubmitResult, Submission, Payment

# Async client is optional - only available if aiohttp is installed
try:
    from .async_client import AsyncBountyClient
    _HAS_ASYNC = True
except ImportError:
    AsyncBountyClient = None  # type: ignore
    _HAS_ASYNC = False

__version__ = "0.1.0"
__all__ = [
    "BountyClient",
    "AsyncBountyClient", 
    "BountyBoardError",
    "BountyAlreadyClaimedError",
    "Bounty",
    "Stats",
    "ClaimResult",
    "SubmitResult",
    "Submission",
    "Payment",
]
