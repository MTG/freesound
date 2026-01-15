const queuesStatusElement = document.getElementById('queuesStatus');
if (queuesStatusElement !== null) {
  setInterval(() => {
    var xmlHttp = new XMLHttpRequest();
    xmlHttp.open('GET', queuesStatusElement.dataset.url, true);
    xmlHttp.onreadystatechange = function () {
      if (xmlHttp.readyState == 4 && xmlHttp.status == 200)
        queuesStatusElement.innerHTML = xmlHttp.responseText;
    };
    xmlHttp.send(null);
    return xmlHttp.responseText;
  }, 1000);
}

// For charts

// Display line chart with downloads, sounds and users
function displayCharts(selectClass, data, options, exclude) {
  var margin = { top: 20, right: 200, bottom: 30, left: 50 },
    width = 700,
    height = 260;
  var svg = d3
    .select(selectClass)
    .append('svg')
    .attr('width', width + margin.left + margin.right)
    .attr('height', height + margin.top + margin.bottom);
  var g = svg
    .append('g')
    .attr('transform', 'translate(' + margin.left + ',' + margin.top + ')');

  var x = d3.scaleTime().rangeRound([0, width]);
  var formatDate = d3.timeFormat(options.timeFormat);

  var y = d3.scaleLinear().rangeRound([height, 0]);

  var concat = [].concat.apply([], data);

  x.domain(
    d3.extent(concat, function (d) {
      return new Date(d[options.attrX]);
    })
  );
  y.domain([
    0,
    1.2 *
      d3.max(concat, function (d) {
        return parseInt(d[options.attrY]);
      }),
  ]);

  g.append('g')
    .attr('transform', 'translate(0,' + height + ')')
    .call(d3.axisBottom(x).ticks(options.tickEvery).tickFormat(formatDate));

  g.append('g')
    .call(d3.axisLeft(y))
    .append('text')
    .attr('fill', '#000')
    .attr('transform', 'rotate(-90)')
    .attr('y', 6)
    .attr('dy', '0.71em')
    .attr('text-anchor', 'end')
    .text(options.yText);

  var i = 0;
  data.forEach(function (data2) {
    var line = d3
      .line()
      .curve(d3.curveMonotoneX)
      .x(function (d) {
        return x(new Date(d[options.attrX]));
      })
      .y(function (d) {
        return y(parseInt(d[options.attrY]));
      });

    data2.sort(function (a, b) {
      return d3.ascending(
        new Date(a[options.attrX]),
        new Date(b[options.attrX])
      );
    });

    g.append('path')
      .datum(data2)
      .attr('fill', 'none')
      .attr('stroke', options.legendData[i]['color'])
      .attr('stroke-linejoin', 'round')
      .attr('stroke-linecap', 'round')
      .attr('stroke-width', 2)
      .attr('d', line);
    i += 1;
  });

  // add legend
  var legend = svg
    .append('g')
    .attr('class', 'legend')
    .attr('x', width - 35)
    .attr('y', 20)
    .attr('height', 100)
    .attr('width', 100);

  legend
    .selectAll('g')
    .data(options.legendData)
    .enter()
    .each(function (d, i) {
      legend
        .append('rect')
        .attr('x', width - 20)
        .attr('y', i * 20 + 20)
        .attr('width', 10)
        .attr('height', 10)
        .attr('class', 'legend-item')
        .attr('line-numb', i)
        .attr('enabled', exclude[i] != null ? 0 : 1)
        .style('fill', d.color);

      legend
        .append('text')
        .attr('x', width - 8)
        .attr('y', i * 20 + 30)
        .text(d.name);
    });
  $(selectClass).find('.legend-item').click(mouseclick);

  function mouseclick(p) {
    $(selectClass).html('');
    var selected = parseInt($(this).attr('line-numb'));
    var enabled = parseInt($(this).attr('enabled'));
    var exclude2 = {};
    if (enabled) {
      var toRemove = data[selected];
      exclude2[selected] = toRemove;
      data[selected] = [];
    }
    for (var key in exclude) {
      if (exclude.hasOwnProperty(key)) {
        data[key] = exclude[key];
      }
    }
    displayCharts(selectClass, data, options, exclude2);
  }
}

