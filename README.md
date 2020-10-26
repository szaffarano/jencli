# README

## Install

```sh
$ pip3 install https://github.com/szaffarano/jencli/archive/main.zip
```

## Usage

```sh
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
      "description": "Test Result: 2 tests failing out of a total of 8,950 tests.",
      "score": 99
    },
    {
      "description": "Build stability: No recent builds failed.",
      "score": 100
    }
  ],
  "passTestsCount": nnn,
  "failTestsCount": k,
  "skipTestsCount": mmm,
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
