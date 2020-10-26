# README

## Install

```sh
$ pip3 install https://github.com/szaffarano/jencli/archive/main.zip
```

## Usage

```sh
⟩ jencli -h
Usage: jencli [OPTIONS] COMMAND [ARGS]...

Options:
  -U, --url <url>        Jenkins url.  [required]
  -u, --user <username>  Jenkins username.  [required]
  -t, --token <token>    Jenkins access token.  [required]
  -h, --help             Show this message and exit.

Commands:
  info
```

### Info

```sh
⟩ jencli info -h
Usage: jencli info [OPTIONS]

Options:
  -j <jenkins job name>       Jenkins job name.  [required]
  -n <jenkins job number>     Jenkins job number, default latest job.
  -o, --output <output file>  Output file or stdout by default.
  -v, --verbose
  -h, --help                  Show this message and exit.

$ export JENKINS_URL=<jenkins url>
$ export JENKINS_USERNAME=<user>
$ export JENKINS_TOKEN=<access token>
$ jencli info -j <job name>
{
  "job": "job name",
  "lastCompletedBuild": {
    "date": "Oct 23 2020 00:25:58",
    "url": "<url>",
    "result": "UNSTABLE"
  },
  "healthReport": [
    {
      "description": "Test Result: 2 tests failing out of a total of NNN tests.",
      "score": 99
    },
    {
      "description": "Build stability: No recent builds failed.",
      "score": 100
    }
  ],
  "passTestsCount": N,
  "failTestsCount": M,
  "skipTestsCount": P,
  "testReportLink": "...",
  "failedCases": [
    {
      "age": 1,
      "className": "....",
      "errorDetails": "....",
      "name": "....",
      "status": "FAILED"
    },
    {
      "age": 2,
      "className": "....",
      "errorDetails": "....",
      "name": "....",
      "status": "FAILED"
    }
  ]
}
