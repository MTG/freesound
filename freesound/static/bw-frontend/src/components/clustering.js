
import ForceGraph from "force-graph";
import * as d3 from "d3";
import jquery from 'jquery';
var $=jquery.noConflict();


/*
  SEARCH RESULTS CLUSTERING
*/

// We get the urls inserted as an attribute of a DOM element when rendering the html templates
var clustering_urls_div = document.querySelector("#cluster-urls-div");
var url_request_clustering = clustering_urls_div.getAttribute("url-clustering");
var url_request_graph = clustering_urls_div.getAttribute("url-graph");

// Ajax request clustering
request_clustering();
var graph = undefined;
var graphLoaded = false;
var showCluster = undefined;

$('#show-clustering-graph-button').click(function () {
    showGraph();
});

// toggle and show graph
function updateShowGraphButton() {
    var buttonText = $("#clustering-graph").is(":visible")? "hide" : "show";
    $("#show-clustering-graph-button").html(buttonText);
}

function showGraph() {
    $("#clustering-graph-modal").show();
    if (graph !== undefined && graphLoaded === false) {
        activateGraph(graph);
        graphLoaded = true;
    }
}

function closeGraphModal() {
    $("#clustering-graph-modal").hide();
}

// play cluster examples on mouseover & click
var mouse_on_cluster_facet_preview = false;
function enableAudioClusterExamples() {
  function playAudio(el, index) {
    var dummySpanClusterExamples = el.parent().children('.dummy-span-cluster-examples');
    var cluster_idx = $('.clustering-facet').index($(el).parents('.clustering-facet'));
    var index = (typeof index == 'number') ? index: parseInt(Math.random()*dummySpanClusterExamples.length);
    var selectedExample = dummySpanClusterExamples.eq(index);
    var soundId = selectedExample.attr("sound-id");
    var soundUrl = selectedExample.attr("sound-url");
    play_sound_from_url(soundId, soundUrl, function () {
      index = (index + 1) % dummySpanClusterExamples.length;
      // this condition ensures that we don't trigger more plays when not previewing the right cluster.
      // otherwise it could happen that stopAllAudio() would not stop the recursive loop.
      if (mouse_on_cluster_facet_preview == cluster_idx) {
        playAudio(el, index)
      }
    });
  };

  function stopAllAudio() {
    $('audio').each(function (i, el) {el.pause();});
  };

  $(".cluster-audio-examples")
    .mouseenter(function() {
      var cluster_idx = $('.clustering-facet').index($(this).parents('.clustering-facet'));
      mouse_on_cluster_facet_preview = cluster_idx;
      stopSound();
      playAudio($(this).parent().parent(), false);
    })
    .mouseleave(function() {
      mouse_on_cluster_facet_preview = false;
      stopSound();
    })
    .click(function() {
      stopSound();
      playAudio($(this).parent().parent(), false);
    });
}

var clustering_trial_number = 0;
// function for requesting clustering
function request_clustering()
{
    $.get(url_request_clustering, 
            {}, 
            function( data ) {
                clustering_trial_number += 1;
                if (data.status === 'pending') {
                    if (clustering_trial_number < 1000) {
                        setTimeout(() => {
                            request_clustering();
                        }, 500);
                    } else {
                        $('#facet-loader').hide();
                        $('#cluster-fail-icon').show();
                    }
                } else if (data.status === 'failed') {
                    // clustering failed
                    $('#facet-loader').hide();
                    $('#cluster-fail-icon').show();
                } else {
                    $('#facet-loader').hide();
                    $('#show-clustering-graph-button').show();
                    $('#cluster-labels').html(data);
                    $('#clusters-div').replaceWith(data);
                    // add cluster colors
                    var num_clusters = Math.max(
                        ...Array.from($('.clustering-facet').map(
                            (e, l)=>parseInt($(l).attr('cluster-id')))
                        )
                    ) + 1;
                    $('#cluster-labels').find('.clustering-facet').each((i, l) => {
                        $(l).find('a').css("color", cluster2color($(l).attr('cluster-id'), num_clusters));
                        $(l).find('a').css('font-weight', 'bold');
                    });
                    enableAudioClusterExamples();

                    $('.cluster-link-button').click(function () {
                        $("#clustering-graph-modal").show();
                        var clusterId = $(this).attr('cluster-id');
                        showCluster = clusterId;
                        if (graph !== undefined && graphLoaded === false) {
                            activateGraph(graph, clusterId);
                            graphLoaded = true;
                        }
                    });

                    $('#close-modal-button').click(function () {
                        closeGraphModal();
                    })

                    // request clustered graph
                    // set graph as a global variable
                    $.get(url_request_graph, {
                        }).then(res => JSON.parse(res)).then(data => {
                            graph = data;
                            if ($("#clustering-graph-modal").is(":visible")) {
                                if (showCluster !== undefined) {
                                    activateGraph(graph, showCluster);
                                    graphLoaded = true;
                                } else {
                                    activateGraph(graph);
                                    graphLoaded = true;
                                }
                            }
                        });
                }
    });
}


