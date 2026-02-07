"""Synchronous client for owockibot Bounty Board API."""

import time
from typing import Optional, List
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import json

from .models import Bounty, Stats, ClaimResult, SubmitResult


class BountyBoardError(Exception):
    """Base exception for bounty board errors."""
    pass


class BountyAlreadyClaimedError(BountyBoardError):
    """Raised when bounty is already claimed."""
    def __init__(self, claimed_by: str, claimed_at: int):
        self.claimed_by = claimed_by
        self.claimed_at = claimed_at
        super().__init__(f"Bounty already claimed by {claimed_by}")


class BountyClient:
    """
    Synchronous client for the owockibot Bounty Board API.
    
    Example:
        >>> client = BountyClient()
        >>> bounties = client.list_bounties(status="open")
        >>> for b in bounties:
        ...     print(f"{b.title}: {b.reward_formatted}")
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
        Initialize the client.
        
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
    
    def _request(
        self, 
        method: str, 
        path: str, 
        data: Optional[dict] = None
    ) -> dict:
        """Make HTTP request with retry logic."""
        url = f"{self.base_url}{path}"
        
        for attempt in range(self.max_retries):
            try:
                req = Request(url, method=method)
                req.add_header("Content-Type", "application/json")
                
                body = None
                if data:
                    body = json.dumps(data).encode("utf-8")
                
                with urlopen(req, body, timeout=30) as response:
                    return json.loads(response.read().decode("utf-8"))
                    
            except HTTPError as e:
                error_body = e.read().decode("utf-8")
                try:
                    error_data = json.loads(error_body)
                except:
                    error_data = {"error": error_body}
                
                if e.code == 409 and "claimed" in error_data.get("error", "").lower():
                    raise BountyAlreadyClaimedError(
                        error_data.get("claimedBy", "unknown"),
                        error_data.get("claimedAt", 0)
                    )
                
                if attempt < self.max_retries - 1 and e.code >= 500:
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue
                    
                raise BountyBoardError(f"API error {e.code}: {error_data}")
            except Exception as e:
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue
                raise BountyBoardError(f"Request failed: {e}")
        
        raise BountyBoardError("Max retries exceeded")
    
    def list_bounties(
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
        data = self._request("GET", "/bounties")
        bounties = [Bounty.from_dict(b) for b in data]
        
        if status:
            bounties = [b for b in bounties if b.status == status]
        
        if tags:
            bounties = [b for b in bounties if any(t in b.tags for t in tags)]
        
        return bounties
    
    def get_bounty(self, bounty_id: str) -> Bounty:
        """
        Get a specific bounty by ID.
        
        Args:
            bounty_id: The bounty ID
            
        Returns:
            Bounty object
        """
        data = self._request("GET", f"/bounties/{bounty_id}")
        return Bounty.from_dict(data)
    
    def claim_bounty(
        self, 
        bounty_id: str, 
        wallet_address: Optional[str] = None
    ) -> ClaimResult:
        """
        Claim a bounty.
        
        Args:
            bounty_id: The bounty ID to claim
            wallet_address: Wallet address (uses default if not provided)
            
        Returns:
            ClaimResult with claim details
            
        Raises:
            BountyAlreadyClaimedError: If bounty is already claimed
        """
        address = wallet_address or self.wallet_address
        if not address:
            raise ValueError("Wallet address required")
        
        data = self._request("POST", f"/bounties/{bounty_id}/claim", {
            "address": address
        })
        
        from datetime import datetime
        return ClaimResult(
            id=data["id"],
            status=data["status"],
            claimed_at=datetime.fromtimestamp(data["claimedAt"] / 1000),
            claimed_by=data["claimedBy"]
        )
    
    def submit_bounty(
        self, 
        bounty_id: str,
        submission: str,
        proof: Optional[str] = None,
        wallet_address: Optional[str] = None
    ) -> SubmitResult:
        """
        Submit work for a bounty.
        
        Args:
            bounty_id: The bounty ID
            submission: Description of the work done
            proof: Optional link to proof (e.g., GitHub URL)
            wallet_address: Wallet address (uses default if not provided)
            
        Returns:
            SubmitResult with submission details
        """
        address = wallet_address or self.wallet_address
        if not address:
            raise ValueError("Wallet address required")
        
        payload = {
            "address": address,
            "submission": submission
        }
        if proof:
            payload["proof"] = proof
        
        data = self._request("POST", f"/bounties/{bounty_id}/submit", payload)
        
        return SubmitResult(
            id=data["id"],
            status=data["status"],
            submission_id=data["submissions"][-1]["id"]
        )
    
    def get_stats(self) -> Stats:
        """
        Get platform statistics.
        
        Returns:
            Stats object with platform metrics
        """
        data = self._request("GET", "/stats")
        return Stats.from_dict(data)
    
    def discover(self, tags: Optional[List[str]] = None) -> List[Bounty]:
        """
        Discover open bounties (alias for list_bounties with status=open).
        
        Args:
            tags: Optional tags to filter by
            
        Returns:
            List of open bounties
        """
        return self.list_bounties(status="open", tags=tags)
