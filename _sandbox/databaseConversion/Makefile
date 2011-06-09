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
	#  make step1
	#
	#  Remove manually all duplicate users. Add them to 
	#  		local_settings.CUSTOM_BANNED_USERS (temporary)
	#  		or users.BANNED_USER_IDS (permanent).
	#
	#  make step2

clean:
	rm -f *.pyc *.sql

destroy:
	sudo -u postgres dropdb freesound
	sudo -u postgres dropuser freesoundpg

setup:
	# You must create the Postgres user with superadmin rights. This version
	# of the scripts make use of the restricted 'COPY FROM <file>'.
	#
	sudo -u postgres createuser -SRD -P freesoundpg
	sudo -u postgres createdb -O freesoundpg freesound
	### Running: manage.py syncdb
	### Don't create a superuser.
	../../manage.py syncdb



step1:
	./users.py
	$(PSQL) < users.sql
	#
	# Remove all duplicated usernames before running 'make step2'.
	
step2:
	./users_reindex.py
	$(PSQL) < users_reindex.sql
	./profiles.py
	$(PSQL) < profiles.sql
	./packs.py
	$(PSQL) < packs.sql
	./sounds.py
	$(PSQL) < sounds.sql
	./tags.py
	$(PSQL) < tags.sql
	./geotags.py
	$(PSQL) < geotags.sql
	./messages.py
	$(PSQL) < messages.sql
	$(PSQL) < messagesbody.sql
	./remixes.py
	$(PSQL) < remixes.sql
	./forums.py
	$(PSQL) < forums.sql
	./threads.py
	$(PSQL) < threads.sql
	#
	./posts.py
	$(PSQL) < posts.sql
	./comments.py
	$(PSQL) < comments.sql
	./votes.py
	$(PSQL) < votes.sql
	./downloads.py
	$(PSQL) < downloads.sql
	#
	$(PSQL) < ../../_sql/nightingale_sql_setup.sql
	$(PSQL) < ../../_sql/nightingale_triggers.sql
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