/*
  AUDIO PLAYER
*/

// Audio using HTLM audio players for compatibility with any browser
// Could perhaps be replace with a web audio api based player
var audioPlayers = {};

function play_sound_from_url(sound_id, url, onEnd) {
  if (audioPlayers[sound_id] === undefined) {
      var player = new Audio()
      player.src = url;
      player.autoplay = true;
      audioPlayers[sound_id] = player;
  } else {
      audioPlayers[sound_id].play();
  }

  // used for sequentially playing cluster examples
  if (onEnd !== undefined) {
      audioPlayers[sound_id].onended = function() {
          onEnd();
      }
  }
}

function stopSound() {
  Object.keys(audioPlayers).forEach(function(key) {
      var player = audioPlayers[key]
      player.pause();
      player.currentTime = 0;
  });
}


/*
  GRAPH VISUALISATION
*/

var COLOR_GROUP = [
  '#D2B48C',
  '#BC8F8F',
  '#F4A460',
  '#DAA520',
  '#B8860B',
  '#CD853F',
  '#D2691E',
  '#808000',
  '#8B4513',
  '#A0522D',
  '#A52A2A',
  '#800000',
  '#FFF8DC'
];

function cluster2color (group_id, num_clusters) {
  return COLOR_GROUP[parseInt(group_id*COLOR_GROUP.length/num_clusters)%COLOR_GROUP.length]
}

