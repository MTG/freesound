var BASE_NODE_SIZE = 5,
    BASE_NODE_SIZE_ONHOVER = 8,
    RATIO_NODE_SIZE_CENTRALITY = 5,
    ON_OVER_NODE_SIZE = 12;
FORCE_CHARGE = -100;
FORCE_LINK_DISTANCE = 20;

var width = window.innerWidth - 30,
    height = window.innerHeight - 30;

var width = 944,
    height = 600;

var fill = d3.scale.category20();

// https://github.com/wbkd/d3-extended
d3.selection.prototype.moveToFront = function () {
    return this.each(function () {
        this.parentNode.appendChild(this);
    });
};


function activateGraph (graph) {
    // // request clustered graph
    // $.get("{% url 'clustered-graph-json' %}"+"?{{url_query_params_string | safe}}", {
    // }).then(res => JSON.parse(res)).then(graph => {
    var force = d3.layout.force()
        .charge(FORCE_CHARGE)
        .linkDistance(FORCE_LINK_DISTANCE)
        .linkStrength(function (d) {
            if (d.weight) {
                return 3 * d.weight;
            } else {
                return 1;
            }
        })
        .size([width, height])
        .gravity(0.4)
        .alpha(0.8)
        .theta(0.8)
        .friction(0.9);
    
    var zoom = d3.behavior.zoom()
        .scaleExtent([0.3, 2])
        .on("zoom", zoomed);
    
    var svg = d3.select("#chart").append("svg")
        .attr("viewBox", "0 0 " + width + " " + height)
        .attr("preserveAspectRatio", "xMinYMid")
        .append("g")
        .call(zoom)
        .append("g");
    
    //big black box surrounding everything that we can zoom on 
    var rect = svg.append("g")
        .attr("class", "rect")
        .append("rect")
        .style("fill", "white")
        .style("opacity", 0)
        .attr("width", width)
        .attr("height", height)
        .style("pointer-events", "all")
    
    var vis = svg.append("g")
        .attr("width", width)
        .attr("height", height)
        .append("g")
    
    function size_node(c) {
        return c * RATIO_NODE_SIZE_CENTRALITY + BASE_NODE_SIZE;
    }
    
    function size_node_on_hover(c) {
        return c * RATIO_NODE_SIZE_CENTRALITY + BASE_NODE_SIZE_ONHOVER;
    }
    
    // Zoom        
    function zoomed() {
        vis.attr("transform", "translate(" + d3.event.translate + ")scale(" + d3.event.scale + ")");
    }
    
    // Web Audio API
    var context = initializeNewWebAudioContext();
    var playingSound; // keep track of playing sound to stop it

    var graph = JSON.parse(graph);
    console.log(graph)
    // var init_graph = JSON.parse(JSON.stringify(graph));

    var nodeById = d3.map();

    graph.nodes.forEach(function (node) {
        nodeById.set(node.id, node);
    });

    graph.links.forEach(function (link) {
        link.source = nodeById.get(link.source);
        link.target = nodeById.get(link.target);
    });

    // Force layout
    force
        .nodes(graph.nodes)
        .links(graph.links)
        .start();

    var link = vis.selectAll(".link")
        .data(graph.links)
        .enter().append("line")
        .attr("class", "link")
        .style("stroke-width", function (d) {
            return d.weight;
        });

    var node = vis.selectAll(".node")
        .data(graph.nodes)
        .enter().append("circle")
        .attr("class", "node")
        .attr("r", function (d) {
            return size_node(d.group_centrality);
        })
        .style("fill", function (d) {
            return fill(d.group);
        })
        .on('click', connectedNodes);
    // .call(force.drag);

    svg.selectAll(".node")
        .on("mouseenter", function (d) {
            // load and play sound
            context.loadSound(d.url, '0');
            playingSound = context.playSound('0');

            // make node bigger
            d3.select(this)
                .transition()
                .attr("r", function (d) {
                    return size_node_on_hover(d.group_centrality);
                })

            d3.select(this).moveToFront();
        })
        .on("mouseleave", function () {
            // stop playing sound
            if (playingSound) {
                playingSound.pause();
            }

            // make node smaller
            d3.select(this)
                .transition()
                .attr("r", function (d) {
                    return size_node(d.group_centrality);
                })
        });

    force.on("tick", function () {
            link.attr("x1", function (d) {
                    return d.source.x;
                })
                .attr("y1", function (d) {
                    return d.source.y;
                })
                .attr("x2", function (d) {
                    return d.target.x;
                })
                .attr("y2", function (d) {
                    return d.target.y;
                });

            node.attr("cx", function (d) {
                    return d.x;
                })
                .attr("cy", function (d) {
                    return d.y;
                });
            node.each(collide(0.3));
        })
        // .on('end', function () {
        //     (function (console) {
        //         console.save = function (data, filename) {

        //             if (!data) {
        //                 console.error('Console.save: No data')
        //                 return;
        //             }

        //             if (!filename) filename = 'console.json'

        //             if (typeof data === "object") {
        //                 data = JSON.stringify(data, undefined, 4)
        //             }

        //             var blob = new Blob([data], {
        //                     type: 'text/json'
        //                 }),
        //                 e = document.createEvent('MouseEvents'),
        //                 a = document.createElement('a')

        //             a.download = filename
        //             a.href = window.URL.createObjectURL(blob)
        //             a.dataset.downloadurl = ['text/json', a.download, a.href].join(':')
        //             e.initMouseEvent('click', true, false, window, 0, 0, 0, 0, 0, false,
        //                 false, false, false, 0, null)
        //             a.dispatchEvent(e)
        //         }
        //     })(console)
            
        //     init_graph.nodes = graph.nodes;
        //     console.save(init_graph, 'graph.json')
        // });

    // Hilight nodes on click
    //Toggle stores whether the highlighting is on
    var toggle = 0;
    //Create an array logging what is connected to what
    var linkedByIndex = {};
    for (i = 0; i < graph.nodes.length; i++) {
        linkedByIndex[i + "," + i] = 1;
    };
    graph.links.forEach(function (d) {
        linkedByIndex[d.source.index + "," + d.target.index] = 1;
    });
    //This function looks up whether a pair are neighbours
    function neighboring(a, b) {
        return linkedByIndex[a.index + "," + b.index];
    }

    function connectedNodes() {
        if (toggle == 0) {
            //Reduce the opacity of all but the neighbouring nodes
            d = d3.select(this).node().__data__;
            link.style("opacity", function (o) {
                return d.index == o.source.index | d.index == o.target.index ? 1 : 0.05;
            });
            node.style("opacity", function (o) {
                return neighboring(d, o) | neighboring(o, d) ? 1 : 0.15;
            });

            // show sound info
            d3.select("#h1").html(d.name + '   centrality: ' + d.group_centrality);
            d3.select("#h2").html(d.tags);
            d3.select("#h3").html('<a href="' + d.sound_page_url + '">' + d.sound_page_url + '</a>');

            toggle = 1;
        } else {
            //Put them back to opacity=1
            node.style("opacity", 1);
            link.style("opacity", 0.1);
            toggle = 0;

            // remove sound info
            d3.select("#h1").html('Sound file name');
            d3.select("#h2").html('Click on a node to display info');
            d3.select("#h3").html('');
        }
    }

    // Collide for forbiding overlap of nodes
    var padding = 1;

    function collide(alpha) {
        var quadtree = d3.geom.quadtree(graph.nodes);
        return function (d) {
            var rb = 2 * size_node(d.group_centrality),
                nx1 = d.x - rb,
                nx2 = d.x + rb,
                ny1 = d.y - rb,
                ny2 = d.y + rb;
            quadtree.visit(function (quad, x1, y1, x2, y2) {
                if (quad.point && (quad.point !== d)) {
                    var x = d.x - quad.point.x,
                        y = d.y - quad.point.y,
                        l = Math.sqrt(x * x + y * y);
                    if (l < rb) {
                        l = (l - rb) / l * alpha;
                        d.x -= x *= l;
                        d.y -= y *= l;
                        quad.point.x += x;
                        quad.point.y += y;
                    }
                }
                return x1 > nx2 || x2 < nx1 || y1 > ny2 || y2 < ny1;
            });
        };
    }
// });

}


