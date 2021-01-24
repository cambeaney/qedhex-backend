#!/usr/bin/python3
import json
import haversine
import googlemaps
import math
import random

def get_route(time_to_walk, walk_speed, location):
    apikey = open('apikey', 'r').read() 
    gmaps = googlemaps.Client(key=apikey)

    search_time = time_to_walk * 3/4

    distance = search_time * walk_speed

    approximate_radius = distance / math.pi / 2



    user_1_absolute_pos = location
    reference_absolute_pos = user_1_absolute_pos

    lat_radians = math.radians(reference_absolute_pos[0])
    m_per_deg_lat = 111132.954 - 559.822 * math.cos(2 * lat_radians) + 1.175 * math.cos(4 * lat_radians)
    m_per_deg_lon = 111132.954 * math.cos(lat_radians)


    def absolute_to_relative(pos):
        # Lat-long to relative to reference
        dlat = pos[0] - reference_absolute_pos[0]
        dlong = pos[1] - reference_absolute_pos[1]

        return (dlat * m_per_deg_lat, dlong * m_per_deg_lon)

    def relative_to_absolute(pos):
        # Lat-long to relative to reference
        dlat = pos[0] / m_per_deg_lat
        dlong = pos[1] / m_per_deg_lon

        return (reference_absolute_pos[0] + dlat, reference_absolute_pos[1] + dlong)

    def get_nearby_parks(pos,radius):
        places_nearby = gmaps.places_nearby(location=pos, radius=radius, keyword='park')['results']
        places_nearby = {place['place_id']:place for place in places_nearby}

        return places_nearby

    places_nearby = get_nearby_parks(user_1_absolute_pos,approximate_radius)

    def select_best_place(places_nearby):
        mse_places = {}

        for place_id, place in places_nearby.items():
            place_lat = place['geometry']['location']['lat']
            place_lng = place['geometry']['location']['lng']

            # Find the most suitable park, closest to radius
            distance_from_user = haversine.haversine(user_1_absolute_pos, (place_lat, place_lng), unit=haversine.Unit.METERS)

            mse = (distance_from_user - approximate_radius) ** 2 * (5 - place['rating']) ** 2

            mse_places[mse] = place_id

        best_place = places_nearby[mse_places[min(mse_places.keys())]]
        return best_place

    if len(places_nearby.items()) > 0:
        best_place = select_best_place(places_nearby)
        best_place_absolute_pos = (best_place['geometry']['location']['lat'], best_place['geometry']['location']['lng'])
        best_place_pos = absolute_to_relative(best_place_absolute_pos)

        centre_absolute_pos = ((user_1_absolute_pos[0] + best_place_absolute_pos[0]) / 2, (user_1_absolute_pos[1] + best_place_absolute_pos[1]) / 2)
        centre_pos = absolute_to_relative(centre_absolute_pos)
        
        if haversine.haversine(user_1_absolute_pos, best_place_absolute_pos, unit=haversine.Unit.METERS) < 400:
            return {'success': False, 'error': 'next_to_park'}

        waypoints = []

        midpoint = centre_pos

        def rotate(origin, point, angle):
            ox, oy = origin
            px, py = point

            qx = ox + math.cos(angle) * (px - ox) - math.sin(angle) * (py - oy)
            qy = oy + math.sin(angle) * (px - ox) + math.cos(angle) * (py - oy)
            return (qx, qy)

        wp1 = rotate(midpoint, best_place_pos, math.pi/2)
        wp2 = rotate(midpoint, best_place_pos, 3*math.pi/2)

        wp1 = ((wp1[0] + midpoint[0]) / 2, (wp1[1] + midpoint[1]) / 2)
        wp2 = ((wp2[0] + midpoint[0]) / 2, (wp2[1] + midpoint[1]) / 2)


        wp1 = relative_to_absolute(wp1)
        wp2 = relative_to_absolute(wp2)

        waypoints = [wp1, best_place_absolute_pos, wp2]

        directions = gmaps.directions(origin=user_1_absolute_pos, destination=user_1_absolute_pos, mode='walking', units='metric', waypoints=waypoints)
    else:
        # Try direct route
        places_nearby = get_nearby_parks(user_1_absolute_pos,approximate_radius * 2)
        if len(places_nearby) > 0:
            best_place = select_best_place(places_nearby)
            best_place_absolute_pos = (best_place['geometry']['location']['lat'], best_place['geometry']['location']['lng'])
            waypoints = [best_place_absolute_pos]
            directions = gmaps.directions(origin=user_1_absolute_pos, destination=user_1_absolute_pos, mode='walking', units='metric', waypoints=waypoints)
            centre_absolute_pos = ((user_1_absolute_pos[0] + best_place_absolute_pos[0]) / 2, (user_1_absolute_pos[1] + best_place_absolute_pos[1]) / 2)
        else:
            # No luck
            return {'success': False, 'error': 'no_parks_within_distance'}




    route = directions[0]
    legs = route['legs']

    steps_list = []
    actual_distance = 0

    for leg in legs:
        actual_distance += leg['distance']['value']
        steps = leg['steps']
        for step in steps:
            # Slightly prune sticky out bits

            if len(legs) == 4 and leg == legs[0] and step == steps[-1] and step['end_location'] == legs[1]['steps'][0]['start_location']:
                continue

            if len(legs) == 4 and leg == legs[2] and step == steps[-1] and step['end_location'] == legs[3]['steps'][0]['start_location']:
                continue


            steps_list.append({'lat': step['end_location']['lat'], 'lng': step['end_location']['lng']})
        

    actual_time = actual_distance / walk_speed

    centre_pos = {'lat': centre_absolute_pos[0], 'lng': centre_absolute_pos[1]}

    return {'success': True, 'requested_distance': distance, 'requested_time': time_to_walk, 'actual_distance': actual_distance, 'actual_time': actual_time, 'place_of_interest': best_place, 'steps': steps_list, 'map_center': centre_pos}
