
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
  y.domain([0, 1.2*d3.max(concat, function(d) { return parseInt(d[options.attrY])})]);
  
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
        .attr("stroke-width", 2)
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
  $(selectClass).find(".legend-item").click(mouseclick);
  
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

// Display histogram
function displayHistogram(selectClass, data, options, exclude){
  var margin = {top: 20, right: 200, bottom: 30, left: 50},
    width = 700,
    height = 260;
  var svg = d3.select(selectClass).append("svg")
    .attr("width", width + margin.left + margin.right)
    .attr("height", height + margin.top + margin.bottom);
  var g = svg.append("g")
    .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

  var tooltip = d3.select("body").append("div").attr("class", "toolTip");
  var formatCount = d3.format(",.0f");

  var x = d3.scaleTime()
    .rangeRound([0, width]);
  x.domain(d3.extent(data, function(d) { return new Date(d[options.attrX]); }));
  var formatDate = d3.timeFormat(options.timeFormat);

  var y = d3.scaleLinear()
    .rangeRound([height, 0]);

  function getY(d){
    var total = 0;
    for (var i=0;i<d.length;i++){
        total += parseInt(d[i][options.attrY]);
    }
    return total;
  }

  var histogram = d3.histogram()
    .value(function(d) { return new Date(d[options.attrX]); })
    .domain(x.domain())
    .thresholds(x.ticks(options.tickEvery));

  var bins = histogram(data);

  y.domain([0, d3.max(bins, function(d) { return getY(d); })]);

  var bar = g.selectAll(".bar")
    .data(bins)
    .enter().append("g")
      .attr("class", "bar")
      .attr("transform", function(d) { return "translate(" + x(d.x0) + "," + y(getY(d))+")";});

  bar.append("rect")
      .attr("x", 1)
      .attr("width", x(bins[0].x1) - x(bins[0].x0) - 1)
      .attr("height", function(d) { return Math.max(0, height - y(getY(d)))})
      .on("mouseover", function(d) {
        tooltip
          .style("left", d3.event.pageX - 50 + "px")
          .style("top", d3.event.pageY - 70 + "px")
          .style("display", "inline-block")
          .html("Week: "+formatDate(d.x0) + "<br><b>€" + getY(d)+"</b>");
      }).on("mouseout", function() {
        tooltip.style("display", "none");
      })

  g.append("g")
      .attr("class", "axis axis--x")
      .attr("transform", "translate(0," + height + ")")
      .call(d3.axisBottom(x).tickFormat(formatDate));
  }

