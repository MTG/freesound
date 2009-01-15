-- on post creation, increment counters for user, thread and post
-- also set the "last_post_id" on the forum and thread
CREATE OR REPLACE FUNCTION forum_post_insert() RETURNS TRIGGER AS
$BODY$
DECLARE
BEGIN
    UPDATE forum_thread SET last_post_id = NEW.id, num_posts = num_posts + 1 WHERE forum_thread.id = NEW.thread_id;
    UPDATE forum_forum  SET last_post_id = NEW.id, num_posts = num_posts + 1 WHERE forum_forum.id = (SELECT forum_id FROM forum_thread WHERE forum_thread.id = NEW.thread_id);
    UPDATE accounts_profile SET num_posts = num_posts + 1 WHERE user_id = NEW.author_id;
    RETURN NEW;
END;
$BODY$
LANGUAGE plpgsql;
DROP TRIGGER forum_post_insert ON forum_post;
CREATE TRIGGER forum_post_insert AFTER INSERT ON forum_post FOR EACH ROW EXECUTE PROCEDURE forum_post_insert();

-- on post deletion, decrement counters for user, thread and post
-- ignore the "last post" link.
CREATE OR REPLACE FUNCTION forum_post_delete() RETURNS TRIGGER AS
$BODY$
DECLARE
BEGIN
    UPDATE forum_thread SET num_posts = num_posts - 1 WHERE forum_thread.id = OLD.thread_id AND num_posts > 0;
    UPDATE forum_forum  SET num_posts = num_posts - 1 WHERE forum_forum.id = (SELECT forum_id FROM forum_thread WHERE forum_thread.id = OLD.thread_id) AND num_posts > 0;
    UPDATE accounts_profile SET num_posts = num_posts - 1 WHERE user_id = OLD.author_id AND num_posts > 0;
    RETURN NEW;
END;
$BODY$
LANGUAGE plpgsql;
DROP TRIGGER forum_post_delete ON forum_post;
CREATE TRIGGER forum_post_delete AFTER DELETE ON forum_post FOR EACH ROW EXECUTE PROCEDURE forum_post_delete();

-- posts will never be changed from thread, so we don't need an update trigger for them

-- on thread insert, increment thread-counter for forum
CREATE OR REPLACE FUNCTION forum_thread_insert() RETURNS TRIGGER AS
$BODY$
DECLARE
BEGIN
    UPDATE forum_forum  SET num_threads = num_threads + 1 WHERE forum_forum.id = NEW.forum_id;
    RETURN NEW;
END;
$BODY$
LANGUAGE plpgsql;
DROP TRIGGER forum_thread_insert ON forum_thread;
CREATE TRIGGER forum_thread_insert AFTER INSERT ON forum_thread FOR EACH ROW EXECUTE PROCEDURE forum_thread_insert();

-- on thread delete, decrement thread-counter for forum
CREATE OR REPLACE FUNCTION forum_thread_delete() RETURNS TRIGGER AS
$BODY$
DECLARE
BEGIN
    UPDATE forum_forum  SET num_threads = num_threads - 1 WHERE forum_forum.id = OLD.forum_id WHERE num_threads > 0;
    RETURN NEW;
END;
$BODY$
LANGUAGE plpgsql;
DROP TRIGGER forum_thread_delete ON forum_thread;
CREATE TRIGGER forum_thread_delete AFTER DELETE ON forum_thread FOR EACH ROW EXECUTE PROCEDURE forum_thread_delete();

-- on thread update, check the forum_id. If it has changed, update counts!
-- careful with deadlocks, see
-- http://www.depesz.com/index.php/2007/09/12/objects-in-categories-counters-with-triggers/
CREATE OR REPLACE FUNCTION forum_thread_update() RETURNS TRIGGER AS
$BODY$
DECLARE
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
$BODY$
LANGUAGE 'plpgsql';
DROP TRIGGER forum_thread_update ON forum_thread;
CREATE TRIGGER forum_thread_update AFTER UPDATE ON forum_thread FOR EACH ROW EXECUTE PROCEDURE forum_thread_update();

-- on sound update, increment the counters for the sound's user
-- if moderation and processing is ok, increment
-- if not, decrement
-- ok+pe -> ok+ok >>> increment
-- ok+ok -> ok+pe >>> decrement
CREATE OR REPLACE FUNCTION sounds_sound_update() RETURNS TRIGGER AS
$BODY$
DECLARE
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
$BODY$
LANGUAGE 'plpgsql';
DROP TRIGGER sounds_sound_update ON sounds_sound;
CREATE TRIGGER sounds_sound_update AFTER UPDATE ON sounds_sound FOR EACH ROW EXECUTE PROCEDURE sounds_sound_update();

-- on sound delete, decrement sound count for user
CREATE OR REPLACE FUNCTION sounds_sound_delete() RETURNS TRIGGER AS
$BODY$
DECLARE
BEGIN
    UPDATE accounts_profile SET num_sounds = num_sounds - 1 WHERE user_id = OLD.user_id AND num_sounds > 0;
    RETURN NEW;
END;
$BODY$
LANGUAGE plpgsql;
DROP TRIGGER forum_post_delete ON forum_post;
CREATE TRIGGER forum_post_delete AFTER DELETE ON forum_post FOR EACH ROW EXECUTE PROCEDURE forum_post_delete();