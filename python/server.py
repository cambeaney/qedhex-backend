#!/usr/bin/python3
from apiserve import ApiServer, ApiRoute
from get_route import *

class MyServer(ApiServer):
        @ApiRoute("/get_route")
        def get_route_req(req):
            if not 'time_to_walk' in req or not 'walk_speed' in req or not 'location' in req:
                return {'success': False, 'error': 'Bad request'}
            else:
                return get_route(req['time_to_walk'], req['walk_speed'], req['location'])
        @ApiRoute("/calendar")
        def calendar_req(req):
            pass

MyServer("0.0.0.0",80).serve_forever()
