"""
Region.py
"""
import logging
from lxml.etree import _Element
from shapely import geometry as sg
import geojson as gs
from pyhaloxml.ellipse import ellipse2polygon
from pyhaloxml.misc import RegionType, _getvertices, _closepolygon, _getvertex


class Region:
    """
    Halo region.
    Can contian negative Regions with the same layer.
    Has a variable called region that contains the original element from the pyhaloxml.
    """

    def __init__(self, region: _Element) -> None:
        self.region = region  # type: _Element
        self.holes = []  # type: [Region]
        self.type = RegionType.Polygon  # type: RegionType
        if region.attrib["Type"] == "Rectangle":
            self.type = RegionType.Rectangle
        if region.attrib["Type"] == "Ruler":
            self.type = RegionType.Ruler
        if region.attrib["Type"] == "Ellipse":
            self.type = RegionType.Ellipse
        self.hasendcaps = region.attrib["HasEndcaps"] == "1"  # type: bool
        self.log = logging.getLogger("HaloXML:Region")  # type: logging.Logger

    def __str__(self):
        return str(self.region.attrib)

    def add_hole(self, negative_region) -> None:
        """
        Halo regions can have holes
        :param negative_region: element of type Region
        """
        self.holes.append(negative_region)

    def getvertices(self) -> list[tuple]:
        """
        Get the vertices of the region
        :return: the vertices element
        """
        vertices = [(None, None)]
        if self.type == RegionType.Polygon:
            if self.hasendcaps:
                vertices = _getvertices(self.region)
            else:
                vertices = _closepolygon(_getvertices(self.region), warn=True)
        if self.type == RegionType.Rectangle:
            pts = _getvertices(self.region)  # corners of the rectangle
            vertices = [
                pts[0],
                (pts[0][0], pts[1][1]),
                pts[1],
                (pts[1][0], pts[0][1]),
                pts[0],
            ]
        if self.type == RegionType.Ruler:
            vertices = _getvertices(self.region)
        if self.type == RegionType.Ellipse:
            pts = _getvertices(self.region)
            center = ((pts[0][0] + pts[1][0]) / 2, (pts[0][1] + pts[1][1]) / 2)
            a = (pts[0][0] - pts[1][0]) / 2
            b = (pts[0][1] - pts[1][1]) / 2
            e = ellipse2polygon(a, b)
            vertices = [(x + center[0], y + center[1]) for (x, y) in e]
        return vertices

    def getpointinregion(self) -> tuple:
        """
        Returns a point in the region or on the edge of the region
        :return:
        """
        pointinregion = (None, None)
        if self.type in [RegionType.Polygon, RegionType.Rectangle]:
            pointinregion = _getvertex(self.region)
        if self.type == RegionType.Ellipse:
            pts = _getvertices(
                self.region
            )  # corners of the rectangle, return the centerpoint
            pointinregion = ((pts[0][0] + pts[1][0]) / 2, (pts[0][1] + pts[1][1]) / 2)
        return pointinregion

    def as_geojson(self) -> gs.Polygon:
        """
        Return the region as geojson.Polygon
        :return:
        """
        vertices = [self.getvertices()]
        if self.type == RegionType.Ruler:
            polygon = gs.LineString(vertices)
        else:
            for v in self.holes:
                vertices.append(v.getvertices())
            polygon = gs.Polygon(vertices)
            if not polygon.is_valid:
                self.log.warning("HaloXML:Region 'Polygon is not valid!'")
        return polygon

    def as_shapely(self) -> sg.Polygon:
        """
        Return the region as a shapeply polygon
        :return:
        """
        if self.type == RegionType.Ruler:
            polygon = sg.LineString(self.getvertices())
        else:
            polygon = sg.Polygon(
                self.getvertices(), [x.getvertices() for x in self.holes]
            )
        return polygon