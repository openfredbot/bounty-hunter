"""Asynchronous client for owockibot Bounty Board API."""

import asyncio
import aiohttp
from typing import Optional, List

from .models import Bounty, Stats, ClaimResult, SubmitResult
from .client import BountyBoardError, BountyAlreadyClaimedError


class AsyncBountyClient:
    """
    Asynchronous client for the owockibot Bounty Board API.
    
    Example:
        >>> async with AsyncBountyClient() as client:
        ...     bounties = await client.list_bounties(status="open")
        ...     for b in bounties:
        ...         print(f"{b.title}: {b.reward_formatted}")
    """
    
    BASE_URL = "https://bounty.owockibot.xyz"
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        wallet_address: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        """
        Initialize the async client.
        
        Args:
            base_url: API base URL (default: https://bounty.owockibot.xyz)
            wallet_address: Default wallet address for claims/submissions
            max_retries: Maximum number of retries for failed requests
            retry_delay: Delay between retries in seconds
        """
        self.base_url = (base_url or self.BASE_URL).rstrip("/")
        self.wallet_address = wallet_address
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self._session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session:
            await self._session.close()
    
    async def _ensure_session(self):
        if not self._session:
            self._session = aiohttp.ClientSession()
    
    async def close(self):
        """Close the client session."""
        if self._session:
            await self._session.close()
            self._session = None
    
    async def _request(
        self,
        method: str,
        path: str,
        data: Optional[dict] = None
    ) -> dict:
        """Make HTTP request with retry logic."""
        await self._ensure_session()
        url = f"{self.base_url}{path}"
        
        for attempt in range(self.max_retries):
            try:
                async with self._session.request(
                    method,
                    url,
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    response_data = await response.json()
                    
                    if response.status >= 400:
                        error_msg = response_data.get("error", "Unknown error")
                        
                        if response.status == 409 and "claimed" in error_msg.lower():
                            raise BountyAlreadyClaimedError(
                                response_data.get("claimedBy", "unknown"),
                                response_data.get("claimedAt", 0)
                            )
                        
                        if attempt < self.max_retries - 1 and response.status >= 500:
                            await asyncio.sleep(self.retry_delay * (attempt + 1))
                            continue
                        
                        raise BountyBoardError(f"API error {response.status}: {error_msg}")
                    
                    return response_data
                    
            except (BountyBoardError, BountyAlreadyClaimedError):
                raise
            except Exception as e:
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    continue
                raise BountyBoardError(f"Request failed: {e}")
        
        raise BountyBoardError("Max retries exceeded")
    
    async def list_bounties(
        self,
        status: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[Bounty]:
        """
        List all bounties.
        
        Args:
            status: Filter by status (open, claimed, submitted, completed)
            tags: Filter by tags
            
        Returns:
            List of Bounty objects
        """
        data = await self._request("GET", "/bounties")
        bounties = [Bounty.from_dict(b) for b in data]
        
        if status:
            bounties = [b for b in bounties if b.status == status]
        
        if tags:
            bounties = [b for b in bounties if any(t in b.tags for t in tags)]
        
        return bounties
    
    async def get_bounty(self, bounty_id: str) -> Bounty:
        """Get a specific bounty by ID."""
        data = await self._request("GET", f"/bounties/{bounty_id}")
        return Bounty.from_dict(data)
    
    async def claim_bounty(
        self,
        bounty_id: str,
        wallet_address: Optional[str] = None
    ) -> ClaimResult:
        """Claim a bounty."""
        address = wallet_address or self.wallet_address
        if not address:
            raise ValueError("Wallet address required")
        
        data = await self._request("POST", f"/bounties/{bounty_id}/claim", {
            "address": address
        })
        
        from datetime import datetime
        return ClaimResult(
            id=data["id"],
            status=data["status"],
            claimed_at=datetime.fromtimestamp(data["claimedAt"] / 1000),
            claimed_by=data["claimedBy"]
        )
    
    async def submit_bounty(
        self,
        bounty_id: str,
        submission: str,
        proof: Optional[str] = None,
        wallet_address: Optional[str] = None
    ) -> SubmitResult:
        """Submit work for a bounty."""
        address = wallet_address or self.wallet_address
        if not address:
            raise ValueError("Wallet address required")
        
        payload = {
            "address": address,
            "submission": submission
        }
        if proof:
            payload["proof"] = proof
        
        data = await self._request("POST", f"/bounties/{bounty_id}/submit", payload)
        
        return SubmitResult(
            id=data["id"],
            status=data["status"],
            submission_id=data["submissions"][-1]["id"]
        )
    
    async def get_stats(self) -> Stats:
        """Get platform statistics."""
        data = await self._request("GET", "/stats")
        return Stats.from_dict(data)
    
    async def discover(self, tags: Optional[List[str]] = None) -> List[Bounty]:
        """Discover open bounties."""
        return await self.list_bounties(status="open", tags=tags)
