"""
RIPPLING SIGNATURE PROBLEM #4 — Org Tree (height + restructuring)
=================================================================
Input: two parallel arrays `managers` and `reportees`, where
       managers[i] is the manager of reportees[i]. The CEO is node 1
       and is the root of the org tree.

Part A: Find the height of the org tree (the level of the employee
        farthest from the CEO). CEO is level 0.

Part B (the hard follow-up): The CEO wants the tree height capped at h.
        Any employee deeper than level h is re-attached to report DIRECTLY
        to the CEO, while the subtree under them stays intact. Do it so the
        number of NEW direct reports added to the CEO is MINIMIZED, while
        keeping the overall height within h.
"""

from collections import defaultdict


def build_tree(managers, reportees):
    """adj[manager] -> list of direct reports. O(n)."""
    adj = defaultdict(list)
    for m, r in zip(managers, reportees):
        adj[m].append(r)
    return adj


# ---------- Part A ----------
def org_height(managers, reportees, ceo=1):
    """
    BFS from the CEO; height = deepest level reached.
    Time O(n), Space O(n).
    """
    # adj = build_tree(managers, reportees)
    # q = deque([(ceo, 0)])
    # height = 0
    # while q:
    #     node, level = q.popleft()
    #     height = max(height, level)
    #     for child in adj[node]:
    #         q.append((child, level + 1))
    # return height

    adj = build_tree(managers, reportees)
    def dfs(node, level):
        height = level
        for child in adj[node]:
            height = max(height, dfs(child, level + 1))
        return height
    return dfs(ceo, 0)


# ---------- Part B ----------
def restructure_to_height(managers, reportees, h, ceo=1):
    """
    Promote the MINIMUM number of nodes to be direct reports of the CEO so
    that every node is within depth h of the CEO.

    GREEDY (provably minimal): walk down from the CEO tracking each node's
    depth relative to its current root. The moment a child would land at
    depth h+1, promote that child -> it becomes a new root at depth 1, and
    we keep descending its subtree from depth 1. You cannot promote later
    (h+1 already violates) and promoting earlier wastes a cut, so promoting
    exactly at h+1 is optimal. This also handles trees deeper than 2h
    (a promoted subtree can itself trigger more promotions).

    Returns (num_new_direct_reports, promoted_nodes).
    Time O(n), Space O(n).
    """
    if h < 1:
        raise ValueError("h must be >= 1 (CEO needs at least one level of reports)")
    adj = build_tree(managers, reportees)
    promoted = []
    def visit(node, depth):
        for child in adj[node]:
            if depth + 1 > h:
                promoted.append(child)
                visit(child, 1)           # promoted → restart depth at 1
            else:
                visit(child, depth + 1)
    visit(ceo, 0)
    return len(promoted), promoted


def _demo():
    # CEO(1) -> 2,3 ; 2 -> 4,5 ; 4 -> 6 ; 6 -> 7
    # levels: 1=0 | 2,3=1 | 4,5=2 | 6=3 | 7=4   => height 4
    managers  = [1, 1, 2, 2, 4, 6]
    reportees = [2, 3, 4, 5, 6, 7]

    assert org_height(managers, reportees) == 4
    print("height ->", org_height(managers, reportees))

    # Cap at h=2. Depth-3 node (6) is the first violator -> promote 6.
    # 6's subtree (7) moves with it: 6 at depth1, 7 at depth2 -> within h=2.
    # Only 1 new direct report needed.
    count, nodes = restructure_to_height(managers, reportees, h=2)
    assert count == 1 and nodes == [6], (count, nodes)
    print(f"cap at h=2 -> {count} new direct report(s) to CEO: {nodes}")

    # Cap at h=1: every node below the CEO's children must be promoted.
    # Children 2,3 stay (depth1). 4,5 (depth2) -> promote. 6 (was depth3) becomes
    # child of promoted 4 at depth2 -> promote again. 7 -> promote again.
    count2, nodes2 = restructure_to_height(managers, reportees, h=1)
    print(f"cap at h=1 -> {count2} new direct report(s): {sorted(nodes2)}")
    assert count2 == 4 and sorted(nodes2) == [4, 5, 6, 7], (count2, nodes2)

    print("All assertions passed ✔")


if __name__ == "__main__":
    _demo()
