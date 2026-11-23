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
      if (Object.prototype.hasOwnProperty.call(exclude, key)) {
        data[key] = exclude[key];
      }
    }
    displayCharts(selectClass, data, options, exclude2);
  }
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
        if (Object.prototype.hasOwnProperty.call(d.terms, key)) {
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

// Monitor donations page
var donationsForm = document.getElementById('donations-date-range');
if (donationsForm !== null) {
  var DONATIONS_COLOR = '#e11e47';
  var SOURCE_COLORS = { p: '#003087', s: '#635bff', t: '#8c8c8c' };

  var formatEuros = function (amount) {
    if (amount === null || amount === undefined) {
      return '–';
    }
    return (
      '€' +
      amount.toLocaleString(undefined, {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      })
    );
  };

  var formatNumber = function (value, decimals) {
    if (value === null || value === undefined) {
      return '–';
    }
    return value.toLocaleString(undefined, {
      minimumFractionDigits: decimals || 0,
      maximumFractionDigits: decimals || 0,
    });
  };

  var formatPercentage = function (part, total) {
    if (!total) {
      return '–';
    }
    return formatNumber((100 * part) / total, 1) + '%';
  };

  var setText = function (id, text) {
    document.getElementById(id).textContent = text;
  };

  var makeRow = function (cells) {
    var row = document.createElement('tr');
    for (var i = 0; i < cells.length; i++) {
      var cell = document.createElement('td');
      cell.textContent = cells[i];
      row.appendChild(cell);
    }
    return row;
  };

  var fillTable = function (id, rows) {
    var body = document.getElementById(id);
    body.innerHTML = '';
    for (var i = 0; i < rows.length; i++) {
      body.appendChild(makeRow(rows[i]));
    }
  };

  var columnChart = function (containerId, categories, series, options) {
    Highcharts.chart(document.getElementById(containerId), {
      chart: { type: 'column' },
      title: { text: '' },
      legend: { enabled: series.length > 1 },
      credits: { enabled: false },
      xAxis: {
        categories: categories,
        title: { text: options.xAxisTitle },
        // Rotate labels of long series. Short ones are only rotated by
        // Highcharts if they overlap.
        labels: { rotation: categories.length > 12 ? -45 : undefined },
      },
      yAxis: { min: 0, title: { text: options.yAxisTitle } },
      plotOptions: { column: { stacking: options.stacked ? 'normal' : null } },
      tooltip: {
        shared: series.length > 1,
        formatter: options.tooltip,
      },
      series: series,
    });
  };

  // Tooltip helpers that work in Highcharts < 12 (`this` is a context object
  // and `this.x` the category name) and >= 12 (`this` is the point and
  // `this.x` the category index)
  var tooltipPoints = function (context) {
    var points = context.points || [context.point || context];
    var result = [];
    for (var i = 0; i < points.length; i++) {
      result.push(points[i].point || points[i]);
    }
    return result;
  };

  var tooltipCategory = function (point) {
    return point.category !== undefined ? point.category : point.x;
  };

  // Shared tooltip listing the value of each series. When the hovered bar has
  // an estimate for the rest of the current day/month/year, it also shows the
  // projected total.
  var makeTooltip = function (format) {
    return function () {
      var points = tooltipPoints(this);
      var text = tooltipCategory(points[0]);
      var total = 0;
      var hasEstimate = false;
      var shown = [];
      var estimates = [];
      for (var i = 0; i < points.length; i++) {
        if (points[i].y !== null && points[i].y !== undefined) {
          total += points[i].y;
          if (points[i].series.options.isEstimate) {
            hasEstimate = true;
            estimates.push(points[i]);
          } else {
            shown.push(points[i]);
          }
        }
      }
      // List the estimate after the actual donations
      shown = shown.concat(estimates);
      for (var j = 0; j < shown.length; j++) {
        text +=
          '<br>' +
          (shown.length > 1 ? shown[j].series.name + ': ' : '') +
          '<b>' +
          format(shown[j].y) +
          '</b>';
      }
      if (hasEstimate) {
        text += '<br>Projected total: <b>' + format(total) + '</b>';
      }
      return text;
    };
  };

  // Series stacked on top of the last bar with the estimate for the rest of
  // the current period. In a stack, Highcharts draws the first series on top,
  // so it has to go first in the series list.
  var estimateSeries = function (name, numBars, value) {
    var data = [];
    for (var i = 0; i < numBars; i++) {
      data.push(i === numBars - 1 ? value : null);
    }
    return {
      name: name,
      data: data,
      color: 'rgba(225, 30, 71, 0.25)',
      borderColor: DONATIONS_COLOR,
      dashStyle: 'Dash',
      legendIndex: 100,
      isEstimate: true,
    };
  };

  var drawAmountChart = function (
    containerId,
    data,
    labelKey,
    xAxisTitle,
    projection,
    estimateName
  ) {
    var categories = [];
    var amounts = [];
    for (var i = 0; i < data.length; i++) {
      categories.push(String(data[i][labelKey]));
      amounts.push(data[i].amount);
    }
    var series = [{ name: 'Donations', data: amounts, color: DONATIONS_COLOR }];
    if (projection) {
      series.unshift(
        estimateSeries(estimateName, data.length, projection.remaining)
      );
    }
    columnChart(containerId, categories, series, {
      xAxisTitle: xAxisTitle,
      yAxisTitle: 'Amount (€)',
      stacked: true,
      tooltip: makeTooltip(formatEuros),
    });
  };

  var setProjectionText = function (id, text) {
    document.getElementById(id).textContent = text || '';
  };

  var drawDailyChart = function (daily) {
    var projection = daily.projection;
    drawAmountChart(
      'daily-donations-chart',
      daily.data,
      'day',
      'Day',
      projection,
      'Estimate for the rest of the day'
    );
    setProjectionText(
      'daily-donations-projection',
      projection &&
        'Estimated total for today: ' +
          formatEuros(projection.projected_total) +
          ' (' +
          formatNumber(100 * projection.elapsed_share, 1) +
          (projection.method === 'past_distribution'
            ? "% of a day's donations usually arrive by this time, based on the last " +
              projection.past_periods_used +
              ' days).'
            : '% of the day has passed).')
    );
  };

  var drawYearlyChart = function (yearly) {
    var projection = yearly.projection;
    drawAmountChart(
      'yearly-donations-chart',
      yearly.data,
      'year',
      'Year',
      projection,
      'Projection for the rest of the year'
    );
    var basis =
      projection && projection.method === 'monthly_distribution'
        ? 'how donations were spread over the months in ' +
          projection.years_used.join(', ')
        : 'the share of the year elapsed so far';
    setProjectionText(
      'yearly-donations-projection',
      projection &&
        'Projected ' +
          projection.year +
          ' total: ' +
          formatEuros(projection.projected_total) +
          ' (' +
          formatNumber(100 * projection.elapsed_share, 1) +
          '% of the yearly donations usually arrive by today, based on ' +
          basis +
          ').'
    );
  };

  var drawMonthlyBySourceChart = function (monthly, measure) {
    var projection = monthly.projection;
    var categories = [];
    for (var i = 0; i < monthly.data.length; i++) {
      categories.push(monthly.data[i].month);
    }
    var series = [];
    for (var code in monthly.sources) {
      if (Object.prototype.hasOwnProperty.call(monthly.sources, code)) {
        var values = [];
        for (var j = 0; j < monthly.data.length; j++) {
          values.push(monthly.data[j].by_source[code][measure]);
        }
        series.push({
          name:
            monthly.sources[code].charAt(0).toUpperCase() +
            monthly.sources[code].slice(1),
          data: values,
          color: SOURCE_COLORS[code],
        });
      }
    }
    if (projection) {
      series.unshift(
        estimateSeries(
          'Estimated',
          monthly.data.length,
          measure === 'amount'
            ? projection.remaining
            : projection.remaining_count
        )
      );
    }
    columnChart('monthly-donations-chart', categories, series, {
      xAxisTitle: 'Month',
      yAxisTitle: measure === 'amount' ? 'Amount (€)' : 'Number of donations',
      stacked: true,
      tooltip: makeTooltip(
        measure === 'amount'
          ? formatEuros
          : function (value) {
              return formatNumber(value, value % 1 ? 1 : 0);
            }
      ),
    });
    setProjectionText(
      'monthly-donations-projection',
      projection &&
        'Estimated total for ' +
          projection.label +
          ': ' +
          formatEuros(projection.projected_total) +
          ' from about ' +
          formatNumber(projection.projected_count) +
          ' donations (' +
          formatNumber(100 * projection.elapsed_share, 1) +
          (projection.method === 'past_distribution'
            ? "% of a month's donations usually arrive by this point of the month, based on the last " +
              projection.past_periods_used +
              ' months).'
            : '% of the month has passed).')
    );
  };

  var updateSummary = function (sectionId, section) {
    setText(sectionId + '-range', section.start + ' to ' + section.end);
    setText(sectionId + '-total', formatEuros(section.amount));
    setText(
      sectionId + '-average',
      formatEuros(
        section.data.length ? section.amount / section.data.length : 0
      )
    );
    setText(sectionId + '-count', formatNumber(section.count));
    setText(sectionId + '-median', formatEuros(section.median_amount));
  };

  var updatePeriod = function (period) {
    var i;
    var ranges = document.getElementsByClassName('period-range');
    for (i = 0; i < ranges.length; i++) {
      ranges[i].textContent =
        period.start +
        ' to ' +
        period.end +
        ' · ' +
        formatNumber(period.count) +
        ' donations';
    }

    // Donors
    setText('period-unique-donors', formatNumber(period.unique_donors));
    var groups = [
      ['period-first-time', period.first_time],
      ['period-returning', period.returning],
    ];
    for (i = 0; i < groups.length; i++) {
      setText(
        groups[i][0],
        formatPercentage(groups[i][1].count, period.count) +
          ' (' +
          formatNumber(groups[i][1].count) +
          ' donations, ' +
          formatPercentage(groups[i][1].amount, period.amount) +
          ' of the amount)'
      );
    }
    var days = period.returning.median_days_since_previous;
    setText(
      'period-days-since-previous',
      days === null ? '–' : formatNumber(days) + ' days'
    );

    // Uploaders
    var uploaderGroups = ['uploaders', 'non-uploaders', 'no-account'];
    for (i = 0; i < uploaderGroups.length; i++) {
      var group = period.uploaders[uploaderGroups[i].replace('-', '_')];
      setText(
        'period-' + uploaderGroups[i] + '-count',
        formatNumber(group.count) +
          ' (' +
          formatPercentage(group.count, period.count) +
          ')'
      );
      setText(
        'period-' + uploaderGroups[i] + '-amount',
        formatEuros(group.amount) +
          ' (' +
          formatPercentage(group.amount, period.amount) +
          ')'
      );
    }

    // Recurrent donors
    var recurrent = period.recurrent;
    setText(
      'recurrent-donations',
      formatPercentage(recurrent.donations, period.count) +
        ' (' +
        formatNumber(recurrent.donations) +
        ' donations, ' +
        formatEuros(recurrent.amount) +
        ', ' +
        formatPercentage(recurrent.amount, period.amount) +
        ' of the amount)'
    );
    setText(
      'recurrent-donors-count',
      formatNumber(recurrent.donors) +
        ' of ' +
        formatNumber(period.unique_donors) +
        ' donors (' +
        formatPercentage(recurrent.donors, period.unique_donors) +
        ')'
    );
    setText(
      'recurrent-amount',
      'average ' +
        formatEuros(recurrent.average_amount) +
        ', median ' +
        formatEuros(recurrent.median_amount)
    );
    setText(
      'recurrent-other-amount',
      formatEuros(recurrent.non_recurrent_average_amount)
    );
    setText(
      'recurrent-interval',
      recurrent.series
        ? 'median ' +
            formatNumber(recurrent.median_interval_days) +
            ' days, average ' +
            formatNumber(recurrent.average_interval_days) +
            ' days'
        : '–'
    );
    setText(
      'recurrent-series-donations',
      formatNumber(recurrent.average_series_donations, 1) + ' on average'
    );
    setText(
      'recurrent-series-amount',
      formatEuros(recurrent.average_series_amount) + ' on average'
    );
    setText(
      'recurrent-stopped',
      formatNumber(recurrent.stopped_series) +
        ' of ' +
        formatNumber(recurrent.series) +
        ' (' +
        formatPercentage(recurrent.stopped_series, recurrent.series) +
        ')'
    );
    setText('recurrent-min-donations', recurrent.min_donations);
    setText(
      'recurrent-tolerance',
      formatNumber(100 * recurrent.interval_tolerance)
    );
    var cadenceRows = [];
    for (i = 0; i < recurrent.by_cadence.length; i++) {
      var cadence = recurrent.by_cadence[i];
      cadenceRows.push([
        cadence.label,
        formatNumber(cadence.donors),
        formatNumber(cadence.donations),
        formatEuros(cadence.amount),
      ]);
    }
    fillTable('recurrent-cadence-table', cadenceRows);

    // Amount distribution
    var bucketLabels = [];
    var bucketCounts = [];
    for (i = 0; i < period.amount_distribution.length; i++) {
      bucketLabels.push(period.amount_distribution[i].label);
      bucketCounts.push(period.amount_distribution[i].count);
    }
    columnChart(
      'amount-distribution-chart',
      bucketLabels,
      [
        {
          name: 'Donations',
          data: bucketCounts,
          color: DONATIONS_COLOR,
        },
      ],
      {
        xAxisTitle: 'Donation amount',
        yAxisTitle: 'Number of donations',
        tooltip: function () {
          var point = tooltipPoints(this)[0];
          var bucket = period.amount_distribution[point.index];
          return (
            tooltipCategory(point) +
            '<br><b>' +
            formatNumber(bucket.count) +
            ' donations</b> (' +
            formatPercentage(bucket.count, period.count) +
            ')<br>' +
            formatEuros(bucket.amount) +
            ' in total'
          );
        },
      }
    );

    // Donation requests
    document.getElementById('requests-data-incomplete').style.display =
      period.requests_data_incomplete ? '' : 'none';
    var before = period.requests_before_donation;
    setText(
      'requests-before-included',
      formatNumber(before.donations_included) +
        ' of ' +
        formatNumber(before.donations_total)
    );
    var rows = [];
    for (i = 0; i < before.by_type.length; i++) {
      var t = before.by_type[i];
      rows.push([
        t.label,
        formatNumber(t.donations_with_requests) +
          ' (' +
          formatPercentage(
            t.donations_with_requests,
            before.donations_included
          ) +
          ')',
        formatNumber(t.average_requests, 1),
      ]);
    }
    fillTable('requests-before-table', rows);

    var conversionDays = document.getElementsByClassName(
      'request-conversion-days'
    );
    for (i = 0; i < conversionDays.length; i++) {
      conversionDays[i].textContent = period.request_conversion_days;
    }
    document.getElementById('request-conversion-incomplete').style.display =
      period.request_conversion_incomplete ? '' : 'none';
    rows = [];
    for (i = 0; i < period.request_conversion.length; i++) {
      var c = period.request_conversion[i];
      rows.push([
        c.label,
        formatNumber(c.requests),
        formatNumber(c.converted_requests) +
          ' (' +
          formatPercentage(c.converted_requests, c.requests) +
          ')',
        formatNumber(c.users),
        formatNumber(c.converted_users) +
          ' (' +
          formatPercentage(c.converted_users, c.users) +
          ')',
      ]);
    }
    fillTable('request-conversion-table', rows);
  };

  var errorElement = document.getElementById('donations-error');
  var startInput = document.getElementById('donations-start');
  var endInput = document.getElementById('donations-end');
  var monthlyData = null;

  var selectedMonthlyMeasure = function () {
    var checked = document.querySelector(
      'input[name="monthly-donations-measure"]:checked'
    );
    return checked ? checked.value : 'amount';
  };

  var loadDonations = function (includeYearly) {
    var params = {};
    if (startInput.value) {
      params.start = startInput.value;
    }
    if (endInput.value) {
      params.end = endInput.value;
    }
    errorElement.style.display = 'none';
    $.get(donationsForm.dataset.url, params, function (d) {
      updateSummary('daily-donations', d.daily);
      drawDailyChart(d.daily);
      updateSummary('monthly-donations', d.monthly);
      monthlyData = d.monthly;
      drawMonthlyBySourceChart(monthlyData, selectedMonthlyMeasure());
      updatePeriod(d.period);
      if (includeYearly) {
        var total = 0;
        for (var i = 0; i < d.yearly.data.length; i++) {
          total += d.yearly.data[i].amount;
        }
        setText('yearly-donations-total', formatEuros(total));
        drawYearlyChart(d.yearly);
      }
    }).fail(function (xhr) {
      var message = 'Could not load donations data';
      if (xhr.responseJSON && xhr.responseJSON.error) {
        message += ': ' + xhr.responseJSON.error;
      }
      errorElement.textContent = message;
      errorElement.style.display = '';
    });
  };

  var measureInputs = document.querySelectorAll(
    'input[name="monthly-donations-measure"]'
  );
  for (var m = 0; m < measureInputs.length; m++) {
    measureInputs[m].addEventListener('change', function () {
      if (monthlyData !== null) {
        drawMonthlyBySourceChart(monthlyData, selectedMonthlyMeasure());
      }
    });
  }
  donationsForm.addEventListener('submit', function (event) {
    event.preventDefault();
    loadDonations(false);
  });
  document
    .getElementById('donations-reset')
    .addEventListener('click', function () {
      startInput.value = '';
      endInput.value = '';
      loadDonations(false);
    });
  $(document).ready(function () {
    loadDonations(true);
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
