from flask import Flask, jsonify
from flask_cors import cross_origin
# from flask_restful import Resource, Api
import os
from neo4j import GraphDatabase, exceptions

app = Flask(__name__)

@app.route('/api/v1/getgraph/', methods=['GET'])
@cross_origin()
def api():
    nodes, edges, timestamp = get_node_edges()
    return jsonify({'nodes':nodes, 'edges':edges, 'timestamp':timestamp})
    
def get_node_edges():
    uri = "bolt://neo4j:7687"
    driver = GraphDatabase.driver(uri, auth=(os.environ['NEO4J_USERNAME'], os.environ['NEO4J_PASSWORD']), encrypted=False)

    with driver.session() as session:
        result = session.run("""MATCH (p:Person)
                                OPTIONAL MATCH (p:Person)-[a]->(m)
                                RETURN  p, labels(p), a, m, labels(m);""")
        rec = session.run("MATCH (a:UpdateTime)  RETURN a.updatetime").single()
        
    nodes = []
    edges = []
    physics = True

    for record in result:
        p_info = get_node_info(record['p'], record['labels(p)'][0])
        
        if p_info not in nodes:
            nodes.append(p_info)
            
        if record['m']:
            m_info = get_node_info(record['m'], record['labels(m)'][0])
            if m_info not in nodes:
                nodes.append(m_info)

            edges.append(get_edge_info(record['a'], p_info, m_info))
    
    return nodes, edges, rec['a.updatetime']


def get_node_info(node, gr):
    if 'Location' in gr:
        return {"id": node.id, 
                "group": gr,
                "label": node['title'], 
                "lon": node['lon'], 
                "lat": node['lat'], 
            }
    elif 'Person' in gr:
        return {"id": node.id,
                "group": gr, 
                "label": node.id,
                "color": node['color'],
                "type" : node['type'],
                "age" : node['age'],
                "org" : node['org'],
                "emptype" : node['emptype'],
                "gender" : node['gender'],
                "blood" : node['blood'],
                "ismedstaff" : node['ismedstaff'],
                "bloodres" : node['bloodres'],
                "province" : node['province']
            }
    else:
        raise Exceptions('Unknown Label')
    
    

def get_edge_info(edge, p_info, m_info):
    if edge.type == 'WENT_TO':
        return {"from": p_info["id"], "to": m_info["id"], "label": edge.type, "start":edge["start"], "end":edge["end"]}
    else:
        return {"from": p_info["id"], "to": m_info["id"], "label": edge.type}


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0',port=5000)
