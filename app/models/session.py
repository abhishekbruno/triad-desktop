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
    DRAFT = "draft"                          # Session created, question entered
    ROUND_1_READY = "round_1_ready"          # Initial prompt formulated and staged
    AWAITING_RESPONSES = "awaiting_responses"# Prompts copied, awaiting imported answers
    ROUND_1_COMPLETE = "round_1_complete"    # All 3 required responses accepted
    INCOMPLETE = "incomplete"                # Round halted or missing answers
    CANCELLED = "cancelled"                  # Aborted by user
    ERROR = "error"                          # Technical error occurred
    # Future Phase states
    DEBATE_ROUND = "debate_round"            # Phase 3: Cross-model critique
    DEVILS_ADVOCATE = "devils_advocate"      # Phase 3: Adversarial stress-testing
    VOTING = "voting"                        # Phase 4: Ballot casting
    CONSENSUS_REACHED = "consensus_reached"  # Phase 4: Deterministic consensus
    NO_CONSENSUS = "no_consensus"            # Phase 4: 1/1/1 split or tie
    OVERRIDDEN = "overridden"                # Phase 4: Human override applied
    TERMINATED = "terminated"                # Session finalized


class AgentRoundStatus(str, Enum):
    """Round progress status for an individual agent."""
    PENDING = "pending"                      # Not yet copied
    PROMPT_STAGED = "prompt_staged"          # Staged in TRIAD
    PROMPT_COPIED = "prompt_copied"          # Copied to clipboard & window focused
    RESPONSE_ACCEPTED = "response_accepted"  # User verified and accepted response


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
    sha256_hash: str
    word_count: int = 0
    char_count: int = 0
    source_type: str = "manual_import"
    user_confirmed: bool = True
    revision_number: int = 1
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    prompt_hash: Optional[str] = None
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
class OutboundPrompt:
    """A prompt staged for clipboard transfer to an AI participant."""
    prompt_id: str
    session_id: str
    round_number: int
    agent_id: str
    prompt_text: str
    staged_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    copied_at: Optional[str] = None


@dataclass
class ReasoningRound:
    """A discrete round within a reasoning session."""
    round_number: int
    round_type: RoundType
    prompt_template_name: str
    started_at: str
    completed_at: Optional[str] = None
    prompts: Dict[str, OutboundPrompt] = field(default_factory=dict)
    responses: Dict[str, ModelResponse] = field(default_factory=dict)
    ballots: Dict[str, ModelBallot] = field(default_factory=dict)
    is_sealed: bool = False


@dataclass
class ReasoningSession:
    """Top-level reasoning session entity."""
    session_id: str
    title: str
    initial_question: str
    mode: ReasoningMode = ReasoningMode.QUICK_CONSENSUS
    max_rounds: int = 3
    state: SessionState = SessionState.DRAFT
    current_round: int = 1
    participants: List[str] = field(default_factory=lambda: ["chatgpt", "claude", "gemini"])
    agent_statuses: Dict[str, AgentRoundStatus] = field(default_factory=dict)
    prompts: Dict[str, OutboundPrompt] = field(default_factory=dict)
    responses: Dict[str, ModelResponse] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
