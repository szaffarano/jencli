# README

## Install

```sh
$ pip3 install https://github.com/szaffarano/jencli/archive/main.zip
```

## Usage

```sh
$ jencli -h
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
$ jencli info --help
Usage: jencli info [OPTIONS]

Options:
  -j, --jobname <job name>        Jenkins job name.  [required]
  -b, --buildnumber <build number>
                                  Jenkins build number, default latest job. It
                                  could be a number or one of the following
                                  expressions: latest, last_N, N..M, N..latest

  -o, --output <output file>      Output file or stdout by default.
  -F, --findflakes
  -h, --help                      Show this message and exit.

$ export JENKINS_URL=<jenkins url>
$ export JENKINS_USERNAME=<user>
$ export JENKINS_TOKEN=<access token>
$ jencli info -j <job name> -b last_2
{
  "job": "<job name>",
  "healthReport": [
    {
      "description": "...",
      "score": 100
    }
  ],
  "builds": [
    {
      "number": NNNN,
      "info": {
        "date": "...",
        "url": "...",
        "result": "SUCCESS"
      },
      "name": "...",
      "passTestsCount": NNNN,
      "failTestsCount": NNNN,
      "skipTestsCount": NNNN,
      "testReportLink": "...",
      "flakes": [
        "...",
        "..."
      ]
    },
    {
      "number": MMMM,
      "info": {
        "date": "...",
        "url": "...",
        "result": "UNSTABLE"
      },
      "name": "...",
      "passTestsCount": MMMM,
      "failTestsCount": MMMM,
      "skipTestsCount": 8MMMM,
      "testReportLink": "...",
      "failedCases": [
        {
          "age": k,
          "className": "....",
          "errorDetails": "....",
          "name": "....",
          "status": "REGRESSION"
        },
        {
          "age": p,
          "className": "...",
          "errorDetails": "...",
          "name": "...",
          "status": "REGRESSION"
        }
      ]
    }
  ]
}
```
