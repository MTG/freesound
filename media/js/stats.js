$( document ).ready(function() {

  $.get(totalsDataUrl, function(data){
    $('#total-users').html(data.total_users);
    $('#users-with-sounds').html(data.users_with_sounds);
    $('#total-donations').html(data.total_donations);
    $('#proj-donations').html((data.donations_last_month * 12).toFixed(2));
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
      displayHistogram('.donations', d.new_donations, {
        yText: 'Amount (€)',
        attrX: 'day',
        attrY: 'amount__sum',
        timeFormat: "%d %b",
        tickEvery: d3.timeWeek.every(1),
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

