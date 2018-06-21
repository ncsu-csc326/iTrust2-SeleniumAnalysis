#!/usr/bin/env python


"""Run artifact tests and collect results with a focus on flakiness.

@author Eric Horton
@author Kai Presler-Marshall
"""


# Imports
from datetime import datetime
from itertools import chain
from pathlib import Path
from xml.etree import ElementTree
import logging
import numpy as np
import os
import pandas
import subprocess


# Constants
PROJECT_ROOT = Path.resolve(Path(__file__).absolute().parent)
ITRUST2 = PROJECT_ROOT / 'iTrust2'
TIMEOUT = 60 * 40  # 40 minutes in seconds
LOG = PROJECT_ROOT / 'log'
STATS_FILE = LOG / 'build_stats.csv'
FAILING_TESTS_FILE = LOG / 'failing_tests.csv'
FLAKY_TESTS_FILE = LOG / 'failing_tests.csv'
LOG_FORMAT = '%(asctime)-15s %(message)s'
EXECUTIONS = 30
MVN = 'mvn'
DF_COLUMNS = ['execution', 'classname', 'name', 'time', 'failed']
BUILD_COLUMNS = ['id', 'time']
TEST_CMD = [MVN + ' clean verify -DskipSurefireTests']
DROP_DB_CMD = ['mysql'+ ' -u' + ' root'+ ' -e' + " 'DROP DATABASE IF EXISTS iTrust2'"]
BUILD_DB_CMD = [MVN + ' -f ' + str(ITRUST2) + '/pom-data.xml clean process-test-classes']
CLEAN_CMD = [MVN + ' clean']

# Configure logging
Path.mkdir(LOG, exist_ok=True)
logging.basicConfig(format=LOG_FORMAT)
logger = logging.getLogger('flakiness-tests')
file_handler = logging.FileHandler(LOG / 'flakiness_tests.log')
file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
logger.addHandler(file_handler)
logger.setLevel(logging.INFO)


def run_tests(artifact):
    """Run an artifact's test cases.

    Parameters
    ----------
    artifact : Path
        Pathlib Path to the artifact directory.

    Returns
    -------
    DataFrame
        Pandas DataFrame with the columns `classname, name, failed`.
    """

    # Compute artifact stdout/stderr logfile names
    build_id = datetime.now().isoformat().replace(':','_');
    stdout_log = LOG / '{}.{}.stdout.log'.format(artifact.stem, build_id)
    stderr_log = LOG / '{}.{}.stderr.log'.format(artifact.stem, build_id)
	
    # Begin context with log files
    with open(stdout_log, 'wb+') as stdout, open(stderr_log, 'wb+') as stderr:

        # Drop database
        logger.info('Dropping database with `{}`'.format(DROP_DB_CMD))
        subprocess.run(DROP_DB_CMD, shell=True)

        logger.info('Rebuilding database with `{}`'.format(BUILD_DB_CMD))
        subprocess.run(BUILD_DB_CMD, shell=True);

        # Spawn test process. Pipe stdout and stderr to file.
        logger.info('Running `{}` for artifact {}'.format(TEST_CMD, artifact))
        logger.info('Stdout logged to {}'.format(stdout_log))
        logger.info('Stderr logged to {}'.format(stderr_log))

        start_time = datetime.now()
        proc = subprocess.Popen(
            args=TEST_CMD,
            cwd=artifact,
            stdout=stdout,
            stderr=stderr,
            shell=True
        )

        # Wait for process to finish. If a timeout occurs, terminate
        # the process early.
        try:

            proc.communicate(timeout=TIMEOUT)

        except subprocess.TimeoutExpired:

            logger.warning('Timeout Encountered... killing process')
            proc.kill()
            proc.communicate()

        finally:

            end_time = datetime.now()

        # Log finish
        logger.info('Tests finished with exit status {}.'.format(proc.returncode))

        # Scrape test results
        test_results = scrape_results(artifact, build_id)

        # Compute build stats
        build_time = end_time - start_time
        build_stats = pandas.DataFrame([[build_id, build_time]], columns=BUILD_COLUMNS)

        return test_results, build_stats


