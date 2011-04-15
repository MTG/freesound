-- sounds
select ID, userID, replace(originalFilename, "\t", " "), dateAdded into outfile '/tmp/lsa_sound.txt' from audio_file;

-- packs
select ID, userID, replace(name, "\t", " "), date into outfile '/tmp/lsa_pack.txt' from audio_file_packs;

-- comments
select ID, userID, date into outfile '/tmp/lsa_comment.txt' from audio_file_comments;

-- tags
select id, replace(tag, "\t", " ") into outfile '/tmp/lsa_tag.txt' from tags;

-- users
select user_id, username into outfile '/tmp/lsa_user.txt' from phpbb_users where user_active = 1;

-- sound in pack
select ID, packID into outfile '/tmp/lsa_sound_pack.txt' from audio_file where packID is not null;

-- votes for file
select audioFileID, userID, vote, date into outfile '/tmp/lsa_sound_vote.txt' from audio_file_vote;

-- file downloads
select userID, audioFileID, date into outfile '/tmp/lsa_sound_download.txt' from audio_file_downloads where packID is null;

-- pack downloads
select userID, packID, date into outfile '/tmp/lsa_pack_download.txt' from audio_file_downloads where audioFileID is null;

-- sound tag
select userID, audioFileID, tagID, date into outfile '/tmp/lsa_sound_tag.txt' from audio_file_tag;