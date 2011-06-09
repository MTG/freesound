PSQL=psql -h localhost -U freesoundpg freesound 


help:
	# Setting up the environment
	# --------------------------
	#
	# Create an appropiate 'local_settings.py' (see example file).
	#
	# Having a '~/.my.cnf' file will probably make easier to run 'mysql'.
	#
	# Having a '~/.pgpass' file will probably make easier to run 'psql'.
	#
	#    localhost:*:freesound:freesoundpg:<your_password>
	#
	# make setup
	#
	# 		Creates a new PostgreSQL db with appropiate permissions.
	# 		When asked if should create a new Django superuser, answer 'no'.
	#
	# make clean
	#
	# 		Removes all .sql files created on previous runs.
	#
	# make destroy
	#
	#		CAUTION! Destroys the PosgreSQL database
	#
	#
	# Migration process
	# -----------------
	#
	# make step1
	#
	# make show_duplicates
	#
	# 		Shows duplicated users. 
	#
	# Remove manually all duplicate users running:
	#
	# 		make deleteuser USERID=666
	#
	# To avoid those users being included in the next import, add to
	#
	#  		local_settings.CUSTOM_BANNED_USERS (temporary)
	#  		or users.BANNED_USER_IDS (permanent).
	#
	# make step2

clean:
	rm -f *.pyc *.sql *.sql.gz

destroy:
	sudo -u postgres dropdb freesound
	sudo -u postgres dropuser freesoundpg

setup:
	# You must create the Postgres user with superadmin rights. This version
	# of the scripts make use of the restricted 'COPY FROM <file>'.
	#
	sudo -u postgres createuser -SRD -P freesoundpg
	sudo -u postgres createdb -O freesoundpg freesound
	sudo -u postgres createlang plpgsql freesound
	### Running: manage.py syncdb
	### Don't create a superuser.
	../../manage.py syncdb


deleteuser:
	echo 'DELETE from auth_user WHERE id=${USERID} ;' | ${PSQL}


step1:
	./users.py
	${PSQL} < users.sql
	gzip users.sql
	#
	# Remove all duplicated usernames before running 'make step2'.
	


SQL_DUPLICATES = 'SELECT id,username,email FROM auth_user \
WHERE UPPER(username) IN ( \
	SELECT upper(username) as u FROM auth_user \
	GROUP BY u HAVING (COUNT(*) > 1) \
) ORDER BY username ;'
show_duplicates:
	echo ${SQL_DUPLICATES} | ${PSQL}


step2:
	./users_reindex.py
	${PSQL} < users_reindex.sql
	./profiles.py
	${PSQL} < profiles.sql
	gzip profiles.sql 
	./packs.py
	${PSQL} < packs.sql
	./sounds.py
	${PSQL} < sounds.sql
	./tags.py
	${PSQL} < tags.sql
	${PSQL} < tags_fs1tag.sql
	${PSQL} < tags_taggeditem.sql
	./geotags.py
	${PSQL} < geotags.sql
	./messages.py
	${PSQL} < messages_body.sql
	${PSQL} < messages.sql
	./remixes.py
	${PSQL} < remixes.sql
	./forums.py
	${PSQL} < forums.sql
	./threads.py
	${PSQL} < threads.sql
	./posts.py
	${PSQL} < posts.sql
	./comments.py
	${PSQL} < comments.sql
	./votes.py
	${PSQL} < votes.sql
	./downloads.py
	gzip downloads.sql
	gunzip -c downloads.sql.gz | ${PSQL}
	# Two errors appear during DROP CONSTRAIN because the named relations
	# do not exist yet. Probably those two sentences are not needed, but
	# won't remove without verifying it.
	#
	#		ERROR:  constraint "sounds_download_pkey" of relation 
	#		"sounds_download" does not exist
	#		ERROR:  constraint "sounds_download_user_id_key" of relation 
	#		"sounds_download" does not exist
	#
	${PSQL} < ../../_sql/nightingale_sql_setup.sql
	${PSQL} < ../../_sql/nightingale_triggers.sql
	#
	#
	#
	# Next steps:
	#
	#  - Run script to determine where to start processing again.
	#  		./manage.py post_conversion
	#
	#  - Run script to do pending processing.
	#  		./manage.py gm_client_processing --pending 
	#