// Display histogram
function displayHistogram(selectClass, data, options, exclude) {
  var margin = { top: 20, right: 200, bottom: 30, left: 50 },
    width = 700,
    height = 260;
  var svg = d3
    .select(selectClass)
    .append('svg')
    .attr('width', width + margin.left + margin.right)
    .attr('height', height + margin.top + margin.bottom);
  var g = svg
    .append('g')
    .attr('transform', 'translate(' + margin.left + ',' + margin.top + ')');

  var tooltip = d3.select('body').append('div').attr('class', 'toolTip');
  var formatCount = d3.format(',.0f');

  var x = d3.scaleTime().rangeRound([0, width]);
  x.domain(
    d3.extent(data, function (d) {
      return new Date(d[options.attrX]);
    })
  );
  var formatDate = d3.timeFormat(options.timeFormat);

  var y = d3.scaleLinear().rangeRound([height, 0]);

  function getY(d) {
    var total = 0;
    for (var i = 0; i < d.length; i++) {
      total += parseInt(d[i][options.attrY]);
    }
    return total;
  }

  var histogram = d3
    .histogram()
    .value(function (d) {
      return new Date(d[options.attrX]);
    })
    .domain(x.domain())
    .thresholds(x.ticks(options.tickEvery));

  var bins = histogram(data);

  y.domain([
    0,
    d3.max(bins, function (d) {
      return getY(d);
    }),
  ]);

  var bar = g
    .selectAll('.bar')
    .data(bins)
    .enter()
    .append('g')
    .attr('class', 'bar')
    .attr('transform', function (d) {
      return 'translate(' + x(d.x0) + ',' + y(getY(d)) + ')';
    });

  bar
    .append('rect')
    .attr('x', 1)
    .attr('width', x(bins[0].x1) - x(bins[0].x0) - 1)
    .attr('height', function (d) {
      return Math.max(0, height - y(getY(d)));
    })
    .on('mouseover', function (d) {
      tooltip
        .style('left', d3.event.pageX - 50 + 'px')
        .style('top', d3.event.pageY - 70 + 'px')
        .style('display', 'inline-block')
        .html('Week: ' + formatDate(d.x0) + '<br><b>€' + getY(d) + '</b>');
    })
    .on('mouseout', function () {
      tooltip.style('display', 'none');
    });

  g.append('g')
    .attr('class', 'axis axis--x')
    .attr('transform', 'translate(0,' + height + ')')
    .call(d3.axisBottom(x).tickFormat(formatDate));
}

