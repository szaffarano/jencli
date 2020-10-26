from io import StringIO
from click import Path
from click import command
from click import echo
from click import group
from click import make_pass_decorator
from click import option
from click import pass_context
from click import style as s

import jenkins
import json
import sys
import io
import re

from datetime import datetime


# A test case has the following properties:
#   'testActions', 'age', 'className', 'duration', 'errorDetails',
#   'errorStackTrace', 'failedSince', 'name', 'skipped', 'skippedMessage',
#   'status', 'stderr', 'stdout'
#
# Remove the ones that aren't relevant.
CASE_SKIP_FIELDS = ['testActions', 'errorStackTrace', 'stderr',
                    'stdout', 'duration', 'failedSince', 'skipped', 'skippedMessage']

# Same for health report
HEALTH_SKIP_FIELDS = ['iconClassName', 'iconUrl']

CONTEXT_SETTINGS = dict(
    help_option_names=['-h', '--help'],
    ignore_unknown_options=False
)


@group(context_settings=CONTEXT_SETTINGS)
@option('-U', '--url', metavar='<url>', required=True,
        envvar='JENKINS_URL',
        help='Jenkins url.')
@option('-u', '--user', metavar='<username>', required=True,
        envvar='JENKINS_USERNAME',
        help='Jenkins username.')
@option('-t', '--token', metavar='<token>', required=True,
        envvar='JENKINS_TOKEN',
        help='Jenkins access token.')
@pass_context
def cli(ctx, url, user, token):
    ctx.ensure_object(dict)
    ctx.obj['server'] = jenkins.Jenkins(url, username=user, password=token)
    pass


@cli.command('info')
@option('-j', '--jobname', metavar='<jenkins job name>', required=True,
        help='Jenkins job name.')
@option('-n', '--jobnumber', metavar='<jenkins job number>', default=0,
        help='Jenkins job number, default latest job.')
@option('-o', '--output', metavar='<output file>',
        help='Output file or stdout by default.')
@option('-v', '--verbose', is_flag=True, default=False)
@option('-F', '--findflakes', is_flag=True, default=False)
@pass_context
def info(ctx, jobname, jobnumber, output, verbose, findflakes):
    server = ctx.obj['server']

    projectReport = {
        'job': jobname
    }

    try:
        info = server.get_job_info(jobname)
    except jenkins.JenkinsException:
        message = sys.exc_info()[1]
        echo(f'Error: {s(str(message), fg="red", bold="true")}')
        sys.exit(1)

    if jobnumber == 0:
        jobnumber = info.get('lastCompletedBuild', {}).get("number")

    build = buildInfo(server, jobname, jobnumber)

    projectReport['build'] = extractBuildInfo(build)

    healthReport = []
    for hr in info.get('healthReport', {}):
        healthReport.append(cleanup(hr, HEALTH_SKIP_FIELDS))

    projectReport['healthReport'] = healthReport

    testReport = server.get_build_test_report(jobname, jobnumber)
    if testReport is not None:
        projectReport['passTestsCount'] = testReport.get('passCount', 'N/A')
        projectReport['failTestsCount'] = testReport.get('failCount', 'N/A')
        projectReport['skipTestsCount'] = testReport.get('skipCount', 'N/A')
        projectReport['testReportLink'] = f'{build.get("url")}testReport'

        if testReport.get('failCount', 0) > 0:
            failedCases = projectReport.setdefault('failedCases', [])
            for suite in testReport.get('suites'):
                failedCases += [
                    cleanup(case, CASE_SKIP_FIELDS) for case in
                    filter(lambda c: c.get('status') in [
                           'REGRESSION', 'FAILED'], suite.get('cases'))
                ]

    if findflakes:
        flakes = findFlakesInLog(
            server.get_build_console_output(jobname, jobnumber))
        if len(flakes) > 0:
            projectReport.setdefault("flakes", flakes)

    jsonReport = json.dumps(projectReport, indent=2)
    if output is not None:
        with open(output, 'w+') as f:
            f.write(jsonReport)
    else:
        print(jsonReport)


def buildInfo(server, jobName, jobNumber):
    return server.get_build_info(jobName, jobNumber, depth=0)


def toDate(timestamp):
    if timestamp != 0:
        return datetime.fromtimestamp(timestamp/1000).strftime('%b %d %Y %H:%M:%S')
    return 'N/A'


def cleanup(case, fields):
    for prop in fields:
        if prop in case.keys():
            case.pop(prop)

    return case


def extractBuildInfo(build):
    return {
        'date': toDate(build.get('timestamp', 0)),
        'url':  build.get('url'),
        'result':  build.get('result')
    }


def findFlakesInLog(log):
    FLAKES_START = re.compile('.*\[WARNING\]\s(Flakes:)')
    FLAKES_END = re.compile('.*\[WARNING\]\sTests\srun:(.*)')
    FLAKY_TEST = re.compile('.*\[WARNING\]\s(.*)')

    flakesFound = False
    flakes = []
    for line in io.StringIO(log).readlines():
        line = line.replace('\n', '')

        if flakesFound:
            if FLAKES_END.match(line) is not None:
                flakesFound = False
            else:
                m = FLAKY_TEST.match(line)
                if m is not None:
                    flakes.append(m.groups()[0])
        elif FLAKES_START.match(line) is not None:
            if flakesFound:
                raise Exception("Already detected a flakes start.")
            flakesFound = True

    if flakesFound:
        raise Exception("Inconsistent flakes report.")

    return flakes
