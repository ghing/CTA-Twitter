import urllib2
import xml.dom.minidom
import xml.sax.saxutils

def get_text(nodelist):
    rc = ""
    for node in nodelist:
        if node.nodeType == node.TEXT_NODE:
            rc = rc + node.data
    return rc

class Bus(object):
    def __init__(self, id, run, from_direction):
        self.id = id
        self.run = run
        self.from_direction = from_direction

class PredictedBus(Bus):
    def __init__(self, id, run, from_direction, predicted_time):
        Bus.__init__(self, id, run, from_direction)
        self.predicted_time = predicted_time

class Stop(object):
    def __init__(self, name, id, x=None, y=None):
        self.name = name
        self.id = id
        self.x = x
        self.y = y

    def __str__(self):
        s = "%s : %s" % (self.id, self.name)
        if self.x and self.y:
            s += " (%s, %s)" % (self.x, self.y)
      
        return s

class Point(object):
    def __init__(self, lat, lon):
        self.lat = lat
        self.lon = lon
        self.stop = None

    def set_stop(self, stop):
        self.stop = stop

class BustrackerException:
    """Base exception class for exceptions raised by Bustracker methods"""
    pass

class BustrackerApiConnectionError:
    """Exception class for errors raised when connecting to the API"""
    pass

class BustrackerApiXmlError:
    """Exception class for errors raised when the XML received from the API call isn't parsable as I expected."""

class Bustracker(object):
    def parse_route_points_xml(self, data):
        try:
            dom = xml.dom.minidom.parseString(data)
            points = {} 
            for pa_element in dom.getElementsByTagName('pa'):
                direction = get_text(pa_element.getElementsByTagName('d')[0].childNodes)
                points[direction] = []
                for point_element in pa_element.getElementsByTagName('pt'):
                    lat = get_text(point_element.getElementsByTagName('lat')[0].childNodes)
                    lon = get_text(point_element.getElementsByTagName('lon')[0].childNodes)
                    point = Point(lat, lon)
                    
                    bs_elements = point_element.getElementsByTagName('bs')
                    if bs_elements:
                      bs_element = bs_elements[0]
                      id = get_text(bs_element.getElementsByTagName('id')[0].childNodes)
                      name =  bs_element.getElementsByTagName('st')[0].firstChild.wholeText
                      point.set_stop(Stop(name, id)) 

                    points[direction].append(point)        

            return points
        except KeyError, e:
            raise BustrackerApiXmlError("The XML returned by the API didn't parse as expected: %s", e)

    def getRoutePoints(self, route):
        url = "http://chicago.transitapi.com/bustime/map/getRoutePoints.jsp?route=%s" % (route)

        try:
            data = urllib2.urlopen(url).read()
        except urllib2.HTTPError, e:
            raise BustrackerApiConnectionError("Http error: %d" % e.code)
        except urllib2.URLError, e:
            raise BustrackerApiConnectionError("Network error: %s" % e.reason.args[1])

        points = self.parse_route_points_xml(data)

        return points

    def getRouteDirectionStops(self, route, direction):
        """Get the stops for a given direction in the order that they are passed on the route."""
        stops = []
        points = self.getRoutePoints(route)
        for point in points[direction]:
            if point.stop:
              stops.append(point.stop)

        return stops

    def parse_route_direction_stop_xml(self, data):
        try:
            dom = xml.dom.minidom.parseString(data)
            stops = [] 
            for stop_element in dom.getElementsByTagName('stop'):
                id = stop_element.getAttribute('id')
                name = xml.sax.saxutils.unescape(stop_element.getAttribute('name'))
                x = stop_element.getAttribute('x')
                y = stop_element.getAttribute('y')
                stop = Stop(name, id, x, y)
                stops.append(stop)

            return stops
        except KeyError, e:
            raise BustrackerApiXmlError("The XML returned by the API didn't parse as expected: %s", e)


    def routeDirectionStopAsXML(self, route, direction):
        # Example Request:http://chicago.transitapi.com/bustime/eta/routeDirectionStopAsXML.jsp?route=147&direction=north%20bound
        # Example response:
        # <stop-list>
        #     <stop id="4725" name="Congress &amp; Michigan" x="1177445.262119" y="1898166.05272"/>
        #     <stop id="17255" name="Congress &amp; Wabash" x="1176787.68965" y="1898138.579471"/>
        url = "http://chicago.transitapi.com/bustime/eta/routeDirectionStopAsXML.jsp?route=%s&direction=%s" % (route, urllib2.quote(direction))

        try:
            data = urllib2.urlopen(url).read()
        except urllib2.HTTPError, e:
            raise BustrackerApiConnectionError("Http error: %d" % e.code)
        except urllib2.URLError, e:
            raise BustrackerApiConnectionError("Network error: %s" % e.reason.args[1])

        stops = self.parse_route_direction_stop_xml(data)

        return stops

    def parse_stop_predictions_xml(self, data):
        try:
            dom = xml.dom.minidom.parseString(data)
            busses = []
            for pre in dom.getElementByTagName('pre'):
                # TODO: Figure out what XML is returned when no busses are predicted
                predicted_time = pre.getElementsByTagName('pt')[0]
                from_direction = pre.getElementsByTagName('fd')[0].firstChild.wholeText
                id = pre.getElementsByTagName('v')[0]
                run = pre.getElementByTagName('rn')[0]
                bus = PredictedBus(id, run, from_direction, predicted_time)
                busses.append(bus)

            return busses
        except KeyError, e:
            raise BustrackerApiXmlError("The XML returned by the API didn't parse as expected: %s", e)
            
    def getStopPredictions(self, stop, route):
        # Example Request: http://chicago.transitapi.com/bustime/map/getStopPredictions.jsp?stop=8207&route=49
        # Notes: route can be stacked. ie: route=50-92. which would give you stop predictions for stops that have both foster and damen.
        url = "http://chicago.transitapi.com/bustime/map/getStopPredictions.jsp?stop=%s&route=%s" % (stop, route)

        try:
            data = urllib2.urlopen(url).read()
        except urllib2.HTTPError, e:
            raise BustrackerApiConnectionError("Http error: %d" % e.code)
        except urllib2.URLError, e:
            raise BustrackerApiConnectionError("Network error: %s" % e.reason.args[1])

        busses = self.parse_stop_preditions_xml(data)
        
        return busses

def main():
    bt = Bustracker()

    #stops = bt.routeDirectionStopAsXML('77', 'west bound')
    #for stop in stops:
    #    print stop['name']

    #points = bt.getRoutePoints('77')
    #for point in points['East Bound']:
    #    if point.stop:
    #      print "%s:%s" % (point.stop.id, point.stop.name)

    stops = bt.getRouteDirectionStops(2, 'North Bound')
    for stop in stops:
        print stop



if __name__ ==  "__main__":
    main()
