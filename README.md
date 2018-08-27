# iTrust2-SeleniumAnalysis

This is the source code for Wait Wait, an investigation into the effect of Selenium configuration
options on web UI test flakiness within iTrust2, NC State's software engineering teaching application.  We investigate the effect of hardware, driver, and wait strategy.  

This repository contains the Python script that we used to run and analyze the results, as well as iTrust2 itself.  The version of iTrust2 here is the "optimal configuration" that we arrived at -- Chrome maanged as a singleton with Angular waits.  Steps for trying other configurations are below.  

## Environment Configuration

Wait Wait needs a few basic things to run.

* Python 3.7 + Pip
* Java SE Development Kit (JDK) 1.8.x
* Maven 3.3.3
* MySQL 5.7 or MariaDB 10.2+
* Google Chrome 59+

Refer to instructions for individual artifacts for any additional setup needed.

Python dependencies can be installed with `pip3 install -r requirements.txt`. We recommend running
in a virtual environment.

Please note that for Jetty to run properly you must setup MySQL/MariaDB with a blank root password.

### iTrust2 Setup
iTrust2 requires a few minor setup steps as well:
* Copy `db.properties.template` to `db.properties` (no content needs to be changed, if using the blank root password)
* Copy `hibernate.properties.template` to `hibernate.properties` (no content needs to be changed, if using the blank root password)
* Copy `email.properties.template` to `email.properties` and add the credentials for a Gmail account.  Make sure to allow [insecure access](https://support.google.com/accounts/answer/6010255?hl=en) to your account.

Maven will handle downloading all of the dependencies required for the build, and the Python script (detailed below) will build the database required with test data.

## Replicating Configurations
Of course, iTrust2 can be modified to enable testing other configurations.  Most of the configuration lives within `SeleniumTest.java`.
  * To change the browser under test, modify `setup()` to create a different browser (HtmlUnit, PhantomJS, or Firefox).  Note that PhantomJS and HtmlUnit require an _older_ version of the `selenium-java` dependency (2.53.1 encouraged) and requires you to remove the `ngwebdriver` dependency.  Both are located in `pom.xml`.
  * To change the waiting approach used, modify `seleniumWait()`.  For "No Wait", this method can be empty.  For Thread Waits, add a call to `Thread.sleep()`.  We encourage a 5-second sleep time.  For Explicit Waits, modify the method to take in an `ExpectedConditions` telling Selenium what it should wait on.  We encourage that you tell it to wait for the visibility of the element that is being located directly below where the call to `seleniumWait()` is made.  Then, call `wait.until(yourCondition)`.
  * To no longer manage Chrome as a singleton, remove the `setUp()` and `tearDown()` methods from `ITRunner.java`.  Then, replace each call to `attemptLogout()` in the `*StepDefs.java` classes with a call to `super.setup()` to ensure that the browser is initialized.

## Running Experiments

Run experiments with `python[3] run_flakiness_tests.py`. Results of a single execution will
be output to a `log/` directory. We recommend saving the following files.

| File | Description |
| ---- | ----------- |
| flakiness_tests.log | Human readable log format containing execution results. |
| build_stats.csv | CSV file containing times for each test run. |
| failing_tests.csv | CSV file containing all test failures from all executions. |
| flaky_tests.csv | CSV file containing all tests which had at least one failure and at least one success. |
