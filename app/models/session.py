from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class ReasoningMode(str, Enum):
    """Supported multi-agent reasoning modes."""
    QUICK_CONSENSUS = "quick_consensus"      # 1 independent round + 1 vote (fast decision)
    DEEP_DEBATE = "deep_debate"              # 1 independent round + up to 3 critique rounds + devil's advocate + vote
    RESEARCH_COUNCIL = "research_council"    # Evidence-weighted deliberation with source verification
    CODE_REVIEW = "code_review"              # Architecture, security, syntax, and performance critique
    CREATIVE_COUNCIL = "creative_council"    # Divergent exploration followed by convergent selection


class SessionState(str, Enum):
    """Lifecycle state of a reasoning session."""
    DRAFT = "draft"                          # Session created, prompt drafted
    INDEPENDENT_ROUND = "independent_round"  # Round 1: Gathering independent initial answers
    DEBATE_ROUND = "debate_round"            # Round 2+: Cross-model critique and rebuttal
    DEVILS_ADVOCATE = "devils_advocate"      # Stress-testing emerging consensus
    VOTING = "voting"                        # Collecting structured ballots
    CONSENSUS_REACHED = "consensus_reached"  # Deterministic consensus achieved
    NO_CONSENSUS = "no_consensus"            # Maximum rounds exhausted without consensus
    OVERRIDDEN = "overridden"                # Human decision override applied
    TERMINATED = "terminated"                # Manually aborted by user


class RoundType(str, Enum):
    """Type of reasoning round."""
    INDEPENDENT = "independent"
    CROSS_CRITIQUE = "cross_critique"
    REVISION = "revision"
    DEVILS_ADVOCATE = "devils_advocate"
    BALLOT = "ballot"


class ConsensusVerdict(str, Enum):
    """Mathematical verdict of a voting round."""
    UNANIMOUS = "unanimous"        # 3/3 agreement
    MAJORITY = "majority"          # 2/3 agreement
    NO_CONSENSUS = "no_consensus"  # 1/1/1 split or tie
    INCOMPLETE = "incomplete"      # Missing ballots
    ABSTAINED = "abstained"        # Abstention occurred


class ClaimCategory(str, Enum):
    """Category classification for structured claims."""
    FACTUAL = "factual"
    METHODOLOGICAL = "methodological"
    ARCHITECTURAL = "architectural"
    ASSUMPTION = "assumption"
    RECOMMENDATION = "recommendation"


class VerificationStatus(str, Enum):
    """Verification status of a structured claim."""
    UNVERIFIED = "unverified"
    SUPPORTED = "supported"
    DISPUTED = "disputed"
    REFUTED = "refuted"


@dataclass
class StructuredClaim:
    """An individual atomic claim extracted from a model response."""
    claim_id: str
    response_id: str
    agent_id: str
    statement: str
    category: ClaimCategory = ClaimCategory.FACTUAL
    evidence: Optional[str] = None
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    supporting_agents: List[str] = field(default_factory=list)
    opposing_agents: List[str] = field(default_factory=list)


@dataclass
class ModelResponse:
    """An immutable response captured from a participating desktop AI application."""
    response_id: str
    session_id: str
    round_number: int
    agent_id: str
    prompt_sent: str
    raw_response: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    prompt_hash: Optional[str] = None
    word_count: int = 0
    claims: List[StructuredClaim] = field(default_factory=list)
    is_sealed: bool = True  # Round 1 answers are sealed until all 3 participants submit


@dataclass
class ModelBallot:
    """A structured ballot cast by a model in a voting round."""
    ballot_id: str
    session_id: str
    round_number: int
    agent_id: str
    selected_candidate_id: str
    candidate_title: str
    confidence_score: float
    justification: str
    dissent_explanation: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class CandidateProposal:
    """A distinct proposed solution or thesis identified in the discussion."""
    candidate_id: str
    title: str
    summary: str
    proposed_by: str
    first_round: int
    revised_in_round: Optional[int] = None
    key_arguments: List[str] = field(default_factory=list)


@dataclass
class ConsensusDecision:
    """The final deterministic output of a consensus calculation."""
    decision_id: str
    session_id: str
    verdict: ConsensusVerdict
    winning_candidate_id: Optional[str]
    winning_candidate_title: Optional[str]
    vote_tally: Dict[str, int]
    participating_agents: List[str]
    dissenting_agents: List[str]
    consensus_summary: str
    minority_report: Optional[str] = None
    human_override_active: bool = False
    human_override_reason: Optional[str] = None
    calculated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class DisagreementPoint:
    """An active disagreement mapped across participants."""
    disagreement_id: str
    session_id: str
    topic: str
    agent_positions: Dict[str, str]  # {agent_id: position_summary}
    unresolved: bool = True
    core_conflict: str = ""


@dataclass
class ReasoningRound:
    """A discrete round within a reasoning session."""
    round_number: int
    round_type: RoundType
    prompt_template_name: str
    started_at: str
    completed_at: Optional[str] = None
    responses: Dict[str, ModelResponse] = field(default_factory=dict)
    ballots: Dict[str, ModelBallot] = field(default_factory=dict)
    is_sealed: bool = False


@dataclass
class ReasoningSession:
    """Top-level reasoning session entity."""
    session_id: str
    title: str
    initial_prompt: str
    mode: ReasoningMode
    max_rounds: int
    state: SessionState = SessionState.DRAFT
    current_round: int = 0
    participants: List[str] = field(default_factory=lambda: ["chatgpt", "claude", "gemini"])
    devils_advocate_enabled: bool = True
    devils_advocate_agent: Optional[str] = None
    proposals: List[CandidateProposal] = field(default_factory=list)
    rounds: List[ReasoningRound] = field(default_factory=list)
    disagreements: List[DisagreementPoint] = field(default_factory=list)
    final_decision: Optional[ConsensusDecision] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
