------------------------------------------------------------------------------------------------------------------------------------------
-- on post creation, increment counters for user, thread and post
-- also set the "last_post_id" on the forum and thread
CREATE OR REPLACE FUNCTION forum_post_insert() RETURNS TRIGGER AS $BODY$
    BEGIN
        UPDATE forum_thread SET last_post_id = NEW.id, num_posts = num_posts + 1 WHERE forum_thread.id = NEW.thread_id;
        UPDATE forum_forum  SET last_post_id = NEW.id, num_posts = num_posts + 1 WHERE forum_forum.id = (SELECT forum_id FROM forum_thread WHERE forum_thread.id = NEW.thread_id);
        UPDATE accounts_profile SET num_posts = num_posts + 1 WHERE user_id = NEW.author_id;
        RETURN NEW;
    END;
$BODY$ LANGUAGE plpgsql;
DROP TRIGGER forum_post_insert ON forum_post;
CREATE TRIGGER forum_post_insert AFTER INSERT ON forum_post FOR EACH ROW EXECUTE PROCEDURE forum_post_insert();

------------------------------------------------------------------------------------------------------------------------------------------
-- this function updates a thread to contain the right "last post"
CREATE OR REPLACE FUNCTION update_thread_last_post(in input_thread_id integer) RETURNS void AS $BODY$
    BEGIN
        update forum_thread set last_post_id=p.last_post from (
            select fp.id as last_post
            from forum_post as fp
            where fp.thread_id=input_thread_id
            order by created desc
            limit 1) as p
        where forum_thread.id=input_thread_id;
    END;
$BODY$ LANGUAGE plpgsql;

------------------------------------------------------------------------------------------------------------------------------------------
-- this function updates a forum to contain the right "last post"
CREATE OR REPLACE FUNCTION update_forum_last_post(in input_forum_id integer) RETURNS void AS $BODY$
    BEGIN
        update forum_forum set last_post_id=t.last_post from (
            select ft.last_post_id as last_post
            from forum_thread as ft
            where
                ft.forum_id=input_forum_id and
                last_post_id is not null
            order by created desc
            limit 1) as t
        where forum_forum.id=input_forum_id;
    END;
$BODY$ LANGUAGE plpgsql;


------------------------------------------------------------------------------------------------------------------------------------------
-- on post deletion, decrement counters for user, thread and post
-- ignore the "last post" link.
CREATE OR REPLACE FUNCTION forum_post_delete() RETURNS TRIGGER AS $BODY$
    DECLARE
        thread_last_post_id INTEGER;
        thread_forum_id INTEGER;
    BEGIN
        SELECT last_post_id INTO thread_last_post_id FROM forum_thread WHERE forum_thread.id = OLD.thread_id;
        SELECT forum_id INTO thread_forum_id FROM forum_thread WHERE forum_thread.id = OLD.thread_id;
        IF thread_last_post_id = OLD.id THEN
            PERFORM update_thread_last_post(OLD.thread_id);
            PERFORM update_forum_last_post(thread_forum_id);
        END IF;
        UPDATE forum_thread SET num_posts = num_posts - 1 WHERE forum_thread.id = OLD.thread_id AND num_posts > 0;
        UPDATE forum_forum SET num_posts = num_posts - 1 WHERE forum_forum.id = thread_forum_id AND num_posts > 0;
        UPDATE accounts_profile SET num_posts = num_posts - 1 WHERE user_id = OLD.author_id AND num_posts > 0;
        RETURN NEW;
    END;
$BODY$ LANGUAGE plpgsql;
DROP TRIGGER forum_post_delete ON forum_post;
CREATE TRIGGER forum_post_delete AFTER DELETE ON forum_post FOR EACH ROW EXECUTE PROCEDURE forum_post_delete();

-- posts will never be changed from thread, so we don't need an update trigger for them

------------------------------------------------------------------------------------------------------------------------------------------
-- on thread insert, increment thread-counter for forum
CREATE OR REPLACE FUNCTION forum_thread_insert() RETURNS TRIGGER AS $BODY$
    BEGIN
        UPDATE forum_forum SET num_threads = num_threads + 1 WHERE forum_forum.id = NEW.forum_id;
        RETURN NEW;
    END;
$BODY$ LANGUAGE plpgsql;
DROP TRIGGER forum_thread_insert ON forum_thread;
CREATE TRIGGER forum_thread_insert AFTER INSERT ON forum_thread FOR EACH ROW EXECUTE PROCEDURE forum_thread_insert();

