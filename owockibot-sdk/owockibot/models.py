"""Data models for owockibot SDK."""

from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime


@dataclass
class Submission:
    """A bounty submission."""
    id: str
    content: str
    proof: Optional[str]
    submitted_at: datetime


@dataclass
class Payment:
    """Payment information for completed bounty."""
    chain: str
    token: str
    tx_hash: str
    gross_reward: int
    net_reward: int
    fee: int
    fee_percent: str
    processed_at: datetime


@dataclass
class Bounty:
    """A bounty from the bounty board."""
    id: str
    uuid: str
    title: str
    description: str
    reward: int
    reward_formatted: str
    status: str
    creator: str
    deadline: Optional[datetime]
    tags: List[str]
    requirements: List[str]
    submissions: List[Submission]
    claimed_by: Optional[str] = None
    claimed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    payment: Optional[Payment] = None
    
    @classmethod
    def from_dict(cls, data: dict) -> "Bounty":
        """Create Bounty from API response dict."""
        submissions = [
            Submission(
                id=s["id"],
                content=s["content"],
                proof=s.get("proof"),
                submitted_at=datetime.fromtimestamp(s["submittedAt"] / 1000)
            )
            for s in data.get("submissions", [])
        ]
        
        payment = None
        if data.get("payment") and data["payment"].get("chain"):
            p = data["payment"]
            payment = Payment(
                chain=p.get("chain", "base"),
                token=p.get("token", "USDC"),
                tx_hash=p.get("txHash", ""),
                gross_reward=p.get("grossReward", 0),
                net_reward=p.get("netReward", 0),
                fee=p.get("fee", 0),
                fee_percent=p.get("feePercent", "0%"),
                processed_at=datetime.fromisoformat(p["processedAt"].replace("Z", "+00:00")) if p.get("processedAt") else datetime.now()
            )
        
        deadline = None
        if data.get("deadline"):
            if isinstance(data["deadline"], int):
                deadline = datetime.fromtimestamp(data["deadline"] / 1000)
            else:
                deadline = datetime.fromisoformat(data["deadline"])
        
        return cls(
            id=data.get("id", ""),
            uuid=data.get("uuid", ""),
            title=data.get("title", ""),
            description=data.get("description", ""),
            reward=int(float(data.get("reward", 0))),
            reward_formatted=data.get("rewardFormatted", "0 USDC"),
            status=data.get("status", "unknown"),
            creator=data.get("creator", ""),
            deadline=deadline,
            tags=data.get("tags", []),
            requirements=data.get("requirements", []),
            submissions=submissions,
            claimed_by=data.get("claimedBy"),
            claimed_at=datetime.fromtimestamp(data["claimedAt"] / 1000) if data.get("claimedAt") else None,
            completed_at=datetime.fromtimestamp(data["completedAt"] / 1000) if data.get("completedAt") else None,
            payment=payment
        )


@dataclass
class Stats:
    """Platform statistics."""
    total_bounties: int
    open_bounties: int
    claimed_bounties: int
    completed_bounties: int
    total_payouts: int
    total_payouts_formatted: str
    
    @classmethod
    def from_dict(cls, data: dict) -> "Stats":
        return cls(
            total_bounties=data.get("totalBounties", 0),
            open_bounties=data.get("openBounties", 0),
            claimed_bounties=data.get("claimedBounties", 0),
            completed_bounties=data.get("completedBounties", 0),
            total_payouts=data.get("totalPayouts", 0),
            total_payouts_formatted=data.get("totalPayoutsFormatted", "0 USDC")
        )


@dataclass
class ClaimResult:
    """Result of claiming a bounty."""
    id: str
    status: str
    claimed_at: datetime
    claimed_by: str


@dataclass 
class SubmitResult:
    """Result of submitting work."""
    id: str
    status: str
    submission_id: str
