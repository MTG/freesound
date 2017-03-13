$( document ).ready(function() {

  $.get(totalsDataUrl, function(data){
    $('#total-users').html(data.total_users);
    $('#users-with-sounds').html(data.users_with_sounds);
    $('#total-donations').html(data.total_donations);
    $('#total-sounds').html(data.sounds);
    $('#total-packs').html(data.packs);
    $('#total-downloads').html(data.downloads);
    $('#avg-downloads').html((data.downloads/data.sounds).toFixed(2));
    $('#total-comments').html(data.comments);
    $('#avg-comments').html((data.comments/data.sounds).toFixed(2));
    $('#total-ratings').html(data.ratings);
    $('#avg-ratings').html((data.ratings/data.sounds).toFixed(2));
    $('#total-tags').html(data.tags);
    $('#total-used-tags').html(data.tags_used);
    $('#avg-tags').html((data.tags_used/data.sounds).toFixed(2));
    $('#total-posts').html(data.posts);
    $('#total-threads').html(data.threads);
  });
  $.get(tagsDataUrl, function(d){
    loadTagGraph(d);

    var tags = [];
    var max = 0;
    d.all_tags.forEach(function(t) {
      max = Math.max(t['num'], max);
      tags.push([t['tag__name'], t['num']]);
    });

    WordCloud($('#tags-cloud')[0], { list: tags, weightFactor: 100/max});

    var tags = [];
    var max = 0;
    d.downloads_tags.forEach(function(t) {
      max = Math.max(t[2], max);
      tags.push([t[1], t[2]]);
    });
    WordCloud($('#down-tags-cloud')[0], { list: tags, weightFactor: 100/max});
  });
  $.get(usersDataUrl, function(d){
      var active_users = d.new_users.filter(e => {return e.is_active})
      var non_active_users = d.new_users.filter(e => {return !e.is_active})
      // Display charts with Downloads, Uploads and Registers
      displayCharts('.users', [active_users, non_active_users], {
        yText: 'Users',
        attrX: 'day',
        attrY: 'id__count',
        timeFormat: "%a %d",
        tickEvery: d3.timeDay.every(1),
        legendData: [{color: 'crimson', name: 'active'}, {color: 'grey', name: 'non active'}]
      });
  });
  $.get(soundsDataUrl, function(d){
      displayCharts('.uploads', [d.new_sounds, d.new_sounds_mod], {
        yText: 'Sounds',
        attrX: 'day',
        attrY: 'id__count',
        timeFormat: "%a %d",
        tickEvery: d3.timeDay.every(1),
        legendData: [{color: 'crimson', name: 'processed'}, {color: 'grey', name: 'moderated'}]
      });
  });
  $.get(downloadsDataUrl, function(d){
      displayCharts('.downloads', [d.new_downloads_pack, d.new_downloads_sound], {
        yText: 'Downloads',
        attrX: 'day',
        attrY: 'id__count',
        timeFormat: "%a %d",
        tickEvery: d3.timeDay.every(1),
        legendData: [{color: 'crimson', name: 'packs'}, {color: 'grey', name: 'sounds'}]
      });
  });
  $.get(donationsDataUrl, function(d){
      displayCharts('.donations', [d.new_donations ], {
        yText: 'Amount (€)',
        attrX: 'week',
        attrY: 'amount__sum',
        timeFormat: "%d %b",
        tickEvery: d3.timeMonth.every(1),
        legendData: [{color: 'crimson', name: 'donations'},]
      });
  });
  $.get(activeUsersDataUrl, function(d){
      displayCharts('.active-users', [d.downloads, d.sounds, d.posts, d.rate, d.comments], {
        yText: 'Users',
        attrX: 'week',
        attrY: 'amount__sum',
        timeFormat: "%d %b",
        tickEvery: d3.timeMonth.every(1),
        legendData: [
          {color: 'crimson', name: 'downloads'},
          {color: 'gray', name: 'sounds'},
          {color: 'black', name: 'posts'},
          {color: 'yellow', name: 'ratings'},
          {color: 'blue', name: 'comments'},
        ]
      });
  });
  $.get(queriesDataUrl, function(d){
    var tags = [];
    var max = 0;
    for (var key in d.terms) {
      if (d.terms.hasOwnProperty(key)) {
        max = Math.max(d.terms[key], max);
        tags.push([key, d.terms[key]]);
      }
    }
    WordCloud($('#queries-wordcloud')[0], { list: tags, weightFactor: 100/max});
  
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

function loadTagGraph(data){
  // Display most used tags with bubbles
  var margin = {top: 20, right: 100, bottom: 0, left: 20},
    width = 680,
    height = 650;

  var c = d3.scaleOrdinal(d3.schemeCategory20c);

  var formatDate = d3.timeFormat("%a %d");
  var xScale = d3.scaleTime()
    .range([0, width]);

  var dates = [];
  var counts = [];
  for (var key in data.tags_stats) {
    if (data.tags_stats.hasOwnProperty(key)) {
      Array.from(data.tags_stats[key]).forEach(d => {
        dates.push(new Date(d['day']));
        counts.push(d['count']);
      });
    }
  }
  xScale.domain(d3.extent(dates));
  var xAxis = d3.axisTop(xScale).ticks(d3.timeDay.every(1)).tickFormat(formatDate);

  var rScale = d3.scalePow()
      .domain([0, d3.max(counts)])
      .range([2, 10]);

  var svg = d3.select('.tags').append("svg")
    .attr("width", width + margin.left + margin.right)
    .attr("height", height + margin.top + margin.bottom)
    .style("margin-left", margin.left + "px")
    .append("g")
    .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

  svg.append("g")
    .attr("class", "x axis")
    .attr("transform", "translate(-" + 5 + ",0)")
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
function displayCharts(selectClass, data, options){
  var margin = {top: 20, right: 200, bottom: 30, left: 50},
    width = 700,
    height = 260;
  var svg = d3.select(selectClass).append("svg")
    .attr("width", width + margin.left + margin.right)
    .attr("height", height + margin.top + margin.bottom);
  var g = svg.append("g")
    .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

  var x = d3.scaleTime()
    .rangeRound([0, width]);
  var formatDate = d3.timeFormat(options.timeFormat);

  var y = d3.scaleLinear()
    .rangeRound([height, 0]);

  var concat = [].concat.apply([], data);
  x.domain(d3.extent(concat, function(d) { return new Date(d[options.attrX]); }));
  y.domain([0, d3.max(concat, function(d) { return parseInt(d[options.attrY])})]);
  
  g.append("g")
      .attr("transform", "translate(0," + height + ")")
      .call(d3.axisBottom(x)
          .ticks(options.tickEvery)
          .tickFormat(formatDate));

  g.append("g")
      .call(d3.axisLeft(y))
      .append("text")
      .attr("fill", "#000")
      .attr("transform", "rotate(-90)")
      .attr("y", 6)
      .attr("dy", "0.71em")
      .attr("text-anchor", "end")
      .text(options.yText);

  var i = 0;
  data.forEach(function(data2) {

      var line = d3.line()
          .curve(d3.curveMonotoneX)
          .x(function(d) { return x(new Date(d[options.attrX])); })
          .y(function(d) { return y(parseInt(d[options.attrY])); });


      data2.sort(function(a, b) { 
        return d3.ascending(new Date(a[options.attrX]), new Date(b[options.attrX])); 
      });

      g.append("path")
        .datum(data2)
        .attr("fill", "none")
        .attr("stroke", options.legendData[i]['color'])
        .attr("stroke-linejoin", "round")
        .attr("stroke-linecap", "round")
        .attr("stroke-width", 3)
        .attr("d", line);
      i+=1;
  }); 

  // add legend   
  var legend = svg.append("g")
    .attr("class", "legend")
    .attr("x", width - 35)
    .attr("y", 20)
    .attr("height", 100)
    .attr("width", 100);

  legend.selectAll('g')
    .data(options.legendData)
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