------------------------------------------------------------------------------------------------------------------------------------------
-- on thread delete, decrement thread-counter for forum
CREATE OR REPLACE FUNCTION forum_thread_delete() RETURNS TRIGGER AS $BODY$
    DECLARE
        forum_last_post_id INTEGER;
    BEGIN
        SELECT last_post_id INTO forum_last_post_id FROM forum_forum WHERE forum_forum.id = OLD.forum_id;
        IF forum_last_post_id = OLD.last_post_id THEN
            PERFORM update_forum_last_post(OLD.forum_id);
        END IF;
        UPDATE forum_forum SET num_threads = num_threads - 1 WHERE forum_forum.id = OLD.forum_id AND num_threads > 0;
        RETURN NEW;
    END;
$BODY$ LANGUAGE plpgsql;
DROP TRIGGER forum_thread_delete ON forum_thread;
CREATE TRIGGER forum_thread_delete AFTER DELETE ON forum_thread FOR EACH ROW EXECUTE PROCEDURE forum_thread_delete();

------------------------------------------------------------------------------------------------------------------------------------------
-- on thread update, check the forum_id. If it has changed, update counts!
-- careful with deadlocks, see
-- http://www.depesz.com/index.php/2007/09/12/objects-in-categories-counters-with-triggers/
CREATE OR REPLACE FUNCTION forum_thread_update() RETURNS TRIGGER AS $BODY$
    BEGIN
        IF NEW.forum_id = OLD.forum_id THEN
            RETURN NEW;
        END IF;
        IF NEW.forum_id < OLD.forum_id THEN
            UPDATE forum_forum SET num_threads = num_threads + 1 WHERE id = NEW.forum_id;
            UPDATE forum_forum SET num_threads = num_threads - 1 WHERE id = OLD.forum_id AND num_threads > 0;
        ELSE
            UPDATE forum_forum SET num_threads = num_threads - 1 WHERE id = OLD.forum_id AND num_threads > 0;
            UPDATE forum_forum SET num_threads = num_threads + 1 WHERE id = NEW.forum_id;
        END IF;
        RETURN NEW;
    END;
$BODY$ LANGUAGE 'plpgsql';
DROP TRIGGER forum_thread_update ON forum_thread;
CREATE TRIGGER forum_thread_update AFTER UPDATE ON forum_thread FOR EACH ROW EXECUTE PROCEDURE forum_thread_update();

------------------------------------------------------------------------------------------------------------------------------------------
-- on sound update, increment the counters for the sound's user
-- if moderation and processing is ok, increment
-- if not, decrement
-- ok+pe -> ok+ok >>> increment
-- ok+ok -> ok+pe >>> decrement
CREATE OR REPLACE FUNCTION sounds_sound_update() RETURNS TRIGGER AS $BODY$
    BEGIN
        IF NEW.moderation_state = OLD.moderation_state AND NEW.processing_state = OLD.processing_state THEN
            RETURN NEW;
        END IF;
        
        -- come from not all ok to all ok, increment!
        IF (OLD.moderation_state != 'OK' OR OLD.processing_state != 'OK') AND (NEW.moderation_state = 'OK' AND NEW.processing_state = 'OK') THEN
            UPDATE accounts_profile SET num_sounds = num_sounds + 1 WHERE user_id = NEW.user_id;
        END IF;
    
        -- come from all ok, go to not all ok
        IF (NEW.moderation_state != 'OK' OR NEW.processing_state != 'OK') AND (OLD.moderation_state = 'OK' AND OLD.processing_state = 'OK') THEN
            UPDATE accounts_profile SET num_sounds = num_sounds - 1 WHERE user_id = NEW.user_id AND num_sounds > 0;
        END IF;
    
        RETURN NEW;
    END;
$BODY$ LANGUAGE 'plpgsql';
DROP TRIGGER sounds_sound_update ON sounds_sound;
CREATE TRIGGER sounds_sound_update AFTER UPDATE ON sounds_sound FOR EACH ROW EXECUTE PROCEDURE sounds_sound_update();

------------------------------------------------------------------------------------------------------------------------------------------
-- on sound delete, decrement sound count for user
CREATE OR REPLACE FUNCTION sounds_sound_delete() RETURNS TRIGGER AS $BODY$
    BEGIN
        UPDATE accounts_profile SET num_sounds = num_sounds - 1 WHERE user_id = OLD.user_id AND num_sounds > 0;
        RETURN NEW;
    END;
$BODY$ LANGUAGE plpgsql;
DROP TRIGGER forum_post_delete ON forum_post;
CREATE TRIGGER forum_post_delete AFTER DELETE ON forum_post FOR EACH ROW EXECUTE PROCEDURE forum_post_delete();

