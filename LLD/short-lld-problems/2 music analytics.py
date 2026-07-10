"""
RIPPLING SIGNATURE PROBLEM #2 — Music Analytics System
======================================================
APIs:
  add_song(song_id)
  play_song(user_id, song_id)
  print_analytics()                      -> most-played songs by UNIQUE users
  print_recently_played(user_id)         -> a user's recently played UNIQUE songs
  print_recently_played(user_id, k)      -> last k unique songs

KEY MODELING IDEAS
  * "Most played by unique users" => count DISTINCT users per song, not raw plays.
    Keep song_id -> set(user_id); rank by len(set).
  * "Recently played unique" => an ordered, de-duplicated history per user.
    A re-play moves the song to the front (most-recent), keeping uniqueness.
"""

from collections import OrderedDict
import heapq


class MusicAnalytics:
    def __init__(self):
        self._songs = set()                       # known songs
        self._unique_listeners = {}               # song_id -> set(user_id)
        self._recent = {}                         # user_id -> OrderedDict(song_id -> None)

    def add_song(self, song_id):
        """O(1)"""
        self._songs.add(song_id)
        self._unique_listeners.setdefault(song_id, set())

    def play_song(self, user_id, song_id):
        """
        O(1) amortized.
        - records the user as a unique listener of the song
        - moves the song to the most-recent position in the user's history
        """
        if song_id not in self._songs:
            self.add_song(song_id)                # clarify: auto-add or reject?
        self._unique_listeners[song_id].add(user_id)

        hist = self._recent.setdefault(user_id, OrderedDict())
        if song_id in hist:
            hist.move_to_end(song_id)             # bump to most-recent
        else:
            hist[song_id] = None

    def most_played_by_unique_users(self, top=None):
        """
        Songs ranked by number of distinct listeners (desc).
        O(S log S) where S = number of songs. Use a heap for top-k if S is huge.
        """
        items = self._unique_listeners.items()
        if top is None:
            ranked = sorted(
                items,
                key=lambda kv: (-len(kv[1]), kv[0]),
            )
            return [(song, len(users)) for song, users in ranked]
        
        top_items = heapq.nsmallest(
            top,
            items,
            key=lambda kv: (-len(kv[1]), kv[0]),  # same tie-break as full sort
        )
        return [(song, len(users)) for song, users in top_items]

    def recently_played(self, user_id, k=None):
        """
        A user's unique songs, MOST RECENT FIRST.
        O(k) (or O(history) if k is None).
        """
        hist = self._recent.get(user_id)
        if not hist:
            return []
        ordered = list(reversed(hist))            # OrderedDict keys, newest last -> reverse
        return ordered if k is None else ordered[:k]

    # convenience printers matching the interview API names
    def print_analytics(self):
        print("Most played (by unique users):", self.most_played_by_unique_users())

    def print_recently_played(self, user_id, k=None):
        print(f"Recently played by {user_id} (k={k}):", self.recently_played(user_id, k))


# ---------------------------------------------------------------------------
# FOLLOW-UPS to mention:
#   * top-k most played without sorting all songs -> maintain a heap, or a
#     bucket of counts (count -> set of songs) for O(1) updates.
#   * memory: unique-listener sets can grow large -> approximate with HyperLogLog
#     if exact counts aren't required.
# ---------------------------------------------------------------------------


def _demo():
    m = MusicAnalytics()
    for s in ("s1", "s2", "s3"):
        m.add_song(s)

    m.play_song("u1", "s1")
    m.play_song("u2", "s1")     # s1 now has 2 unique listeners
    m.play_song("u1", "s2")
    m.play_song("u1", "s1")     # re-play: s1 bumps to most-recent for u1; still 2 unique
    m.play_song("u3", "s3")

    assert m.most_played_by_unique_users() == [("s1", 2), ("s2", 1), ("s3", 1)]
    assert m.most_played_by_unique_users(top=2) == [("s1", 2), ("s2", 1)]
    # u1 most-recent first: s1 (re-played last), then s2
    assert m.recently_played("u1") == ["s1", "s2"]
    assert m.recently_played("u1", k=1) == ["s1"]

    m.print_analytics()
    m.print_recently_played("u1")
    m.print_recently_played("u1", k=1)
    print("All assertions passed ✔")


if __name__ == "__main__":
    _demo()
