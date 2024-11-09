import math

# Calculate the next coordinate from a reference point based on bearing and distance
def get_next_coordinate(reference_point, line):

    if line['ns'] == 'DN': #Due North
        x = 0
        y = float(line['dist'])
    elif line['ns'] == 'DS': #Due South
        x = 0
        y = -float(line['dist'])
    elif line['ns'] == 'DE': #Due East
        x = float(line['dist'])
        y = 0
    elif line['ns'] == 'DW': #Due West
        x = -float(line['dist'])
        y = 0
    else:
        angle = math.radians(int(line['deg']) + float(line['min']) / 60)
        if line['ns'] == 'S' and line['ew'] == 'W':
            x = -float(line['dist']) * math.sin(angle)
            y = -float(line['dist']) * math.cos(angle)
        elif line['ns'] == 'N' and line['ew'] == 'W':
            x = -float(line['dist']) * math.sin(angle)
            y = float(line['dist']) * math.cos(angle)
        elif line['ns'] == 'N' and line['ew'] == 'E':
            x = float(line['dist']) * math.sin(angle)
            y = float(line['dist']) * math.cos(angle)
        elif line['ns'] == 'S' and line['ew'] == 'E':
            x = float(line['dist']) * math.sin(angle)
            y = -float(line['dist']) * math.cos(angle)

    return (reference_point[0] + x, reference_point[1] + y)

# Convert Degrees Minutes Seconds (DMS) to Decimal Degrees (DD)
def convert_dms_to_dd(dms):
    return round(dms['deg'] + (dms['min'] / 60) + (dms['sec'] / 3600), 7)

# Convert Decimal Degrees (DD) to Degrees Minutes Seconds (DMS)
def convert_dd_to_dms(dd):
    deg = int(dd)
    min = int((dd - deg) * 60)
    sec = round(((dd - deg) * 60 - min) * 60, 4)
    return {'deg': deg, 'min': min, 'sec': sec}

# Get latitude and longitude of a new point given the reference point and easting/northing
def get_lat_long(reference_longitude_x, reference_latitude_y, reference_point, k_longitude_x, k_latitude_y, point):
    longitude_x = round(convert_dms_to_dd(reference_longitude_x) + (point[0] - reference_point[0]) / (3600 * k_longitude_x), 7)
    latitude_y = round(convert_dms_to_dd(reference_latitude_y) + (point[1] - reference_point[1]) / (3600 * k_latitude_y), 7)
    return (longitude_x, latitude_y)

# Main function to compute all the points
def calculate_boundary(tiepoint, technical_descriptions):
    # Initialize the points
    points = []
    reference_point = (tiepoint['easting'], tiepoint['northing'])
    
    # Start at tiepoint
    point = reference_point

    # Calculate Cartesian points
    for line in technical_descriptions:
        point = get_next_coordinate(point, line)
        points.append(point)

    # Convert to geographic coordinates (dd)
    geo_coord_dd = []
    for point in points:
        longitude_x, latitude_y = get_lat_long(tiepoint['longitude'], tiepoint['latitude'], reference_point, tiepoint['k_longitude'], tiepoint['k_latitude'], point)
        geo_coord_dd.append((longitude_x, latitude_y))

    # Reverse
    map_coord_dd = [(coord[1], coord[0]) for coord in geo_coord_dd]

    # Return the points and geographic coordinates in DD and map compatible coordinate formats
    return points, geo_coord_dd, map_coord_dd