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
CASE_FIELDS_TO_REMOVE = ['testActions', 'errorStackTrace', 'stderr',
                    'stdout', 'duration', 'failedSince', 'skipped', 'skippedMessage']

# Same for health report
HEALTH_FIELDS_TO_REMOVE = ['iconClassName', 'iconUrl']

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
        envvar='JENKINS_TOKEN', prompt=True,
        help='Jenkins access token.')
@pass_context
def cli(ctx, url, user, token):
    ctx.ensure_object(dict)
    ctx.obj['server'] = jenkins.Jenkins(url, username=user, password=token)
    pass


@cli.command('info')
@option('-j', '--jobname', metavar='<job name>', required=True,
        help='Jenkins job name.')
@option('-b', '--buildnumber', metavar='<build number>', default='latest',
        help='Jenkins build number, default latest job. It could be a number or a keyword: latest, last_N')
@option('-o', '--output', metavar='<output file>',
        help='Output file or stdout by default.')
@option('-F', '--findflakes', is_flag=True, default=False)
@pass_context
def info(ctx, jobname, buildnumber, output, findflakes):
    BUILD_NUMBER_PARSER = re.compile("^last_(?P<last>\d+)$|^(?P<num>\d+)$|^(?P<latest>latest)$")

    server = ctx.obj['server']
    buildsCount = -1

    projectReport = {
        'job': jobname
    }

    parsedBuildNumber = BUILD_NUMBER_PARSER.search(buildnumber)
    if parsedBuildNumber is None:
        echo(s(f'Error: {buildnumber}: invalid format', fg="red", bold="true"))
        sys.exit(1)
    elif parsedBuildNumber.group('num') is not None:
        buildnumber = int(parsedBuildNumber.group('num'))
    elif parsedBuildNumber.group('last') is not None:
        buildsCount = int(parsedBuildNumber.group('last'))
    elif parsedBuildNumber.group('latest') is not None:
        buildsCount = 1

    try:
        jobInfo = server.get_job_info(jobname)
    except jenkins.JenkinsException:
        message = sys.exc_info()[1]
        echo(f'Error: {s(str(message), fg="red", bold="true")}')
        sys.exit(1)

    healthReport = []
    for hr in jobInfo.get('healthReport', {}):
        healthReport.append(cleanup(hr, HEALTH_FIELDS_TO_REMOVE))
    projectReport.setdefault('healthReport', healthReport)

    builds = projectReport.setdefault('builds', [])
    if buildsCount != -1:
        buildnumber = jobInfo.get('lastCompletedBuild', {}).get("number")
        while buildsCount > 0:
            builds.append(buildReport(
                jobname, buildnumber - buildsCount + 1, findflakes, server))
            buildsCount = buildsCount - 1
    else:
        builds.append(
            buildReport(jobname, buildnumber, findflakes, server)
        )

    jsonReport = json.dumps(projectReport, indent=2)
    if output is not None:
        with open(output, 'w+') as f:
            f.write(jsonReport)
    else:
        print(jsonReport)


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
    FLAKES_END = re.compile('.*\[ERROR|WARNING\]\sTests\srun:(.*)')
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


def buildReport(jobName, buildNumber, findFlakes, server):
    buildReport = {
        "number": buildNumber
    }

    build = server.get_build_info(jobName, buildNumber, depth=0)

    buildReport.setdefault('info', extractBuildInfo(build))
    buildReport.setdefault('name', build.get("displayName"))

    testReport = server.get_build_test_report(jobName, buildNumber)
    if testReport is not None:
        buildReport.setdefault('passTestsCount', testReport.get('passCount', 'N/A'))
        buildReport.setdefault('failTestsCount', testReport.get('failCount', 'N/A'))
        buildReport.setdefault('skipTestsCount', testReport.get('skipCount', 'N/A'))
        buildReport.setdefault('testReportLink', f'{build.get("url")}testReport')

        if testReport.get('failCount', 0) > 0:
            failedCases = buildReport.setdefault('failedCases', [])
            for suite in testReport.get('suites'):
                failedCases += [
                    cleanup(case, CASE_FIELDS_TO_REMOVE) for case in
                    filter(lambda c: c.get('status') in [
                           'REGRESSION', 'FAILED'], suite.get('cases'))
                ]

    if findFlakes:
        flakes = findFlakesInLog(
            server.get_build_console_output(jobName, buildNumber))
        if len(flakes) > 0:
            buildReport.setdefault("flakes", flakes)

    return buildReport
