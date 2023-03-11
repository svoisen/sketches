import vsketch
import numpy as np
import shapely 
from functools import reduce

"""
Circle packing
"""

# A tile is a rectangular object containing references to any shapes that
# intersect its bounds
class Tile:
    bounds: shapely.Polygon
    shapes: list[vsketch.Shape]

    def __init__(self, x, y, width, height) -> None:
        self.bounds = shapely.box(x, y, x + width, y + height)
        self.shapes = []

# Create a list of tiles that can be used to reduce overhead for hit-testing
def create_tiles(vsk: vsketch.Vsketch, num_rows, num_cols) -> list[Tile]:
    tiles = []
    tile_width = vsk.width / num_cols
    tile_height = vsk.height / num_rows

    for x in np.linspace(0, vsk.width, num_cols, endpoint=False):
        for y in np.linspace(0, vsk.height, num_rows, endpoint=False):
            tiles.append(Tile(x, y, tile_width, tile_height))
    
    return tiles


class Sketch001(vsketch.SketchClass):
    min_radius = vsketch.Param(5, unit="mm")
    max_radius = vsketch.Param(50, unit="mm")
    margin = vsketch.Param(10, unit="mm")
    padding = vsketch.Param(1, unit="mm")
    tile_rows = vsketch.Param(8)
    tile_cols = vsketch.Param(8)
    attempts = vsketch.Param(1000)

    tiles: list[Tile] = []
    shapes: list[shapely.Polygon] = []
    

    def draw(self, vsk: vsketch.Vsketch) -> None:
        vsk.size("a4", landscape=False, center=False)
        self.tiles = create_tiles(vsk, self.tile_rows, self.tile_cols)
        self.shapes = []

        min_x = self.margin + self.min_radius
        max_x = vsk.width - self.min_radius - self.margin
        min_y = self.margin + self.min_radius
        max_y = vsk.height - self.min_radius - self.margin

        # Attempt to add "attempts" number of shapes
        for _ in range(self.attempts):
            self.grow_circle(vsk, vsk.random(min_x, max_x), vsk.random(min_y, max_y), self.min_radius)

        # Draw the shapes
        for s in self.shapes:
            vsk.geometry(s)


    # Grow the circle starting with the minimum radius until we hit an edge or
    # another circle (plus any padding)
    def grow_circle(self, vsk, x, y, radius) -> None:
        # Check if the circle has hit the edge of the sketch
        if radius > self.min_radius and (
                x + radius >= vsk.width - self.margin or 
                x - radius <= self.margin or 
                y + radius >= vsk.height - self.margin or 
                y - radius <= self.margin):
            self.add_circle(x, y, radius)
            return

        circle = shapely.Point(x, y).buffer(radius + self.padding)
        candidates = list(map(lambda t: t.shapes, self.get_intersecting_tiles(circle)))

        if len(candidates) > 0:
            for c in reduce(lambda s1, s2: s1 + s2, candidates):
                if circle.intersects(c):
                    if radius > self.min_radius:
                        self.add_circle(x, y, radius) 
                    return

        if radius >= self.max_radius:
            self.add_circle(x, y, radius)
        else:
            self.grow_circle(vsk, x, y, radius + 1)


    def get_intersecting_tiles(self, circle) -> list[Tile]:
        return list(filter(
            lambda tile: tile.bounds.intersects(circle) or 
                tile.bounds.contains(circle), self.tiles))


    def add_circle(self, x, y, radius) -> None:
        circle = shapely.Point(x, y).buffer(radius)
        intersecting_tiles = self.get_intersecting_tiles(circle)

        for tile in intersecting_tiles:
            tile.shapes.append(circle)

        self.shapes.append(circle)

    def finalize(self, vsk: vsketch.Vsketch) -> None:
        vsk.vpype("linemerge linesimplify reloop linesort")


if __name__ == "__main__":
    Sketch001.display()
