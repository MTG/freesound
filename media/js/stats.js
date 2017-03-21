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
    var tags = [];
    var max = 0;
    d.tags_stats.forEach(function(t) {
      max = Math.max(t['num'], max);
      tags.push([t['tag__name'], t['num']]);
    });

    WordCloud($('#tags-cloud-week')[0], { list: tags, weightFactor: 80/max});

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
      max = Math.max(t[0], max);
      tags.push([t[1], t[0]]);
    });
    WordCloud($('#down-tags-cloud')[0], { list: tags, weightFactor: 80/max});
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
      }, {});
  });
  $.get(soundsDataUrl, function(d){
      displayCharts('.uploads', [d.new_sounds, d.new_sounds_mod], {
        yText: 'Sounds',
        attrX: 'day',
        attrY: 'id__count',
        timeFormat: "%a %d",
        tickEvery: d3.timeDay.every(1),
        legendData: [{color: 'crimson', name: 'processed'}, {color: 'grey', name: 'moderated'}]
      }, {});
  });
  $.get(downloadsDataUrl, function(d){
      displayCharts('.downloads', [d.new_downloads_pack, d.new_downloads_sound], {
        yText: 'Downloads',
        attrX: 'day',
        attrY: 'id__count',
        timeFormat: "%a %d",
        tickEvery: d3.timeDay.every(1),
        legendData: [{color: 'crimson', name: 'packs'}, {color: 'grey', name: 'sounds'}]
      }, {});
  });
  $.get(donationsDataUrl, function(d){
      displayCharts('.donations', [d.new_donations ], {
        yText: 'Amount (€)',
        attrX: 'week',
        attrY: 'amount__sum',
        timeFormat: "%d %b",
        tickEvery: d3.timeMonth.every(1),
        legendData: [{color: 'crimson', name: 'donations'},]
      }, {});
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
      }, {});
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

// Display line chart with downloads, sounds and users
function displayCharts(selectClass, data, options, exclude){
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
          .attr("class", "legend-item")
          .attr("line-numb", i)
          .attr("enabled", (exclude[i] != null ) ? 0 : 1)
          .style("fill", d.color) 

        legend.append("text")
          .attr("x", width - 8)
          .attr("y", i * 20 + 30)
          .text(d.name);
    });
  $(".legend-item").click(mouseclick);
  
  function mouseclick(p) {
    $(selectClass).html("");
    var selected = parseInt($(this).attr('line-numb'));
    var enabled = parseInt($(this).attr('enabled'));
    var exclude2 = {};
    if (enabled){
      var toRemove = data[selected];
      exclude2[selected] = toRemove;
      data[selected]= [];
    }
    for (var key in exclude) {
      if (exclude.hasOwnProperty(key)){
        data[key]= exclude[key];
      }
    }
    displayCharts(selectClass, data, options, exclude2);
  }

}

