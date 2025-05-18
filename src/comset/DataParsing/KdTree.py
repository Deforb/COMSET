from __future__ import annotations
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..COMSETsystem.Link import Link
    from ..COMSETsystem.Vertex import Point2D


class KdTree:
    """
    Modified from Michael <GrubenM@GMail.com>'s code (https://github.com/mgruben/Kd-Trees) to index
    2D line segments (i.e., links) instead of 2D points.
    """

    """
    Copyright (C) 2019 Bo <boxu08@gmail.com>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

    Below is the original license notice from Michael <GrubenM@GMail.com> 

    Copyright (C) 2016 Michael <GrubenM@GMail.com>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
    """

    class Node:
        def __init__(self, link: Link) -> None:
            self.link = link
            self.min_x = link.min_x
            self.min_y = link.min_y
            self.max_x = link.max_x
            self.max_y = link.max_y
            self.lb: Optional[KdTree.Node] = None  # left/bottom subtree
            self.rt: Optional[KdTree.Node] = None  # right/top subtree

        def extend_range(self, link: Link) -> None:
            self.min_x = min(self.min_x, link.min_x)
            self.min_y = min(self.min_y, link.min_y)
            self.max_x = max(self.max_x, link.max_x)
            self.max_y = max(self.max_y, link.max_y)

    def __init__(self) -> None:
        self.root: Optional[KdTree.Node] = None
        self._size: int = 0

    def is_empty(self) -> bool:
        return self.root is None

    @property
    def size(self) -> int:
        return self._size

    def insert(self, link: Optional[Link]) -> None:
        """
        Add the link to the group.

        At the root (and every second level thereafter), the x-coordinate is
        used as the key. The root link partitions the space using a vertical band
        the width of which is determined by the minX and maxX of the link. Let L be
        the next link to be added.

        If L.maxX<=root.minX, then L is added to the left branch of the root;
        If L.minX>=root.maxX, then L is added to the right branch of the root;
        Otherwise (i.e., L intersects the root's partition band), the root link's partition
        band is expanded to contain L, and L is added to the right branch of the root.

        Args:
            link: the link to add
        Raises:
            NullPointerException if `link` is `null`.
        """
        if link is None:
            raise ValueError("called insert() with a null Link")
        self.root = self._insert(self.root, link, True)

    def _insert(self, node: Optional[Node], link: Link, even_level: bool) -> Node:
        if node is None:
            self._size += 1
            return KdTree.Node(link)

        cmp: int = self._direction_link_to_band(link, node, even_level)

        """
        Traverse down the BST.
        
        In subsequent levels, the orientation is orthogonal
        to the current orientation.
        
        Place the link in the left or right nodes accordingly.
        
        If the comparison is affirmatively left or right, then we're considering a link
        that is either entirely to the left/bottom (may touch) or entirely to the right/top 
        (may touch) of the node's partition band.
        """

        # Handle Nodes which should be inserted to the left and bottom
        if cmp < 0:
            node.lb = self._insert(node.lb, link, not even_level)

        # Handle Nodes which should be inserted to the right and top
        elif cmp > 0:
            node.rt = self._insert(node.rt, link, not even_level)

        # The link intersects the node's partition band.
        # This is considered a tie and resolved in favor of the right subtree.
        else:
            # Expand the node's partition band and insert into right subtree
            node.extend_range(link)
            node.rt = self._insert(node.rt, link, not even_level)

        return node

    def nearest(self, p: Optional[Point2D]) -> Optional[Link]:
        if p is None:
            raise ValueError("called nearest() with a null Point2D")
        if self.is_empty():
            return None
        return self._nearest(self.root, p, self.root.link, True)

    def _nearest(
        self, node: Optional[Node], p: Point2D, champion: Link, even_level: bool
    ) -> Link:

        # Handle reaching the end of the tree
        if node is None:
            return champion

        # Determine if the current Node's link beats the existing champion
        current_dist = node.link.distance_sq(p)
        champion_dist = champion.distance_sq(p)
        new_champion = node.link if current_dist < champion_dist else champion

        """
        Calculate the distance from the search point to the current
        Node's partition band.
        
        Primarily, the sign of this calculation is useful in determining
        which side of the Node to traverse next.
        
        Additionally, the magnitude to toPartitionLine is useful for pruning.
        
        Specifically, if we find a champion whose distance is shorter than
        to a previous partition band, then we know we don't have to check any
        of the links on the other side of that partition band, because none
        can be closer.
        """
        to_partition_line = self._distance_point_to_band(p, node, even_level)

        if to_partition_line < 0:
            # Handle the search point being to the left of or below
            # the current Node's partition band.
            new_champion = self._nearest(node.lb, p, new_champion, not even_level)

            # Since champion may have changed, recalculate distance
            if new_champion.distance_sq(p) >= (to_partition_line**2):
                new_champion = self._nearest(node.rt, p, new_champion, not even_level)
        else:
            # Handle the search link being to the right of or above
            # the current Node's partition band.
            #
            # Note that, since insert() above breaks link comparison ties
            # by placing the inserted link on the right branch of the current
            # Node, traversal must also break ties by going to the right branch
            # of the current Node (i.e. to the right or top, depending on
            # the level of the current Node).
            new_champion = self._nearest(node.rt, p, new_champion, not even_level)

            # Since champion may have changed, recalculate distance
            if new_champion.distance_sq(p) >= (to_partition_line**2):
                new_champion = self._nearest(node.lb, p, new_champion, not even_level)

        return new_champion

    def _direction_link_to_band(self, link: Link, node: Node, even_level: bool) -> int:
        """
        The direction from the given link to the given Node's partition band.

        If the sign of the returned integer is -1, then the given link
        lies or should lie on the left branch of the given Node.

        Otherwise, the given link lies or should lie on the right branch of the given Node.

        Args:
            link: the link in question
            n: the Node in question
            evenLevel: is the current level even?  If so, then the Node's
            partition band is vertical, so the link will be to the left
            or right of the Node's partition band. If not, then the Node's
            partition band is horizontal, so the link will be above or
            below the Node's partition band.

        Return:
            -1 if the link is to the left of the node's partition band;\n
            1 right;\n
            0 if the link intersects the node's partition band.
        """
        if even_level:
            if link.max_x <= node.min_x:
                return -1
            elif link.min_x >= node.max_x:
                return 1
            else:
                return 0
        else:
            if link.max_y <= node.min_y:
                return -1
            elif link.min_y >= node.max_y:
                return 1
            else:
                return 0

    def _distance_point_to_band(
        self, p: Point2D, node: Node, even_level: bool
    ) -> float:
        """
        The distance and direction from the given point to the given Node's partition band.

        If the sign of the returned double is negative, then the given point
        lies or should lie on the left branch of the given Node.

        Otherwise (including where the difference is exactly 0), then the
        given point lies or should lie on the right branch of the given Node.

        Args:
            p: the point in question
            n: the Node in question
            evenLevel is the current level even?  If so, then the Node's
            partition band is vertical, so the point will be to the left
            or right of the Node's partition band. If not, then the Node's
            partition band is horizontal, so the point will be above or
            below the Node's partition band.

        Return:
            -1 if the point is to the left of the node's partition band;\n
            1 right;\n
            0 if the point is inside the node's partition band.
        """
        if even_level:
            if p.x <= node.min_x or p.x >= node.max_x:
                return p.x - node.min_x
            else:
                return 0.0
        else:
            if p.y <= node.min_y or p.y >= node.max_y:
                return p.y - node.min_y
            else:
                return 0.0
