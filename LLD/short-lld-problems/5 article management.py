"""
RIPPLING CODING ROUND 3 — Article Management / Voting System
=============================================================
Users upvote or downvote articles. A *flip* is switching UP↔DOWN on the
same article (first vote is NOT a flip; repeating the same vote is a no-op).

Part 1:
  add_article / upvote / downvote / print_last_k_flipped_articles

Part 2 (analytics follow-up):
  get_top_k_articles_by_score / get_last_voted_article

Patterns:
  * Facade  — ArticleManagementSystem exposes the interview API
  * State   — Vote enum tracks UP/DOWN; transitions drive score + flip logic

Core data structures
---------------------
_article_names : dict[article_id -> name]
                 source of truth for article existence; used for name lookup.
                 Keeping names separate from scores keeps each dict single-purpose.

_votes         : dict[(user_id, article_id) -> Vote]
                 current vote per (user, article) pair; O(1) lookup to detect
                 first vote, repeat vote, or genuine flip.

_scores        : dict[article_id -> int]
                 running net score (upvotes - downvotes); updated in O(1) on
                 every vote by applying the delta directly (no recount needed).

_flip_history  : dict[user_id -> OrderedDict[article_id, None]]
                 ordered set per user: O(1) insert + O(1) move-to-end (recency),
                 while staying unique per article (re-flip just bumps recency).

_last_voted    : dict[user_id -> article_id]
                 O(1) "last touched" pointer; overwritten on every vote action.
"""

from enum import Enum
from typing import Dict, Optional, Tuple, List
from collections import OrderedDict, defaultdict
import heapq


class Vote(Enum):
    UP = 1
    DOWN = -1


class ArticleManagementSystem:
    """Facade exposing the interview-facing API."""

    def __init__(self):
        self._article_names: Dict[str, str] = {}
        # source of truth for which articles exist; needed to reject votes on
        # unknown articles (can't rely on _scores because a new article has no votes yet)

        self._votes: Dict[Tuple[str, str], Vote] = {}
        self._scores: Dict[str, int] = defaultdict(int)
        self._flip_history: Dict[str, "OrderedDict[str, None]"] = defaultdict(OrderedDict)
        self._last_voted: Dict[str, str] = {}

    # ---------------- Part 1 ----------------

    def add_article(self, article_id: str, name: str) -> None:
        self._article_names[article_id] = name
        self._scores.setdefault(article_id, 0)  # show up in top-k even with 0 votes

    def upvote(self, user_id: str, article_id: str) -> None:
        self._vote(user_id, article_id, Vote.UP)

    def downvote(self, user_id: str, article_id: str) -> None:
        self._vote(user_id, article_id, Vote.DOWN)

    def _vote(self, user_id: str, article_id: str, new_vote: Vote) -> None:
        if article_id not in self._article_names:
            raise ValueError(f"Unknown article: {article_id}")

        self._last_voted[user_id] = article_id  # any vote action counts as "last touched"

        key = (user_id, article_id)
        current_vote = self._votes.get(key)

        if current_vote is None:
            # first-ever vote on this article by this user -> not a flip
            self._votes[key] = new_vote
            self._scores[article_id] += new_vote.value
            return

        if current_vote == new_vote:
            return  # repeating the same vote -> no-op, no score change, no flip

        # genuine flip: e.g. UP(+1) -> DOWN(-1) is a swing of -2; DOWN -> UP is +2
        self._votes[key] = new_vote
        self._scores[article_id] += 2 * new_vote.value
        self._record_flip(user_id, article_id)

    def _record_flip(self, user_id: str, article_id: str) -> None:
        history = self._flip_history[user_id]
        if article_id in history:
            history.move_to_end(article_id)  # re-flip -> just refresh recency
        else:
            history[article_id] = None

    def print_last_k_flipped_articles(self, user_id: str, k: int) -> List[str]:
        history = self._flip_history.get(user_id, OrderedDict())
        most_recent_first = list(reversed(list(history.keys())[-k:]))
        names = [self._article_names.get(a) for a in most_recent_first]
        for name in names:
            print(name)
        return names

    # ---------------- Part 2: analytics ----------------

    def get_top_k_articles_by_score(self, k: int) -> List[Tuple[str, int]]:
        # heapq.nlargest: O(n log k), avoids a full O(n log n) sort for small k
        return heapq.nlargest(k, self._scores.items(), key=lambda pair: pair[1])

    def get_last_voted_article(self, user_id: str) -> Optional[str]:
        article_id = self._last_voted.get(user_id)
        return self._article_names.get(article_id) if article_id else None


# ---------------- sanity checks ----------------
if __name__ == "__main__":
    ams = ArticleManagementSystem()
    ams.add_article("a1", "Intro to Rust")
    ams.add_article("a2", "Python Tricks")
    ams.add_article("a3", "Async Patterns")

    # first vote is never a flip
    ams.upvote("u1", "a1")
    assert ams._scores["a1"] == 1
    ams.print_last_k_flipped_articles("u1", 5) == []

    # repeat vote -> no-op
    ams.upvote("u1", "a1")
    assert ams._scores["a1"] == 1

    # genuine flip UP -> DOWN: -2 swing
    ams.downvote("u1", "a1")
    assert ams._scores["a1"] == -1
    assert ams.print_last_k_flipped_articles("u1", 5) == ["Intro to Rust"]

    # flip back DOWN -> UP: +2 swing
    ams.upvote("u1", "a1")
    assert ams._scores["a1"] == 1

    # flips on other articles, recency ordering
    ams.upvote("u1", "a2")
    ams.downvote("u1", "a2")   # flip #2 (article a2)
    ams.upvote("u1", "a3")
    ams.downvote("u1", "a3")   # flip #3 (article a3)
    ams.downvote("u1", "a1")   # flip #4 (article a1 again -> bumped to most recent)

    assert ams.print_last_k_flipped_articles("u1", 3) == [
        "Intro to Rust", "Async Patterns", "Python Tricks"
    ]

    # top-k by score
    ams.upvote("u2", "a2")
    ams.upvote("u3", "a2")
    top2 = ams.get_top_k_articles_by_score(2)
    assert top2[0][0] == "a2"  # a2 has the highest score now

    # last voted article
    assert ams.get_last_voted_article("u1") == "Intro to Rust"

    print("ALL PASSED")
