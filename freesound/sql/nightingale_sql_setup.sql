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