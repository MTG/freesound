-- set correct last_post and num_posts for all threads
update forum_thread set last_post_id=t.latest_id, num_posts=t.num_posts from (
    select
        stats.thread_id,
        stats.num_posts,
        p.id as latest_id
    from forum_post as p
    inner join (
        select
            thread_id,
            max(created) as last_created,
            count(1) as num_posts
        from forum_post
        group by thread_id) as stats
    on p.created=stats.last_created and p.thread_id=stats.thread_id
) as t
where t.thread_id=forum_thread.id;

-- set correct last_post and num_posts for all forums
update forum_forum set last_post_id=t.latest_id, num_threads=t.num_threads, num_posts=t.num_posts from (
    select
        forum_id,
        count(1) as num_threads,
        sum(num_posts) as num_posts,
        max(last_post_id) as latest_id
    from forum_thread
    group by forum_id
) as t
where t.forum_id=forum_forum.id;

-- set correct num_sounds for all users
update accounts_profile set num_sounds=t.num_sounds
from (select user_id, count(*) as num_sounds from sounds_sound where moderation_state='OK' and processing_state='OK' group by user_id) as t
where t.user_id=accounts_profile.user_id;

-- set correct num_posts for all users
update accounts_profile set num_posts=t.num_posts
from (select author_id as user_id, count(*) as num_posts from forum_post group by author_id) as t
where t.user_id=accounts_profile.user_id;

-- update the rating for all sounds
update sounds_sound set avg_rating=t.avg_rating, num_ratings=t.num_ratings
from (
    select
        object_id as sound_id,
        avg(rating) as avg_rating,
        count(*) as num_ratings
    from ratings_rating
    where content_type_id=(
        select id
        from django_content_type
        where app_label='sounds' and model='sound'
    )
    group by object_id
) as t
where t.sound_id=sounds_sound.id;

-- correct num_comments for all sounds
update sounds_sound set num_comments=t.num_comments from (
    select
        object_id as sound_id,
        count(*) as num_comments
    from comments_comment
    where content_type_id=(
        select id
        from django_content_type
        where app_label='sounds' and model='sound'
    )
    group by object_id
) as t
where t.sound_id=sounds_sound.id;

-- correct number of downloads per sound
update sounds_sound set num_downloads=d.num_downloads from (
    select
        sound_id,
        count(1) as num_downloads
    from sounds_download
    where
        pack_id is null
    group by sound_id
) as d
where d.sound_id = sounds_sound.id;

-- correct number of downloads per pack
update sounds_pack set num_downloads=d.num_downloads
from (
    select
        pack_id,
        count(1) as num_downloads
    from sounds_download
    where
        sound_id is null
    group by pack_id
) as d
where d.pack_id = sounds_pack.id;

-- set has_old_license true only for users with uploaded sounds
update accounts_profile set has_old_license = (num_sounds > 0) ;
	
-- unqueness for downloads with null of either field
CREATE INDEX sounds_download_user_pack
    ON sounds_download
    USING btree
    (user_id, sound_id)
    WHERE pack_id IS NULL;
  
CREATE INDEX sounds_download_user_sound
    ON sounds_download
    USING btree
    (user_id, pack_id)
    WHERE sound_id IS NULL;

-- update site object
update django_site set domain = 'freesound.org', name = 'freesound.org';

vacuum analyze sounds_sound;
vacuum analyze sounds_pack;
vacuum analyze forum_thread;
vacuum analyze forum_forum;
vacuum analyze accounts_profile;
vacuum analyze sounds_sound;
