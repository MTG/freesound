$( document ).ready(function() {

  $.get(totalUsersDataUrl, function(data){
    $('#total-users').html(data.total_users);
    $('#users-with-sounds').html(data.users_with_sounds);
  });
  $.get(totalSoundsDataUrl, function(data){
    $('#total-sounds').html(data.sounds);
    $('#total-packs').html(data.packs);
    $.get(totalActivityDataUrl, function(d){
      $('#total-downloads').html(d.downloads);
      $('#avg-downloads').html(Math.round(d.downloads/data.sounds));
      $('#total-comments').html(d.comments);
      $('#avg-comments').html(Math.round(d.comments/data.sounds));
      $('#total-ratings').html(d.ratings);
      $('#avg-ratings').html(Math.round(d.ratings/data.sounds));
    });
  });
  $.get(totalTagsDataUrl, function(data){
    $('#total-tags').html(data.tags);
    $('#total-used-tags').html(data.tags_used);
  });
  $.get(totalForumDataUrl, function(data){
    $('#total-posts').html(data.posts);
    $('#total-threads').html(data.threads);
  });
  $.get(tagsDataUrl, function(d){
    loadTagGraph(d);
  });
  $.get(usersDataUrl, function(d){
      var active_users = d.new_users.filter(e => {return e.is_active})
      var non_active_users = d.new_users.filter(e => {return !e.is_active})
      // Display charts with Downloads, Uploads and Registers
      displayCharts('.users', active_users, non_active_users, 'Users',
          [{color: 'crimson', name: 'active'}, {color: 'grey', name: 'non active'}]);
  });
  $.get(soundsDataUrl, function(d){
      displayCharts('.uploads', d.new_sounds, d.new_sounds_mod, 'Sounds',
          [{color: 'crimson', name: 'processed'}, {color: 'grey', name: 'moderated'}]);
  });
  $.get(downloadsDataUrl, function(d){
      displayCharts('.downloads', d.new_downloads_pack, d.new_downloads_sound, 'Downloads',
          [{color: 'crimson', name: 'packs'}, {color: 'grey', name: 'sounds'}]);
  });
});

function truncate(str, maxLength, suffix) {
  if(str.length > maxLength) {
    str = str.substring(0, maxLength + 1); 
    str = str.substring(0, Math.min(str.length, str.lastIndexOf(" ")));
    str = str + suffix;
  }
  return str;
}

function loadTotals(data){
  }
function loadTagGraph(data){
  // Display most used tags with bubbles
  var margin = {top: 20, right: 100, bottom: 0, left: 20},
    width = 680,
    height = 650;

  var c = d3.scaleOrdinal(d3.schemeCategory20c);

  var formatDate = d3.timeFormat("%a %d");
  var xScale = d3.scaleTime()
    .range([0, width]);
  var xAxis = d3.axisTop(xScale).ticks(d3.timeDay.every(1)).tickFormat(formatDate);

  for (var key in data.tags_stats) {
    if (data.tags_stats.hasOwnProperty(key)) {
      xScale.domain(d3.extent(data.tags_stats[key], function(d) { return new Date(d['day']); }));
    }
  }

  var svg = d3.select('.tags').append("svg")
    .attr("width", width + margin.left + margin.right)
    .attr("height", height + margin.top + margin.bottom)
    .style("margin-left", margin.left + "px")
    .append("g")
    .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

  svg.append("g")
    .attr("class", "x axis")
    .attr("transform", "translate(-" + 15 + ",0)")
    .call(xAxis);

  var j = 0;
  for (var key in data.tags_stats) {
    if (data.tags_stats.hasOwnProperty(key)) {
    var g = svg.append("g").attr("class","journal");

    var circles = g.selectAll("circle")
      .data(data.tags_stats[key])
      .enter()
      .append("circle");

    var text = g.selectAll("text")
      .data(data.tags_stats[key])
      .enter()
      .append("text");

    var rScale = d3.scaleLinear()
      .domain([0, d3.max(data.tags_stats[key], function(d) { return d['count']; })])
      .range([2, 9]);

    circles
      .attr("cx", function(d) { return xScale(new Date(d['day']))})
      .attr("cy", j*20+20)
      .attr("r", function(d) { return rScale(d['count']);})
      .style("fill", function(d) { return c(j); });

    text
      .attr("y", j*20+25)
      .attr("x", function(d, i) { return xScale(new Date(d['day']))})
      .attr("class","value")
      .text(function(d){ return d['count']; })
      .style("fill", function(d) { return c(j); })
      .style("display","none");

    g.append("text")
      .attr("y", j*20+25)
      .attr("x",width+20)
      .attr("class","label")
      .text(truncate(key,30,"..."))
      .style("fill", function(d) { return c(j); })
      .on("mouseover", mouseover)
      .on("mouseout", mouseout);
    j += 1;
    }
  }

  function mouseover(p) {
    var g = d3.select(this).node().parentNode;
    d3.select(g).selectAll("circle").style("display","none");
    d3.select(g).selectAll("text.value").style("display","block");
  }

  function mouseout(p) {
    var g = d3.select(this).node().parentNode;
    d3.select(g).selectAll("circle").style("display","block");
    d3.select(g).selectAll("text.value").style("display","none");
  }
}

