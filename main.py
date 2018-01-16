import os
import requests
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon
from collections import deque

def save_gdf_shapefile(gdf, filename=None, folder=None):

    for col in [c for c in gdf.columns if not c == 'geometry']:
        gdf[col] = gdf[col].fillna('').map(str)

    folder_path = '{}/{}'.format(folder, filename)

    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    gdf.to_file(folder_path, encoding='utf-8')

def overpass_request(data, timeout=180):
    url = 'https://overpass-api.de/api/interpreter'
    response = requests.post(url, data=data, timeout=timeout)

    size_kb = len(response.content) / 1000.
    print('Downloaded {:,.1f}KB from {}'.format(size_kb, url))
    response_json = None
    try:
        response_json = response.json()
    except Exception:
        assert(False)

    return response_json



def osm_city_boundary_download(city_name='深圳'):

    query_template = '''
    [out:json];
    relation["name:zh"~"{city_name}"]["boundary"="administrative"];
    rel(r)["boundary"="administrative"]["admin_level"=6];
    (._;>;);
    out;
    '''

    query_str = query_template.format(city_name=city_name)

    
    response_json = overpass_request(data={'data': query_str})

    return response_json

def create_boundary_shp(place_name):
    response_json = osm_city_boundary_download(city_name=place_name)

    vertices = {}

    for element in response_json['elements']:
        if element.get('type') == 'node':
            vertices[element['id']] = {
                'lat': element['lat'],
                'lon': element['lon']
            }

    ways = {}

    for element in response_json['elements']:
        if element.get('type') == 'way':
            nodes = element['nodes']
            ways[element['id']] = nodes
    print(len(ways.keys()))
    
    boundaries = {}

    for element in response_json['elements']:
        if element.get('type') == 'relation':
            
            nodes_list = []
            nodes = deque()
            for member in element['members']:
                if member['type'] == 'way' and member['role'] == 'outer':                    
                    assert(member['ref'] in ways)
                    sub_nodes = ways[member['ref']]
                    if len(nodes) == 0:
                        nodes.extend(sub_nodes)
                    else:
                        if nodes[0] == sub_nodes[0]:
                            nodes.extendleft(sub_nodes[1:])
                        elif nodes[0] == sub_nodes[-1]:                            
                            sub_nodes.reverse()
                            nodes.extendleft(sub_nodes[1:])
                        elif nodes[-1] == sub_nodes[0]:
                            nodes.extend(sub_nodes[1:])
                        elif nodes[-1] == sub_nodes[-1]:
                            sub_nodes.reverse()
                            nodes.extend(sub_nodes[1:])
                        else:                            
                            nodes_list.append(nodes)
                            nodes = deque()
                            nodes.extend(sub_nodes)
            
            nodes_list.append(nodes)
            try:
                
                for idx, nodes in enumerate(nodes_list):
                    polygon = Polygon([(vertices[node]['lon'], vertices[node]['lat']) for node in nodes])
                    boundary = {
                        'geometry': polygon
                    }
                    boundary.update(element['tags'])
                    boundaries[str(element['id']) + str(idx)] = boundary
                    
                
            except Exception:
                assert(False)

    gdf = gpd.GeoDataFrame(boundaries).T
    gdf.crs = {'init':'epsg:4326'}
    save_gdf_shapefile(gdf, filename=place_name, folder='.')

    

if __name__ == '__main__':
    create_boundary_shp(place_name='中山')