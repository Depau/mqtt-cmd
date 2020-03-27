# MQTT command runner

Run actions when something is published over MQTT.

**Work in progress**, may not work as expected.

## What it does

- You provide a list of subscription
- For each subscription, you provide a list of patterns to match in the
  message
- For each pattern, you can run multiple actions

Currently implemented actions include:

- HTTP requests
- Running commands (both with and without the shell)

Patterns can be provided both as [jq](https://stedolan.github.io/jq/)-style
patterns, or as Jinja2 templates.

Action parameters (such as URL, POST data, command parameters or
`stdin` to commands) are all parsed as Jinja2 templates, and are provided
the MQTT topic, raw payload, JSON-parsed payload and other less useful things.

MQTT authentication is not implemented but it can be easily added (there
is not much code).

# Configuration

Configuration must be provided and it's a YAML document:

```yaml
## MQTT broker connection
mqtt:
  host: "ip"                 # your broker's IP
  port: 1883                 # default 1883
  client_id: "mqtt-cmd"      # default "mqtt-cmd"

templates:
  template_name:
    action_name:
      prepared: "params"

topics:
  ## List of topics
  - 'subscription/topic/with/wildcard/#':
      ## Topic-specific settings
      # Whether the payload should be parsed as a JSON string
      load_json: true        # default false

      ## Pattern extraction settings (mutually exclusive, optional)
      jq_query: ".button"    # optional, applies only to patterns
      #jinja_query: ""       # optional, mutually exclusive with jq_query

      patterns:
        ## Patterns to match
        'KEY_PLAY':
          # ... actions
```

## Topics

All topics will be subscribed to. They can have wildcards (both `+` and `#`).

For each topic you can specify whether its payload should be parsed as JSON.

`jq_query` and `jinja_query` are explained in Patterns.

## Patterns

Patterns are a list of strings that will be matched against the payload.

In case you provide a query matcher (in the topic config), its result will be
matched against your patterns. If you don't provide any, the raw payload will
be used instead. 

`jq_query` patterns are less flexible, but they *should* be faster (that is my
expectation though, no benchmarks have been performed).

`jinja_query` patterns are way more flexible, they can match against anything
including the topic, the payload, QoS, etc. and can run Python code to 
some extent.

Note that they are mutually exclusive for each topic. If you provide both,
an exception will be raised.

If you need different matchers for the same topic, you can specify it multiple
times with different matchers.

### jq matcher

If a `jq_query` is provided, it will be run against the JSON-parsed payload.

If `load_json` is set to `false`, then the payload will be turned into a JSON
string and passed to `jq`.

Only the first result of the jq query will be considered.

Full documentation for jq's syntax is available in their website:
https://stedolan.github.io/jq/

### Jinja2 matcher

If a `jinja_query` is provided, it will be rendered as a Jinja2 template.

Available template variables are described later in
[Jinja2 template variables](#jinja2-template-variables)


## Actions

Thre actions are available for use. All strings inside are parsed as Jinja2
templates, with variables described in 
[Jinja2 template variables](#jinja2-template-variables).

All actions accept a `timeout` field in seconds that will kill it if it
takes longer. Defaults vary. 

### Command action

Runs a system command (asynchronously).

- `shell`: `true`/`false`, default `false` - Whether or not to run the
  command in the system shell.
- `args` - If `shell` is `false`, a list of subprocess arguments (parsed
  as Jinja2 templates) like in `subprocess.Popen`. If `shell` is `true`,
  a string containing the shell command.
- `stdin`: optional, string - If provided, it must be a string that will
  be passed to the subprocess' `stdin`.
  
### Request action

Performs an HTTP request to a remote server (asynchronously).

- `url`: string - The HTTP URL
- `method`: optional, default `GET` - The HTTP method
- `post_data`: optional - Any raw post data to be sent to the server
- `headers`: optional - A dict of strings to be used for HTTP headers

### Template actions

Basic templates for actions may be provided (i.e. in order to avoid
typing all over the config the same api key).

Templates may be defined on top of any action (including `template`),
but they can accept any additional Jinja2 template variables.

To define templates, add in the config root:

```yaml
templates:
  my_tpl_name:
    action_name:
      action_parameters: null

  # For example
  api_request:
    request:
      url: "https://api.example.com{{ location }}"
      headers:
        X-API-Key: "deadbeef" 
```

To use template, use, as action:

```yaml
template:
  name: api_request
  method: GET
  location: /
```

Note that template variables that override internal variables such as
`topic`, `value`, `payload` are discarded.

To-do:
- Extend Jinja2 variable parsing so that Jinja2 non-string objects are
  used as such, allowing one to generate `args` and `headers` based on
  template action arguments in the template definition.

## Jinja2 template variables

The following variables are available in all Jinja2 templates:

- `mqtt: gmqtt.client.Client` - The MQTT client object
- `topic: str` - MQTT topic from which the message was received
- `payload: str` - Raw MQTT message payload (decoded as UTF-8)
- `value` - If `load_json` is `true`, it will contain the JSON-parsed MQTT
   payload. If `false`, it's the same as `payload`
- `qos: int` - The message's QoS value
- `properties: dict` - Message properties as provided by `gmqtt`

# License

Licensed under the GNU GPLv3.0 license.