// Display line chart with downloads, sounds and users
function displayCharts(selectClass, data, data2, yText, legendData){
  var margin = {top: 20, right: 200, bottom: 30, left: 50},
    width = 700,
    height = 400;
  var svg = d3.select(selectClass).append("svg")
    .attr("width", width + margin.left + margin.right)
    .attr("height", height + margin.top + margin.bottom);
  var g = svg.append("g")
    .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

  var x = d3.scaleTime()
    .rangeRound([0, width]);
  var formatDate = d3.timeFormat("%a %d");

  var y = d3.scaleLinear()
    .rangeRound([height, 0]);

  x.domain(d3.extent(data.concat(data2), function(d) { return new Date(d['day']); }));
  y.domain([0, d3.max(data.concat(data2), function(d) { return d['id__count']; })]);

  var line = d3.line()
      .curve(d3.curveMonotoneX)
      .x(function(d) { return x(new Date(d['day'])); })
      .y(function(d) { return y(d['id__count']); });

  var line2 = d3.line()
      .curve(d3.curveMonotoneX)
      .x(function(d) { return x(new Date(d['day'])); })
      .y(function(d) { return y(d['id__count']); });


  g.append("g")
      .attr("transform", "translate(0," + height + ")")
      .call(d3.axisBottom(x)
          .ticks(d3.timeDay.every(1))
          .tickFormat(formatDate));

  g.append("g")
      .call(d3.axisLeft(y))
      .append("text")
      .attr("fill", "#000")
      .attr("transform", "rotate(-90)")
      .attr("y", 6)
      .attr("dy", "0.71em")
      .attr("text-anchor", "end")
      .text(yText);

    data.sort(function(a, b) { 
      return d3.ascending(new Date(a.day), new Date(b.day)); 
    });

    data2.sort(function(a, b) { 
      return d3.ascending(new Date(a.day), new Date(b.day)); 
    });

    g.append("path")
      .datum(data)
      .attr("fill", "none")
      .attr("stroke", legendData[0]['color'])
      .attr("stroke-linejoin", "round")
      .attr("stroke-linecap", "round")
      .attr("stroke-width", 3)
      .attr("d", line);

    g.append("path")
      .datum(data2)
      .attr("fill", "none")
      .attr("stroke", legendData[1]['color'])
      .attr("stroke-linejoin", "round")
      .attr("stroke-linecap", "round")
      .attr("stroke-width", 3)
      .attr("d", line2);
  
    // add legend   
    var legend = svg.append("g")
      .attr("class", "legend")
      .attr("x", width - 35)
      .attr("y", 20)
      .attr("height", 100)
      .attr("width", 100);

    legend.selectAll('g')
      .data(legendData)
        .enter()
        .each(function(d, i) {
          legend.append("rect")
            .attr("x", width - 20)
            .attr("y", i*20 + 20)
            .attr("width", 10)
            .attr("height", 10)
            .style("fill", d.color); 

          legend.append("text")
            .attr("x", width - 8)
            .attr("y", i * 20 + 30)
            .text(d.name);
      });
}