function activateGraph (graph, clusterId=undefined) {
  var data = graph;
  // var data = JSON.parse(graph);

  var num_clusters = Math.max(...data.nodes.map(node => node.group))+1;

  const NODE_R = 15;

  var elem = document.getElementById('graph');

  function playSound(d) {
      try {
          play_sound_from_url(d.id, d.url);
      } catch (error) {
          console.log(error);
      }
  }

  function onNodeHover(node) {
      if (node) {
          elem.style.cursor = 'pointer';
          playSound(node);
          $("#cluster-labels .clustering-facet").removeClass("label-over");
          $("#cluster-labels .clustering-facet[cluster-id="+ node.group +"]").addClass("label-over");
      } else {
          $("#cluster-labels .clustering-facet").removeClass("label-over");
          elem.style.cursor = null;
          stopSound();
      }
      hoverNode = node || null;
  }

  var nodeById = new Map();
  var nodeByGroup = new Map();
  data.nodes.forEach(function (node) {
      nodeById.set(node.id, node);

      var nodesInGroup = nodeByGroup.get(node.group);
      if (nodesInGroup === undefined) {
          nodeByGroup.set(node.group, [node]);
      } else {
          nodeByGroup.set(node.group, [...nodesInGroup, node]);
      }
  });

  function imageLabel(node) {
      var html_label = '<div class="graph-node-card">'
      html_label += '<div class="graph-node-card-header">' + node.name + '</div>'
      html_label += '<div class="graph-node-card-content">' + node.tags + '</div>'
      html_label += '<div class="graph-node-card-image"><span class="clustering-loader"></span><img src="' + node.image_url + '"></img></div>'
      html_label += '</div>'
      getSoundDisplay(node);
      return html_label
  }

  async function getSoundDisplay(node) {
    // const url = "/embed/sound/iframe/"+ node.id +"/simple/medium/";
    const url = node.sound_display_url;
    $.get(url, {}).then(data => {
      $(".graph-node-card").html(data);
    });
  }

  // cross-link node objects
  data.links.forEach(link => {
      const a = nodeById.get(link.source);
      const b = nodeById.get(link.target);
      !a.neighbors && (a.neighbors = []);
      !b.neighbors && (b.neighbors = []);
      a.neighbors.push(b);
      b.neighbors.push(a);
  
      !a.links && (a.links = []);
      !b.links && (b.links = []);
      a.links.push(link);
      b.links.push(link);
  });

  const highlightNodes = new Set();
  const highlightLinks = new Set();
  let hoverNode = null;

  function onNodeClick(node) {
      if (cntrlIsPressed) {
          addSoundToBookmark(node);
      } else {
          highlightNodes.clear();
          highlightLinks.clear();
          if (node) {
              highlightNodes.add(node);
              node.neighbors.forEach(neighbor => highlightNodes.add(neighbor));
              node.links.forEach(link => highlightLinks.add(link));
          }
          hoverNode = node || null;
          elem.style.cursor = node ? '-webkit-grab' : null;
      }
  }

  // remeber if ctrl key is pressed
  var cntrlIsPressed = false;
  var bookmarkedSounds = [];

  $(document).keydown(function(event) {
      if (event.which == "17")
          cntrlIsPressed = true;
  });
  
  $(document).keyup(function(event) {
      if (event.which == "17")
          cntrlIsPressed = false;
  });

  function addSoundToBookmark(node) {
      if (!bookmarkedSounds.includes(node.id)) {
          var link_id = "bookmark-s-" + node.id;
          $("#h2").append('<div id="bookmark-s-' + node.id +'"><a target="_blank" href="' 
              + node.sound_page_url + '">' + node.name 
              + '</a><span class="close-bookmark"> ×</span><div>');
          bookmarkedSounds.push(node.id);
          $('#'+link_id).children('.close-bookmark').click(() => {deleteBookmark(node.id)})
      }
  }

  function deleteBookmark(sound_id) {
      $('#bookmark-s-'+sound_id).remove();
      for (var i = bookmarkedSounds.length - 1; i >= 0; i--) {
          if (bookmarkedSounds[i] === sound_id) {
              bookmarkedSounds.splice(i, 1);
          }
      }
  }

  function onclick() {
      highlightNodes.clear();
      highlightLinks.clear();
  }

  function onClickClusterFacet(clusterId) {
      highlightNodes.clear();
      highlightLinks.clear();
      nodeByGroup.get(parseInt(clusterId)).forEach(neighbor => highlightNodes.add(neighbor));
  }

  // Add event when clicking on facet cluster
  $('.cluster-link-button').click(function () {
      var clusterId = $(this).attr('cluster-id');
      onClickClusterFacet(clusterId);
  });

  function drawBigNode(node, ctx) {
      ctx.beginPath();
      ctx.arc(node.x, node.y, NODE_R * 1.4, 0, 2 * Math.PI, false);
      ctx.fillStyle = 'rgb(160,160,160)';
      ctx.fill();
      ctx.beginPath();
      ctx.arc(node.x, node.y, NODE_R * 1.2, 0, 2 * Math.PI, false);
      ctx.fillStyle = node.color
      ctx.fill();
  }

  function drawSmallNode(node, ctx) {
      ctx.globalAlpha = 1;
      ctx.beginPath();
      ctx.arc(node.x, node.y, NODE_R * 1.2, 0, 2 * Math.PI, false);
      ctx.fillStyle = 'white';
      ctx.fill();
  }

  var width = elem.parentElement.getBoundingClientRect().width;
  var height = elem.parentElement.getBoundingClientRect().height;

  var Graph = ForceGraph()(elem);
  Graph.backgroundColor('rgba(128, 128, 128, 0.0)')
      .width(width)
      .height(height)
      .nodeRelSize(NODE_R)
      .nodeCanvasObject((node, ctx) => {
          drawSmallNode(node, ctx);
      })
      .nodeLabel(node => imageLabel(node))
      .nodeAutoColorBy('group')
      .nodeColor(node => cluster2color(node.group, num_clusters))
      .linkColor(link => highlightLinks.has(link) ? 'rgba(0,0,0,0.3)' : 'rgba(0,0,0,0.2)')
      .linkWidth(link => highlightLinks.has(link) ? 3 : 1)
      .onBackgroundClick(() => onclick())
      .onNodeHover(node => onNodeHover(node))
      .onNodeClick(node => {
          onNodeClick(node);
      })
      .nodeCanvasObjectMode(node => 'before')
      .nodeCanvasObject((node, ctx) => {
          drawSmallNode(node, ctx);
          if (hoverNode === node) {
              drawBigNode(node, ctx);
          }
          if (highlightNodes.size > 0) {
              if (highlightNodes.has(node)) {
                  drawBigNode(node, ctx);
              } else {
                  ctx.globalAlpha = 0.4;
              }
          }
      })

  var nodes = data.nodes;
  Graph
      .d3Force('collide', d3.forceCollide(Graph.nodeRelSize()*1.3))
      .d3Force('box', () => {
      const SQUARE_HALF_SIDE = Graph.nodeRelSize() * 800 * 0.5;
      nodes.forEach(node => {
          const x = node.x || 1, y = node.y || 1;
          // bounce on box walls
          if (Math.abs(x) > SQUARE_HALF_SIDE) { node.vx *= 0; }
          if (Math.abs(y) > SQUARE_HALF_SIDE) { node.vy *= 0; }
      });
      })
      .zoom(1)
      .graphData(data)
      .enableNodeDrag(false)
      .warmupTicks(300)
      .cooldownTicks(0)
      .onEngineStop(() => $('#graph-loader').hide());

  if (clusterId !== undefined) {
      onClickClusterFacet(clusterId);
  }
}
