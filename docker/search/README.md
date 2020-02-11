Solr maven template
===================

Alastair Porter, 2013

This sample POM provides a simple way to develop a Solr server and then
deploy it to a servlet container.

Development
-----------

To quickly set up a solr server, run

    mvn jetty:run-war

Access the solr server at http://localhost:8080

Solr configuration is in the `solr/` directory. Because the `solr.home`
variable is not set, Solr will default to this. If you want to change the
value of `solr.home` you can do it like this:

    mvn -Dsolr.solr.home=myhome jetty:run-war

Add custom Solr components to `src/main/java` as you would in any other
maven project. These will be compiled into the war file.

Deployment
----------

If you want to deploy to a servlet container, run

    mvn package

to create a war file in `target/`

When running in a servlet container you must configure the location
of `solr.home`. For Tomcat there are a few ways of doing this
(from http://wiki.apache.org/solr/SolrTomcat)

1) add

    JAVA_OPTS="$JAVA_OPTS -Dsolr.solr.home=/opt/solr/example"

to `$CATALINA_HOME/bin/setenv.sh` and deploy through `webapps/` as usual.

2) Configure a Context fragment

    cp tomcat-context.xml $CATALINA_HOME/conf/Catalina/localhost/solr.xml

and edit the `solr/home` `<Environment>` value. Note that you can set up
as many different contexts as you want with different `solr/home` values,
each using the same `solr.war`

Credits and License
-------------------
The majority of this pom file was copied from
http://netsuke.wordpress.com/2010/06/24/launching-solr-from-maven-for-rapid-development/, with an unknown license.
Any other changes are available under a BSD 2-clause license.

