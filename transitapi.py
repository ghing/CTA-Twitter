import urllib2
import xml.dom.minidom
import xml.sax.saxutils

def get_text(nodelist):
    rc = ""
    for node in nodelist:
        if node.nodeType == node.TEXT_NODE:
            rc = rc + node.data
    return rc

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

# Base exception class for exceptions raised by Bustracker methods
class BustrackerException:
    pass

# TODO: Lazily catch and log XML (KeyError) and urllib exceptions so I can find bugs

class Bustracker(object):
    def parse_route_points_xml(self, data):
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

    def getRoutePoints(self, route):
        url = "http://chicago.transitapi.com/bustime/map/getRoutePoints.jsp?route=%s" % (route)

        try:
            data = urllib2.urlopen(url).read()
        except urllib2.HTTPError, e:
            print "HTTP error: %d" % e.code
        except urllib2.URLError, e:
            print "Network error: %s" % e.reason.args[1]

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
	    print "HTTP error: %d" % e.code
        except urllib2.URLError, e:
	    print "Network error: %s" % e.reason.args[1]

        stops = self.parse_route_direction_stop_xml(data)

        return stops

    def parse_stop_predictions_xml(self, data):
        pass
            
    def getStopPredictions(self, stop, route):
        # Example Request: http://chicago.transitapi.com/bustime/map/getStopPredictions.jsp?stop=8207&route=49
        # Notes: route can be stacked. ie: route=50-92. which would give you stop predictions for stops that have both foster and damen.
        # Example Response: 
        # <stop>
        #     <id>8207</id>
        #     <nm>Western & Fullerton</nm>
        #     <sri>
        #         <rt>49</rt>
        #         <d>South Bound</d>
        #     </sri>
        #     <sbs>
        #
			  #     </sbs>
        #     <cr>49</cr>
        #     <pre>
        #         <pt>DELAYED</pt>
        #         <fd>79th</fd>
        #         <v>6562</v>
        #         <rn>49</rn>
        #     </pre>
        # </stop>
        pass

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