// Monitor stats page
if (document.getElementById('global-stats') !== null) {
  $(document).ready(function () {
    $.get(totalsDataUrl, function (data) {
      $('#total-users').html(data.total_users);
      $('#users-with-sounds').html(data.users_with_sounds);
      $('#total-donations').html(data.total_donations);
      $('#proj-donations').html((data.donations_last_month * 12).toFixed(2));
      $('#total-sounds').html(data.sounds);
      $('#total-packs').html(data.packs);
      $('#total-downloads').html(data.downloads);
      $('#avg-downloads').html((data.downloads / data.sounds).toFixed(2));
      $('#total-comments').html(data.comments);
      $('#avg-comments').html((data.comments / data.sounds).toFixed(2));
      $('#total-ratings').html(data.ratings);
      $('#avg-ratings').html((data.ratings / data.sounds).toFixed(2));
      $('#total-tags').html(data.tags);
      $('#total-used-tags').html(data.tags_used);
      $('#avg-tags').html((data.tags_used / data.sounds).toFixed(2));
      $('#total-posts').html(data.posts);
      $('#total-threads').html(data.threads);
    });
    $.get(tagsDataUrl, function (d) {
      var tags = [];
      var max = 0;
      d.tags_stats.forEach(function (t) {
        max = Math.max(t['num'], max);
        tags.push([t['tag__name'], t['num']]);
      });

      WordCloud($('#tags-cloud-week')[0], {
        list: tags,
        weightFactor: 80 / max,
      });

      var tags = [];
      var max = 0;
      d.all_tags.forEach(function (t) {
        max = Math.max(t['num'], max);
        tags.push([t['tag__name'], t['num']]);
      });

      WordCloud($('#tags-cloud')[0], { list: tags, weightFactor: 100 / max });

      var tags = [];
      var max = 0;
      d.downloads_tags.forEach(function (t) {
        max = Math.max(t[0], max);
        tags.push([t[1], t[0]]);
      });
      WordCloud($('#down-tags-cloud')[0], {
        list: tags,
        weightFactor: 80 / max,
      });
    });
    // Display charts with Downloads, Uploads and Registers
    $.get(usersDataUrl, function (d) {
      var new_users_active = [];
      var new_users_inactive = [];
      for (var i = 0; i < d.new_users.length; i++) {
        if (d.new_users[i]['is_active']) {
          new_users_active.push([
            new Date(d.new_users[i]['day']).getTime(),
            d.new_users[i]['id__count'],
          ]);
        } else {
          new_users_inactive.push([
            new Date(d.new_users[i]['day']).getTime(),
            d.new_users[i]['id__count'],
          ]);
        }
      }
      new_users_active.sort(function (a, b) {
        return a[0] - b[0];
      });
      new_users_inactive.sort(function (a, b) {
        return a[0] - b[0];
      });
      Highcharts.chart($('.users')[0], {
        title: {
          text: '',
        },
        series: [
          {
            name: 'Active users',
            data: new_users_active,
          },
          {
            name: 'Non active users',
            data: new_users_inactive,
          },
        ],
        xAxis: {
          type: 'datetime',
          tickInterval: 24 * 3600 * 1000, // one day
          tickWidth: 0,
          gridLineWidth: 1,
          labels: {
            align: 'left',
            x: 3,
            y: -3,
          },
        },
        yAxis: {
          title: {
            text: 'Users',
          },
        },
      });
    });
    $.get(soundsDataUrl, function (d) {
      var new_sounds = [];
      for (var i = 0; i < d.new_sounds.length; i++) {
        new_sounds.push([
          new Date(d.new_sounds[i]['day']).getTime(),
          d.new_sounds[i]['id__count'],
        ]);
      }
      new_sounds.sort(function (a, b) {
        return a[0] - b[0];
      });
      var new_sounds_mod = [];
      for (var i = 0; i < d.new_sounds_mod.length; i++) {
        new_sounds_mod.push([
          new Date(d.new_sounds_mod[i]['day']).getTime(),
          d.new_sounds_mod[i]['id__count'],
        ]);
      }
      new_sounds_mod.sort(function (a, b) {
        return a[0] - b[0];
      });
      Highcharts.chart($('.uploads')[0], {
        title: {
          text: '',
        },
        series: [
          {
            name: 'New Sound',
            data: new_sounds,
          },
          {
            name: 'Moderated Sound',
            data: new_sounds_mod,
          },
        ],
        xAxis: {
          type: 'datetime',
          tickInterval: 24 * 3600 * 1000, // one day
          tickWidth: 0,
          gridLineWidth: 1,
          labels: {
            align: 'left',
            x: 3,
            y: -3,
          },
        },
        yAxis: {
          title: {
            text: 'Sounds',
          },
        },
      });
    });
    $.get(downloadsDataUrl, function (d) {
      var downloads_data = [];
      for (var i = 0; i < d.new_downloads_sound.length; i++) {
        downloads_data.push([
          new Date(d.new_downloads_sound[i]['day']).getTime(),
          d.new_downloads_sound[i]['id__count'],
        ]);
      }
      downloads_data.sort(function (a, b) {
        return a[0] - b[0];
      });
      var downloads_data_pack = [];
      for (var i = 0; i < d.new_downloads_pack.length; i++) {
        downloads_data_pack.push([
          new Date(d.new_downloads_pack[i]['day']).getTime(),
          d.new_downloads_pack[i]['id__count'],
        ]);
      }
      downloads_data_pack.sort(function (a, b) {
        return a[0] - b[0];
      });
      Highcharts.chart($('.downloads')[0], {
        title: {
          text: '',
        },
        series: [
          {
            name: 'Download Pack',
            data: downloads_data_pack,
          },
          {
            name: 'Download Sound',
            data: downloads_data,
          },
        ],
        xAxis: {
          type: 'datetime',
          tickInterval: 24 * 3600 * 1000, // one day
          tickWidth: 0,
          gridLineWidth: 1,
          labels: {
            align: 'left',
            x: 3,
            y: -3,
          },
        },
        yAxis: {
          title: {
            text: 'Downloads',
          },
        },
      });
    });
    $.get(donationsDataUrl, function (d) {
      displayHistogram(
        '.donations',
        d.new_donations,
        {
          yText: 'Amount (€)',
          attrX: 'day',
          attrY: 'amount__sum',
          timeFormat: '%d %b',
          tickEvery: d3.timeWeek.every(1),
          legendData: [{ color: 'crimson', name: 'donations' }],
        },
        {}
      );
    });
    $.get(activeUsersDataUrl, function (d) {
      var sound_downloads = [];
      for (var i = 0; i < d.sound_downloads.length; i++) {
        sound_downloads.push([
          new Date(d.sound_downloads[i]['week']).getTime(),
          d.sound_downloads[i]['amount__sum'],
        ]);
      }
      sound_downloads.sort(function (a, b) {
        return a[0] - b[0];
      });
      var pack_downloads = [];
      for (var i = 0; i < d.pack_downloads.length; i++) {
        pack_downloads.push([
          new Date(d.pack_downloads[i]['week']).getTime(),
          d.pack_downloads[i]['amount__sum'],
        ]);
      }
      pack_downloads.sort(function (a, b) {
        return a[0] - b[0];
      });
      var sounds = [];
      for (var i = 0; i < d.sounds.length; i++) {
        sounds.push([
          new Date(d.sounds[i]['week']).getTime(),
          d.sounds[i]['amount_sum'],
        ]);
      }
      sounds.sort(function (a, b) {
        return a[0] - b[0];
      });
      var posts = [];
      for (var i = 0; i < d.posts.length; i++) {
        posts.push([
          new Date(d.posts[i]['week']).getTime(),
          d.posts[i]['amount_sum'],
        ]);
      }
      posts.sort(function (a, b) {
        return a[0] - b[0];
      });
      var rate = [];
      for (var i = 0; i < d.rate.length; i++) {
        rate.push([
          new Date(d.rate[i]['week']).getTime(),
          d.rate[i]['amount_sum'],
        ]);
      }
      rate.sort(function (a, b) {
        return a[0] - b[0];
      });
      var comments = [];
      for (var i = 0; i < d.comments.length; i++) {
        rate.push([
          new Date(d.comments[i]['week']).getTime(),
          d.comments[i]['amount_sum'],
        ]);
      }
      comments.sort(function (a, b) {
        return a[0] - b[0];
      });
      Highcharts.chart($('.active-users')[0], {
        title: {
          text: '',
        },
        series: [
          {
            name: 'Sound Downloads',
            data: sound_downloads,
          },
          {
            name: 'Pack Downloads',
            data: pack_downloads,
          },
          {
            name: 'Comments',
            data: comments,
          },
          {
            name: 'Posts',
            data: posts,
          },
          {
            name: 'Rates',
            data: rate,
          },
          {
            name: 'Sounds Upload',
            data: sounds,
          },
        ],
        yAxis: {
          title: {
            text: 'Users',
          },
        },
        xAxis: {
          type: 'datetime',
          tickInterval: 7 * 24 * 3600 * 1000, // one week
          tickWidth: 0,
          gridLineWidth: 1,
          labels: {
            align: 'left',
            x: 3,
            y: -3,
          },
        },
      });
    });
    $.get(queriesDataUrl, function (d) {
      var tags = [];
      var max = 0;
      for (var key in d.terms) {
        if (d.terms.hasOwnProperty(key)) {
          max = Math.max(d.terms[key], max);
          tags.push([key, d.terms[key]]);
        }
      }
      WordCloud($('#queries-wordcloud')[0], {
        list: tags,
        weightFactor: 100 / max,
      });
    });
  });
}

// API monitor page
if (document.getElementsByClassName('api-usage')[0] !== undefined) {
  $(document).ready(function () {
    var usage = [];
    var limit = [];
    var max_usage = 0;

    for (var i in data) {
      var date = data[i][0];
      var count = data[i][1];
      if (count > max_usage) {
        max_usage = count;
      }
      usage.push({ day: date, count: count });
      limit.push({ day: date, count: dayLimit });
    }
    if (usage.length > 0) {
      if (max_usage < dayLimit * 0.5) {
        var toShow = [usage];
        var legend = [{ color: 'crimson', name: 'requests/day' }];
      } else {
        var toShow = [usage, limit];
        var legend = [
          { color: 'crimson', name: 'requests/day' },
          { color: 'gray', name: 'daily limit' },
        ];
      }

      displayCharts(
        '.api-usage',
        toShow,
        {
          attrX: 'day',
          attrY: 'count',
          timeFormat: '%a %d',
          tickEvery: d3.timeDay.every(n_days / 10),
          legendData: legend,
        },
        {}
      );
    }
  });
}