def scrape_results(artifact, execution):
    """Scrape the results of running artifact tests.

    Parameters
    ----------
    artifact : Path
        Pathlib Path to the artifact directory.
    execution : string
        String used to uniquely identify results from the test execution.

    Returns
    -------
    DataFrame
        Pandas DataFrame with the columns `classname, name, failed`.
    """

    # Compute surefire directory
    surefire_dir = artifact / 'target/surefire-reports'
    logger.info('Looking for XML reports in {}'.format(surefire_dir))

    # Compute failsafe directory
    failsafe_dir = artifact / 'target/failsafe-reports'
    logger.info('Looking for XML reports in {}'.format(failsafe_dir))

    # Load all test XML report files using file globs
    reports = list(chain(*(
        list(reports_dir.glob('TEST*.xml'))
        for reports_dir in (surefire_dir, failsafe_dir)
    )))
    logger.info('Found {} total reports'.format(len(reports)))

    # Map each report to a result set
    results = list(map(
        lambda report: ElementTree.parse(report).getroot()[1:],
        reports
    ))

    # Parse results as a pandas dataframe
    # Failure is a boolean, determined by if the testcase has a child whose
    # tag is `failure` or `error`.
    if len(results):
        df = pandas.DataFrame(
            np.array([
                [
                    execution,
                    testcase.attrib['classname'],
                    testcase.attrib['name'],
                    testcase.attrib['time'],
                    np.any(list(map(lambda e: e.tag == 'failure' or e.tag == 'error', testcase)))
                ]
                for result_set in results
                for testcase in result_set
            ]),
            columns=DF_COLUMNS
        )
    else:
        df = pandas.DataFrame(columns=DF_COLUMNS)

    # Log and return
    logger.info('Found {} total test cases'.format(len(df)))
    return df


def main():
    """Main function. Run experiment and collect data."""

    # Start
    logger.info('Starting new set of flakiness tests.')

    # Start empty results frames
    results = pandas.DataFrame([], columns=DF_COLUMNS)
    build_stats = pandas.DataFrame([], columns=BUILD_COLUMNS)

    # Clean before running tests
    logger.info('Cleaning build with `{}`'.format(CLEAN_CMD))
    subprocess.run(CLEAN_CMD, cwd=ITRUST2, shell=True)

    # Run tests
    for i in range(EXECUTIONS):

        logger.info('Starting execution {} of artifact {}.'.format(i + 1, ITRUST2.stem))
        execution_results, execution_stats = run_tests(ITRUST2)
        results = pandas.concat([results, execution_results])
        build_stats = pandas.concat([build_stats, execution_stats])

    # Get all failing test cases
    failing = results[results['failed'].astype('str') == 'True'][['execution', 'classname', 'name', 'time']]

    # Determine which tests are flaky, and how many executions failed
    def is_flaky(s):
        return (s.astype('str') == 'True').any() and not (s.astype('str') == 'True').all()

    def num_failing(s):
        return len(s[s.astype('str') == 'True'])

    flaky = results.drop(columns=['execution']).groupby(['classname', 'name'], as_index=False)['failed'].agg([
        is_flaky, num_failing
    ]).reset_index()

    # Subset to only the flaky tests
    flaky = flaky[flaky['is_flaky'].astype('str') == 'True'][['classname', 'name', 'num_failing']]

    # With print context
    context = pandas.option_context(
        'display.max_rows', None,
        'display.max_columns', None,
        'display.max_colwidth', 70,
        'expand_frame_repr', False,
        'justify', 'right'
    )
    with context:

        # Log build stats
        logger.info('Build Stats:\n' + str(build_stats) + '\n')
        build_stats.to_csv(STATS_FILE, index=False)

        logger.info('Average Build Time: {}'.format(build_stats['time'].mean()))
        logger.info('Build Time Standard Deviation: {}\n'.format(build_stats['time'].std()))

        # Log failing test cases, if any
        if len(failing):
            logger.info('Failing Test Cases:\n' + str(failing) + '\n')
            failing.to_csv(FAILING_TESTS_FILE, index=False)
        else:
            logger.info('No failing test cases.')

        # Log flaky test cases, if any
        if len(flaky):
            logger.info('Flaky Test Cases:\n' + str(flaky) + '\n')
            flaky.to_csv(FLAKY_TESTS_FILE, index=False)
        else:
            logger.info('No flaky test cases.')


# Invoke main if called directly
if __name__ == '__main__':
    main()
