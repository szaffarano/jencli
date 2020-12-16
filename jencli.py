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

from datetime import datetime, timedelta


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
        help='Jenkins build number, default latest job. It could be a number or one of the following expressions: latest, last_N, N..M, N..latest')
@option('-o', '--output', metavar='<output file>',
        help='Output file or stdout by default.')
@option('-F', '--findflakes', is_flag=True, default=False)
@pass_context
def info(ctx, jobname, buildnumber, output, findflakes):
    BUILD_NUMBER_PARSER = re.compile(
        '^last_(?P<last>\d+)$|^(?P<num>\d+)$|^(?P<latest>latest)$|^(?P<from>\d+)\.\.((?P<to>\d+)|latest)$')

    buildFrom = -1
    buildTo = -1
    server = ctx.obj['server']

    projectReport = {
        'job': jobname
    }

    parsedBuildNumber = BUILD_NUMBER_PARSER.search(buildnumber)
    if parsedBuildNumber is None:
        echo(s(f'Error: {buildnumber}: invalid format', fg="red"), err=True)
        sys.exit(1)

    try:
        jobInfo = server.get_job_info(jobname)
    except jenkins.JenkinsException:
        message = sys.exc_info()[1]
        echo(f'Error: {s(str(message), fg="red")}')
        sys.exit(1)

    if parsedBuildNumber.group('num') is not None:
        buildFrom = int(parsedBuildNumber.group('num'))
        buildTo = buildFrom
    elif parsedBuildNumber.group('last') is not None:
        buildTo = jobInfo.get('lastCompletedBuild', {}).get("number")
        buildFrom = buildTo - int(parsedBuildNumber.group('last')) + 1
    elif parsedBuildNumber.group('latest') is not None:
        buildFrom = jobInfo.get('lastCompletedBuild', {}).get("number")
        buildTo = buildFrom
    elif parsedBuildNumber.group('from') is not None:
        buildFrom = int(parsedBuildNumber.group('from'))
        if parsedBuildNumber.group('to'):
            buildTo = int(parsedBuildNumber.group('to'))
            if buildFrom > buildTo:
                echo(
                    s(f'Error: {buildnumber}: "to" must be greater than "from"', fg="red"), err=True)
                sys.exit(1)
        else:
            buildTo = jobInfo.get('lastCompletedBuild', {}).get("number")

    healthReport = []
    for hr in jobInfo.get('healthReport', {}):
        healthReport.append(cleanup(hr, HEALTH_FIELDS_TO_REMOVE))
    projectReport.setdefault('healthReport', healthReport)

    builds = projectReport.setdefault('builds', [])
    while buildTo >= buildFrom:
        report = buildReport(jobname, buildTo, findflakes, server)
        buildTo = buildTo - 1
        if report is not None:
            builds.append(report)

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
    FLAKES_END = re.compile('.*(\[ERROR\]|\[WARNING\])\sTests\srun:(.*)')
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
    try:
        build = server.get_build_info(jobName, buildNumber, depth=0)
    except jenkins.JenkinsException:
        message = sys.exc_info()[1]
        echo(f'Error: {s(str(message), fg="red")}', err=True)
        return None

    duration = timedelta(milliseconds=build.get('duration'))
    secs = duration.total_seconds() % (24 * 3600)
    hours = secs // 3600
    secs %= 3600
    mins = secs // 60
    secs %= 60

    report = {
        "number": buildNumber,
        'duration': f'{int(hours)}:{int(mins)}:{int(secs)}'
    }

    report.setdefault('info', extractBuildInfo(build))
    report.setdefault('name', build.get("displayName"))

    testReport = server.get_build_test_report(jobName, buildNumber)
    if testReport is not None:
        report.setdefault(
            'passTestsCount', testReport.get('passCount', 'N/A'))
        report.setdefault(
            'failTestsCount', testReport.get('failCount', 'N/A'))
        report.setdefault(
            'skipTestsCount', testReport.get('skipCount', 'N/A'))
        report.setdefault(
            'testReportLink', f'{build.get("url")}testReport')

        if testReport.get('failCount', 0) > 0:
            failedCases = report.setdefault('failedCases', [])
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
            report.setdefault("flakes", flakes)

    return report
