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
  // Display charts with Downloads, Uploads and Registers
  $.get(usersDataUrl, function(d){
      var new_users_active = [];
      var new_users_inactive = [];
      for (var i=0 ; i<d.new_users.length; i++) {
        if (d.new_users[i]['is_active']){
          new_users_active.push([
              new Date(d.new_users[i]['day']).getTime(),
              d.new_users[i]['id__count']
          ])
        } else {
           new_users_inactive.push([
              new Date(d.new_users[i]['day']).getTime(),
              d.new_users[i]['id__count']
          ])
        }
      }
      new_users_active.sort(function(a, b) { return a[0] - b[0];});
      new_users_inactive.sort(function(a, b) { return a[0] - b[0];});
      Highcharts.chart($('.users')[0], {
          title:{
              text:''
          },
          series: [
          {
            name: "Active users",
            data: new_users_active
          },
          {
            name: "Non active users",
            data: new_users_inactive
          }],
          xAxis: {
            type: 'datetime',
            tickInterval: 24 * 3600 * 1000, // one day
            tickWidth: 0,
            gridLineWidth: 1,
            labels: {
                align: 'left',
                x: 3,
                y: -3
            },
        },
        yAxis: {
            title: {
              text: 'Users'
            }
          },
      });
  });
  $.get(soundsDataUrl, function(d){
      var new_sounds = [];
      for (var i=0 ; i<d.new_sounds.length; i++) {
          new_sounds.push([
              new Date(d.new_sounds[i]['day']).getTime(),
              d.new_sounds[i]['id__count']
          ])
      }
      new_sounds.sort(function(a, b) { return a[0] - b[0];});
      var new_sounds_mod = [];
      for (var i=0 ; i<d.new_sounds_mod.length; i++) {
          new_sounds_mod.push([
              new Date(d.new_sounds_mod[i]['day']).getTime(),
              d.new_sounds_mod[i]['id__count']
          ])
      }
      new_sounds_mod.sort(function(a, b) { return a[0] - b[0];});
      Highcharts.chart($('.uploads')[0], {
          title:{
              text:''
          },
          series: [
          {
            name: "New Sound",
            data: new_sounds
          },
          {
            name: "Moderated Sound",
            data: new_sounds_mod
          }],
          xAxis: {
            type: 'datetime',
            tickInterval: 24 * 3600 * 1000, // one day
            tickWidth: 0,
            gridLineWidth: 1,
            labels: {
                align: 'left',
                x: 3,
                y: -3
            },
        },
        yAxis: {
            title: {
              text: 'Sounds'
            }
          },
      });
  });
  $.get(downloadsDataUrl, function(d){
      var downloads_data = [];
      for (var i=0 ; i<d.new_downloads_sound.length; i++) {
          downloads_data.push([
              new Date(d.new_downloads_sound[i]['day']).getTime(),
              d.new_downloads_sound[i]['id__count']
          ])
      }
      downloads_data.sort(function(a, b) { return a[0] - b[0];});
      var downloads_data_pack = [];
      for (var i=0 ; i<d.new_downloads_pack.length; i++) {
          downloads_data_pack.push([
              new Date(d.new_downloads_pack[i]['day']).getTime(),
              d.new_downloads_pack[i]['id__count']
          ])
      }
      downloads_data_pack.sort(function(a, b) { return a[0] - b[0];});
      Highcharts.chart($('.downloads')[0], {
          title:{
              text:''
          },
          series: [
          {
            name: "Download Pack",
            data: downloads_data_pack
          },
          {
            name: "Download Sound",
            data: downloads_data
          }],
          xAxis: {
            type: 'datetime',
            tickInterval: 24 * 3600 * 1000, // one day
            tickWidth: 0,
            gridLineWidth: 1,
            labels: {
                align: 'left',
                x: 3,
                y: -3
            },
          },
          yAxis: {
            title: {
              text: 'Downloads'
            }
          },
      });
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
      var sound_downloads = [];
      for (var i=0 ; i<d.sound_downloads.length; i++) {
          sound_downloads.push([
              new Date(d.sound_downloads[i]['week']).getTime(),
              d.sound_downloads[i]['amount__sum']
          ])
      }
      sound_downloads.sort(function(a, b) { return a[0] - b[0];});
      var pack_downloads = [];
      for (var i=0 ; i<d.pack_downloads.length; i++) {
          pack_downloads.push([
              new Date(d.pack_downloads[i]['week']).getTime(),
              d.pack_downloads[i]['amount__sum']
          ])
      }
      pack_downloads.sort(function(a, b) { return a[0] - b[0];});
      var sounds = [];
      for (var i=0 ; i<d.sounds.length; i++) {
          sounds.push([
              new Date(d.sounds[i]['week']).getTime(),
              d.sounds[i]['amount_sum']
          ])
      }
      sounds.sort(function(a, b) { return a[0] - b[0];});
      var posts = [];
      for (var i=0 ; i<d.posts.length; i++) {
          posts.push([
              new Date(d.posts[i]['week']).getTime(),
              d.posts[i]['amount_sum']
          ])
      }
      posts.sort(function(a, b) { return a[0] - b[0];});
      var rate = [];
      for (var i=0 ; i<d.rate.length; i++) {
          rate.push([
              new Date(d.rate[i]['week']).getTime(),
              d.rate[i]['amount_sum']
          ])
      }
      rate.sort(function(a, b) { return a[0] - b[0];});
      var comments = [];
      for (var i=0 ; i<d.comments.length; i++) {
          rate.push([
              new Date(d.comments[i]['week']).getTime(),
              d.comments[i]['amount_sum']
          ])
      }
      comments.sort(function(a, b) { return a[0] - b[0];});
      Highcharts.chart($('.active-users')[0], {
          title:{
              text:''
          },
          series: [
          {
            name: "Sound Downloads",
            data: sound_downloads
          },
          {
            name: "Pack Downloads",
            data: pack_downloads
          },
          {
            name: "Comments",
            data: comments
          },
          {
            name: "Posts",
            data: posts
          },
          {
            name: "Rates",
            data: rate
          },
          {
            name: "Sounds Upload",
            data: sounds
          }],
          yAxis: {
            title: {
              text: 'Users'
            }
          },
          xAxis: {
            type: 'datetime',
            tickInterval: 7 * 24 * 3600 * 1000, // one week
            tickWidth: 0,
            gridLineWidth: 1,
            labels: {
                align: 'left',
                x: 3,
                y: -3
            },
        },
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

