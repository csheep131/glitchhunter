"""
Ensemble Voting Engine für GlitchHunter v2.0

Koordiniert mehrere Modelle und wählt den besten Fix durch Voting.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
from enum import Enum
import hashlib
import json

logger = logging.getLogger(__name__)


class VoteStrategy(Enum):
    """Voting-Strategien für Ensemble."""
    MAJORITY = "majority"           # Einfache Mehrheit
    WEIGHTED = "weighted"           # Gewichtet nach Modell-Performance
    CONFIDENCE = "confidence"       # Höchste Konfidenz gewinnt
    CONSENSUS = "consensus"         # Alle Modelle müssen übereinstimmen


@dataclass
class ModelVote:
    """Stimme eines einzelnen Modells."""
    model_id: str
    model_name: str
    fix_proposal: str
    confidence: float
    reasoning: str
    response_time_ms: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "model_name": self.model_name,
            "fix_proposal": self.fix_proposal,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "response_time_ms": self.response_time_ms,
            "metadata": self.metadata,
        }


@dataclass  
class VoteResult:
    """Ergebnis des Ensemble-Votings."""
    winning_fix: str
    winning_model: str
    confidence_score: float
    strategy_used: VoteStrategy
    total_votes: int
    agreement_ratio: float
    all_votes: List[ModelVote]
    consensus_reached: bool
    explanation: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "winning_fix": self.winning_fix,
            "winning_model": self.winning_model,
            "confidence_score": self.confidence_score,
            "strategy_used": self.strategy_used.value,
            "total_votes": self.total_votes,
            "agreement_ratio": self.agreement_ratio,
            "all_votes": [v.to_dict() for v in self.all_votes],
            "consensus_reached": self.consensus_reached,
            "explanation": self.explanation,
            "timestamp": self.timestamp.isoformat(),
        }


class VotingEngine:
    """
    Ensemble Voting Engine für Multi-Model Fix-Generierung.
    
    Features:
    - Parallele Anfragen an mehrere Modelle
    - Mehrere Voting-Strategien
    - Intelligente Deduplizierung ähnlicher Fixes
    - Performance-Tracking pro Modell
    """
    
    def __init__(
        self,
        strategy: VoteStrategy = VoteStrategy.WEIGHTED,
        min_confidence: float = 0.7,
        timeout_seconds: float = 60.0,
    ):
        self.strategy = strategy
        self.min_confidence = min_confidence
        self.timeout_seconds = timeout_seconds
        self.model_weights: Dict[str, float] = {}
        self.model_performance: Dict[str, Dict[str, Any]] = {}
        self._fix_cache: Dict[str, str] = {}
        
    def register_model(self, model_id: str, weight: float = 1.0) -> None:
        """Registriert ein Modell mit Gewichtung."""
        self.model_weights[model_id] = weight
        if model_id not in self.model_performance:
            self.model_performance[model_id] = {
                "total_calls": 0,
                "successful_fixes": 0,
                "avg_confidence": 0.0,
                "avg_response_time": 0.0,
            }
        logger.info(f"Modell registriert: {model_id} (Gewicht: {weight})")
        
    async def vote(
        self,
        model_calls: List[Callable[[], asyncio.Future[ModelVote]]],
        context_hash: Optional[str] = None,
    ) -> VoteResult:
        """
        Führt Ensemble-Voting durch.
        
        Args:
            model_calls: Liste von Callables, die ModelVotes zurückgeben
            context_hash: Optionaler Hash für Caching
            
        Returns:
            VoteResult mit dem besten Fix
        """
        # Cache-Check
        if context_hash and context_hash in self._fix_cache:
            logger.info(f"Cache-Hit für Context-Hash: {context_hash[:8]}...")
            cached_fix = self._fix_cache[context_hash]
            return self._create_cached_result(cached_fix)
        
        # Parallele Ausführung aller Modelle
        logger.info(f"Starte Ensemble-Voting mit {len(model_calls)} Modellen...")
        start_time = datetime.utcnow()
        
        try:
            votes = await asyncio.wait_for(
                asyncio.gather(*[call() for call in model_calls], return_exceptions=True),
                timeout=self.timeout_seconds,
            )
        except asyncio.TimeoutError:
            logger.error(f"Ensemble-Voting Timeout nach {self.timeout_seconds}s")
            votes = []
        
        # Filtere erfolgreiche Votes
        valid_votes: List[ModelVote] = []
        for i, vote in enumerate(votes):
            if isinstance(vote, Exception):
                logger.warning(f"Modell {i} fehlgeschlagen: {vote}")
            elif isinstance(vote, ModelVote):
                if vote.confidence >= self.min_confidence:
                    valid_votes.append(vote)
                    self._update_model_performance(vote)
                else:
                    logger.debug(f"Modell {vote.model_id} unter Min-Confidence: {vote.confidence}")
        
        if not valid_votes:
            logger.error("Keine gültigen Votes erhalten!")
            return self._create_empty_result()
        
        # Voting-Strategie anwenden
        if self.strategy == VoteStrategy.MAJORITY:
            result = self._majority_vote(valid_votes)
        elif self.strategy == VoteStrategy.WEIGHTED:
            result = self._weighted_vote(valid_votes)
        elif self.strategy == VoteStrategy.CONFIDENCE:
            result = self._confidence_vote(valid_votes)
        elif self.strategy == VoteStrategy.CONSENSUS:
            result = self._consensus_vote(valid_votes)
        else:
            result = self._weighted_vote(valid_votes)
        
        # Cache speichern
        if context_hash:
            self._fix_cache[context_hash] = result.winning_fix
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.info(f"Ensemble-Voting abgeschlossen in {duration:.2f}s - "
                   f"Gewinner: {result.winning_model} (Confidence: {result.confidence_score:.2f})")
        
        return result
    
    def _majority_vote(self, votes: List[ModelVote]) -> VoteResult:
        """Einfache Mehrheitsentscheidung."""
        fix_groups: Dict[str, List[ModelVote]] = {}
        
        for vote in votes:
            # Normalisiere Fix für Vergleich
            fix_key = self._normalize_fix(vote.fix_proposal)
            if fix_key not in fix_groups:
                fix_groups[fix_key] = []
            fix_groups[fix_key].append(vote)
        
        # Gruppe mit meisten Stimmen gewinnt
        best_group = max(fix_groups.values(), key=lambda g: len(g))
        best_vote = max(best_group, key=lambda v: v.confidence)
        
        total_votes = len(votes)
        agreement = len(best_group) / total_votes if total_votes > 0 else 0
        
        return VoteResult(
            winning_fix=best_vote.fix_proposal,
            winning_model=best_vote.model_name,
            confidence_score=best_vote.confidence,
            strategy_used=VoteStrategy.MAJORITY,
            total_votes=total_votes,
            agreement_ratio=agreement,
            all_votes=votes,
            consensus_reached=agreement >= 0.75,
            explanation=f"Mehrheitsentscheidung: {len(best_group)}/{total_votes} Stimmen",
        )
    
    def _weighted_vote(self, votes: List[ModelVote]) -> VoteResult:
        """Gewichtetes Voting basierend auf Modell-Performance."""
        scored_votes: List[tuple] = []
        
        for vote in votes:
            weight = self.model_weights.get(vote.model_id, 1.0)
            perf = self.model_performance.get(vote.model_id, {})
            success_rate = perf.get("successful_fixes", 0) / max(perf.get("total_calls", 1), 1)
            
            # Composite Score
            score = vote.confidence * weight * (0.5 + 0.5 * success_rate)
            scored_votes.append((score, vote))
        
        scored_votes.sort(reverse=True, key=lambda x: x[0])
        best_score, best_vote = scored_votes[0]
        
        # Agreement berechnen
        fix_key = self._normalize_fix(best_vote.fix_proposal)
        agreeing_votes = sum(1 for _, v in scored_votes if self._normalize_fix(v.fix_proposal) == fix_key)
        agreement = agreeing_votes / len(votes) if votes else 0
        
        return VoteResult(
            winning_fix=best_vote.fix_proposal,
            winning_model=best_vote.model_name,
            confidence_score=best_vote.confidence,
            strategy_used=VoteStrategy.WEIGHTED,
            total_votes=len(votes),
            agreement_ratio=agreement,
            all_votes=votes,
            consensus_reached=agreement >= 0.75,
            explanation=f"Gewichtetes Voting: {best_vote.model_name} mit Score {best_score:.2f}",
        )
    
    def _confidence_vote(self, votes: List[ModelVote]) -> VoteResult:
        """Wählt Vote mit höchster Konfidenz."""
        best_vote = max(votes, key=lambda v: v.confidence)
        
        fix_key = self._normalize_fix(best_vote.fix_proposal)
        agreeing_votes = sum(1 for v in votes if self._normalize_fix(v.fix_proposal) == fix_key)
        agreement = agreeing_votes / len(votes) if votes else 0
        
        return VoteResult(
            winning_fix=best_vote.fix_proposal,
            winning_model=best_vote.model_name,
            confidence_score=best_vote.confidence,
            strategy_used=VoteStrategy.CONFIDENCE,
            total_votes=len(votes),
            agreement_ratio=agreement,
            all_votes=votes,
            consensus_reached=agreement >= 0.75,
            explanation=f"Höchste Konfidenz: {best_vote.confidence:.2f} von {best_vote.model_name}",
        )
    
    def _consensus_vote(self, votes: List[ModelVote]) -> VoteResult:
        """Erfordert Konsens (75% Übereinstimmung)."""
        fix_groups: Dict[str, List[ModelVote]] = {}
        
        for vote in votes:
            fix_key = self._normalize_fix(vote.fix_proposal)
            if fix_key not in fix_groups:
                fix_groups[fix_key] = []
            fix_groups[fix_key].append(vote)
        
        # Suche Gruppe mit Konsens
        total_votes = len(votes)
        for fix_key, group in fix_groups.items():
            if len(group) / total_votes >= 0.75:
                best_vote = max(group, key=lambda v: v.confidence)
                return VoteResult(
                    winning_fix=best_vote.fix_proposal,
                    winning_model=best_vote.model_name,
                    confidence_score=best_vote.confidence,
                    strategy_used=VoteStrategy.CONSENSUS,
                    total_votes=total_votes,
                    agreement_ratio=len(group) / total_votes,
                    all_votes=votes,
                    consensus_reached=True,
                    explanation=f"Konsens erreicht: {len(group)}/{total_votes} Modelle einig",
                )
        
        # Kein Konsens - Fallback zu weighted
        logger.warning("Kein Konsens erreicht, Fallback zu weighted voting")
        return self._weighted_vote(votes)
    
    def _normalize_fix(self, fix: str) -> str:
        """Normalisiert einen Fix für Vergleich (Deduplizierung)."""
        # Entferne Whitespace und Kommentare für Vergleich
        lines = fix.strip().split('\n')
        normalized = []
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                normalized.append(line)
        return hashlib.md5('\n'.join(normalized).encode()).hexdigest()[:16]
    
    def _update_model_performance(self, vote: ModelVote) -> None:
        """Aktualisiert Performance-Metriken eines Modells."""
        model_id = vote.model_id
        if model_id not in self.model_performance:
            return
        
        perf = self.model_performance[model_id]
        perf["total_calls"] += 1
        
        # Rolling average für Confidence
        n = perf["total_calls"]
        perf["avg_confidence"] = (perf["avg_confidence"] * (n - 1) + vote.confidence) / n
        perf["avg_response_time"] = (perf["avg_response_time"] * (n - 1) + vote.response_time_ms) / n
    
    def _create_cached_result(self, cached_fix: str) -> VoteResult:
        """Erstellt ein Result aus Cache."""
        return VoteResult(
            winning_fix=cached_fix,
            winning_model="cache",
            confidence_score=1.0,
            strategy_used=self.strategy,
            total_votes=0,
            agreement_ratio=1.0,
            all_votes=[],
            consensus_reached=True,
            explanation="Aus Cache geladen",
        )
    
    def _create_empty_result(self) -> VoteResult:
        """Erstellt ein leeres Result bei Fehler."""
        return VoteResult(
            winning_fix="",
            winning_model="none",
            confidence_score=0.0,
            strategy_used=self.strategy,
            total_votes=0,
            agreement_ratio=0.0,
            all_votes=[],
            consensus_reached=False,
            explanation="Keine gültigen Votes erhalten",
        )
    
    def get_model_stats(self) -> Dict[str, Dict[str, Any]]:
        """Gibt Performance-Statistiken aller Modelle zurück."""
        return self.model_performance.copy()