------------------------------------------------------------------------------------------------------------------------------------------
-- on sound rating update
CREATE OR REPLACE FUNCTION sound_rating_update() RETURNS TRIGGER AS $BODY$
    DECLARE
        sound_content_type_id INTEGER;
    BEGIN
        SELECT id INTO sound_content_type_id FROM django_content_type WHERE app_label='sounds' AND model='sound';    
        IF sound_content_type_id = NEW.content_type_id THEN
           UPDATE sounds_sound SET avg_rating=(SELECT coalesce(avg(rating),0) FROM ratings_rating WHERE content_type_id=NEW.content_type_id AND object_id=NEW.object_id) WHERE sounds_sound.id=NEW.object_id;
        END IF;
        RETURN NEW;
    END;
$BODY$ LANGUAGE plpgsql;
DROP TRIGGER rating_post_update ON ratings_rating;
CREATE TRIGGER rating_post_update AFTER UPDATE ON ratings_rating FOR EACH ROW EXECUTE PROCEDURE sound_rating_update();

CREATE OR REPLACE FUNCTION sound_rating_insert() RETURNS TRIGGER AS $BODY$
    DECLARE
        sound_content_type_id INTEGER;
    BEGIN
        SELECT id INTO sound_content_type_id FROM django_content_type WHERE app_label='sounds' AND model='sound';    
        IF sound_content_type_id = NEW.content_type_id THEN
           UPDATE sounds_sound SET num_ratings=num_ratings+1, avg_rating=(SELECT coalesce(avg(rating),0) FROM ratings_rating WHERE content_type_id=NEW.content_type_id AND object_id=NEW.object_id) WHERE sounds_sound.id=NEW.object_id;
        END IF;
        RETURN NEW;
    END;
$BODY$ LANGUAGE plpgsql;
DROP TRIGGER rating_post_insert ON ratings_rating;
CREATE TRIGGER rating_post_insert AFTER INSERT ON ratings_rating FOR EACH ROW EXECUTE PROCEDURE sound_rating_insert();

CREATE OR REPLACE FUNCTION sound_rating_delete() RETURNS TRIGGER AS $BODY$
    DECLARE
        sound_content_type_id INTEGER;
    BEGIN
        SELECT id INTO sound_content_type_id FROM django_content_type WHERE app_label='sounds' AND model='sound';    
        IF sound_content_type_id = OLD.content_type_id THEN
           UPDATE sounds_sound SET num_ratings=num_ratings-1, avg_rating=(SELECT coalesce(avg(rating),0) FROM ratings_rating WHERE content_type_id=OLD.content_type_id AND object_id=OLD.object_id) WHERE sounds_sound.id=OLD.object_id;
        END IF;
        RETURN OLD;
    END;
$BODY$ LANGUAGE plpgsql;
DROP TRIGGER rating_post_delete ON ratings_rating;
CREATE TRIGGER rating_post_delete AFTER DELETE ON ratings_rating FOR EACH ROW EXECUTE PROCEDURE sound_rating_delete();

------------------------------------------------------------------------------------------------------------------------------------------
-- on downloads
CREATE OR REPLACE FUNCTION download_insert() RETURNS TRIGGER AS $BODY$
    BEGIN
        IF NEW.sound_id is null THEN
            UPDATE sounds_pack SET num_downloads=num_downloads+1 WHERE sounds_pack.id=NEW.pack_id;
        ELSE
            UPDATE sounds_sound SET num_downloads=num_downloads+1 WHERE sounds_sound.id=NEW.sound_id;
        END IF;
        RETURN NEW;
    END;
$BODY$ LANGUAGE plpgsql;
DROP TRIGGER download_post_insert ON sounds_download;
CREATE TRIGGER download_post_insert AFTER INSERT ON sounds_download FOR EACH ROW EXECUTE PROCEDURE download_insert();

CREATE OR REPLACE FUNCTION download_delete() RETURNS TRIGGER AS $BODY$
    BEGIN
        IF OLD.sound_id is null THEN
            UPDATE sounds_pack SET num_downloads=num_downloads-1 WHERE sounds_pack.id=OLD.pack_id;
        ELSE
            UPDATE sounds_sound SET num_downloads=num_downloads-1 WHERE sounds_sound.id=OLD.sound_id;
        END IF;
        RETURN OLD;
    END;
$BODY$ LANGUAGE plpgsql;
DROP TRIGGER download_post_delete ON sounds_download;
CREATE TRIGGER download_post_delete AFTER DELETE ON sounds_download FOR EACH ROW EXECUTE PROCEDURE download_delete();
