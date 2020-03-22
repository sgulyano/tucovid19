from IPython.display import IFrame
import json
import uuid

def vis_network(nodes, edges, physics=False):
    html = """
    <html>
    <head>
      <script type="text/javascript" src="https://cdnjs.cloudflare.com/ajax/libs/vis/4.20.0/vis.min.js"></script>
      <link href="https://cdnjs.cloudflare.com/ajax/libs/vis/4.20.0/vis.css" rel="stylesheet" type="text/css">
    </head>
    <body>

    <div id="{id}"></div>

    <script type="text/javascript">
      var network;
      var allNodes;
      var highlightActive = false;


      var options = {{}};
      var nodesDataset = new vis.DataSet(options);
      var edgesDataset = new vis.DataSet(options);

      nodesDataset.add({nodes});
      edgesDataset.add({edges});

      var data = {{nodes:nodesDataset, edges:edgesDataset}} 

      var container = document.getElementById("{id}");

      var options = {{
          nodes: {{
              shape: 'dot',
              size: 25,
              font: {{
                  size: 14
              }}
          }},
          edges: {{
              font: {{
                  size: 14,
                  align: 'middle'
              }},
              color: 'gray',
              arrows: {{
                  to: {{enabled: true, scaleFactor: 0.5}}
              }},
              smooth: {{enabled: false}}
          }},
          groups: {{
              PUIPerson: {{
                  shape: 'box',
                  font: {{
                      size: 16,
                      color: '#ffffff'
                  }},
                  margin: 7,
                  color: {{
                      background: '#7c26ff',
                      highlight: '#6600ff'
                  }}
              }},
              HighRiskPerson: {{
                  shape: 'ellipse',
                  font: {{
                      size: 14,
                  }},
                  color: {{
                      background: '#ff5050',
                      highlight: '#ff3535'
                  }}
              }},
              LowRiskPerson: {{
                  shape: 'ellipse',
                  font: {{
                      size: 12,
                  }},
                  color: {{
                      background: 'orange',
                      highlight: '#ff8811'
                  }}
              }},
              HealthyPerson: {{
                  shape: 'ellipse',
                  font: {{
                      size: 12,
                  }},
                  color: {{
                      background: '#99ff99',
                      highlight: '#72ff72'
                  }}
              }},
              Location: {{
                  shape: 'circle',
                  font: {{
                      size: 12,
                  }},
                  color: {{
                      background: '#66ccff',
                      highlight: '#3fbdfc'
                  }}
              }}
          }},
          physics: {{
              enabled: {physics}
          }}
      }};

      var network = new vis.Network(container, data, options);

      function neighbourhoodHighlight(params) {{
          // if something is selected:
          if (params.nodes.length > 0) {{
              highlightActive = true;
              var i, j;
              var selectedNode = params.nodes[0];
              var degrees = 2;

              // mark all nodes as hard to read.
              for (var nodeId in allNodes) {{
                  allNodes[nodeId].color = 'rgba(200,200,200,0.5)';
                  if (allNodes[nodeId].hiddenLabel === undefined) {{
                      allNodes[nodeId].hiddenLabel = allNodes[nodeId].label;
                      allNodes[nodeId].label = undefined;
                  }}
              }}
              var connectedNodes = network.getConnectedNodes(selectedNode);
              var allConnectedNodes = [];

              // get the second degree nodes
              for (i = 1; i < degrees; i++) {{
                  for (j = 0; j < connectedNodes.length; j++) {{
                      allConnectedNodes = allConnectedNodes.concat(network.getConnectedNodes(connectedNodes[j]));
                  }}
              }}

              // all second degree nodes get a different color and their label back
              for (i = 0; i < allConnectedNodes.length; i++) {{
                  allNodes[allConnectedNodes[i]].color = undefined;
                  if (allNodes[allConnectedNodes[i]].hiddenLabel !== undefined) {{
                      allNodes[allConnectedNodes[i]].label = allNodes[allConnectedNodes[i]].hiddenLabel;
                      allNodes[allConnectedNodes[i]].hiddenLabel = undefined;
                  }}
              }}

              // all first degree nodes get their own color and their label back
              for (i = 0; i < connectedNodes.length; i++) {{
                  allNodes[connectedNodes[i]].color = undefined;
                  if (allNodes[connectedNodes[i]].hiddenLabel !== undefined) {{
                      allNodes[connectedNodes[i]].label = allNodes[connectedNodes[i]].hiddenLabel;
                      allNodes[connectedNodes[i]].hiddenLabel = undefined;
                  }}
              }}

              // the main node gets its own color and its label back.
              allNodes[selectedNode].color = undefined;
              if (allNodes[selectedNode].hiddenLabel !== undefined) {{
                  allNodes[selectedNode].label = allNodes[selectedNode].hiddenLabel;
                  allNodes[selectedNode].hiddenLabel = undefined;
              }}
          }}
          else if (highlightActive === true) {{
              // reset all nodes
              for (var nodeId in allNodes) {{
                  allNodes[nodeId].color = undefined;
                  if (allNodes[nodeId].hiddenLabel !== undefined) {{
                      allNodes[nodeId].label = allNodes[nodeId].hiddenLabel;
                      allNodes[nodeId].hiddenLabel = undefined;
                  }}
              }}
              highlightActive = false
          }}

          // transform the object into an array
          var updateArray = [];
          for (nodeId in allNodes) {{
              if (allNodes.hasOwnProperty(nodeId)) {{
                  updateArray.push(allNodes[nodeId]);
              }}
          }}
          nodesDataset.update(updateArray);
      }}



      // get a JSON object
      allNodes = nodesDataset.get({{returnType:"Object"}});

      network.on("click",neighbourhoodHighlight);

    </script>
    </body>
    </html>
    """

    unique_id = str(uuid.uuid4())
    html = html.format(id=unique_id, nodes=json.dumps(nodes), edges=json.dumps(edges), physics=json.dumps(physics))

    filename = "figure/graph-{}.html".format(unique_id)

    file = open(filename, "w")
    file.write(html)
    file.close()

    return IFrame(filename, width="100%", height="800")

def draw(graph, options, physics=False, limit=100):
    # The options argument should be a dictionary of node labels and property keys; it determines which property
    # is displayed for the node label. For example, in the movie graph, options = {"Movie": "title", "Person": "name"}.
    # Omitting a node label from the options dict will leave the node unlabeled in the visualization.
    # Setting physics = True makes the nodes bounce around when you touch them!
    query = """
    MATCH (n)
    WITH n, rand() AS random
    ORDER BY random
    LIMIT {limit}
    OPTIONAL MATCH (n)-[r]->(m)
    RETURN n AS source_node,
           id(n) AS source_id,
           r,
           m AS target_node,
           id(m) AS target_id
    """

    data = graph.run(query, limit=limit)

    nodes = []
    edges = []

    def get_vis_info(node, id):
        node_label = list(node.labels())[0]
        prop_key = options.get(node_label)
        vis_label = node.properties.get(prop_key, "")

        return {"id": id, "label": vis_label, "group": node_label, "title": repr(node.properties)}

    for row in data:
        source_node = row[0]
        source_id = row[1]
        rel = row[2]
        target_node = row[3]
        target_id = row[4]

        source_info = get_vis_info(source_node, source_id)

        if source_info not in nodes:
            nodes.append(source_info)

        if rel is not None:
            target_info = get_vis_info(target_node, target_id)

            if target_info not in nodes:
                nodes.append(target_info)

            edges.append({"from": source_info["id"], "to": target_info["id"], "label": rel.type()})

    return vis_network(nodes, edges, physics=physics)
