mysql -u root -e 'DROP DATABASE iTrust2'
mvn -f pom-data.xml clean process-test-classes

mvn clean test verify checkstyle:checkstyle

