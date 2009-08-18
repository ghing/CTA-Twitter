import urllib2

class Bustracker(object):
    def routeDirectionStopAsXML(self, route, direction):
        # Example Request:http://chicago.transitapi.com/bustime/eta/routeDirectionStopAsXML.jsp?route=147&direction=north%20bound
        # Example response:
        # <stop-list>
        #     <stop id="4725" name="Congress &amp; Michigan" x="1177445.262119" y="1898166.05272"/>
        #     <stop id="17255" name="Congress &amp; Wabash" x="1176787.68965" y="1898138.579471"/>
        # TODO: Need to escape direction
        url = "http://chicago.transitapi.com/bustime/eta/routeDirectionStopAsXML.jsp?route=%s&direction=%s" % (route, direction)

        try:
	          data = urllib2.urlopen(url).read()
        except urllib2.HTTPError, e:
	          print "HTTP error: %d" % e.code
        except urllib2.URLError, e:
	          print "Network error: %s" % e.reason.args[1]

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
