"""Mocks objects and protos for the GRR Host module tests."""

import datetime
import mock

from grr_api_client import client
from grr_api_client import flow
from grr_api_client import hunt
from grr_response_proto.api import client_pb2
from grr_response_proto.api import flow_pb2
from grr_response_proto import sysinfo_pb2
from grr_response_proto.api import hunt_pb2
from grr_response_proto import flows_pb2

from google.protobuf import text_format


client_proto1 = """
  urn: "aff4:/C.0000000000000000"
  os_info {{
    system: "Linux"
    release: "debian"
    version: "buster/sid"
    machine: "x86_64"
    kernel: "4.9.0-3-amd64"
    fqdn: "tomchop"
    install_date: 1480414461000000
  }}
  first_seen_at: 1480416002507491
  last_seen_at: {0:d}
  last_booted_at: 1507912328000000
  last_clock: 1511174989272124
  age: 1510710503319681
  client_id: "C.0000000000000000"
  knowledge_base {{
      users {{
          username: "tomchop_username1"
      }}
  }}
""".format(int(
    (
        datetime.datetime.now(datetime.timezone.utc)
        - datetime.timedelta(20)
    ).timestamp()*1000000)
)

# This has a more recent install_date and last_seen date than client_proto1
client_proto2 = """
  urn: "aff4:/C.0000000000000001"
  os_info {{
    system: "Linux"
    release: "debian"
    version: "buster/sid"
    machine: "x86_64"
    kernel: "4.9.0-3-amd64"
    fqdn: "tomchop"
    install_date: 1480414461020000
  }}
  first_seen_at: 1480416002507491
  last_seen_at: {0:d}
  last_booted_at: 1507912328000000
  last_clock: 1511174989272124
  age: 1510710503319681
  client_id: "C.0000000000000001"
  knowledge_base {{
      users {{
          username: "tomchop_username2"
      }}
  }}
""".format(int(
    (
        datetime.datetime.now(datetime.timezone.utc)
        - datetime.timedelta(25)
    ).timestamp()*1000000)
)

client_windows_1 = """
  urn: "aff4:/C.0000000000000002"
  os_info {{
    system: "Windows"
    release: "10"
    version: "10.0.19041"
    machine: "x86_64"
    kernel: "10.0.19041"
    fqdn: "tomchop"
    install_date: 1480414461000000
  }}
  first_seen_at: 1480416002507491
  last_seen_at: {0:d}
  last_booted_at: 1507912328000000
  last_clock: 1511174989272124
  age: 1510710503319681
  client_id: "C.0000000000000002"
  knowledge_base {{
      users {{
          username: "tomchop_username1"
      }}
  }}
""".format(int(
    (
        datetime.datetime.now(datetime.timezone.utc)
        - datetime.timedelta(20)
    ).timestamp()*1000000)
)

MOCK_CLIENT = client.Client(
    data=text_format.Parse(client_proto1, client_pb2.ApiClient()),
    context=mock.MagicMock())
MOCK_CLIENT_RECENT = client.Client(
    data=text_format.Parse(client_proto2, client_pb2.ApiClient()), context=True)
MOCK_WINDOWS_CLIENT = client.Client(
    data=text_format.Parse(client_windows_1, client_pb2.ApiClient()),
    context=True)
MOCK_CLIENT_LIST = [
    MOCK_CLIENT,
    MOCK_CLIENT_RECENT,
    MOCK_WINDOWS_CLIENT
]

MOCK_CLIENT_REF = client.ClientRef(MOCK_CLIENT.client_id, context=True)

flow_pb_terminated = flow_pb2.ApiFlow(
    urn="C.0000000000000001",
    flow_id="F:12345",
    state=flows_pb2.FlowContext.TERMINATED
)
flow_pb_error = flow_pb2.ApiFlow(
    urn="C.0000000000000001",
    flow_id="F:12345",
    state=flows_pb2.FlowContext.ERROR
)
flow_pb_running= flow_pb2.ApiFlow(
    urn="C.0000000000000001",
    flow_id="F:12345",
    state=flows_pb2.FlowContext.RUNNING
)
MOCK_FLOW = flow.Flow(data=flow_pb_terminated, context=True)
MOCK_FLOW_ERROR = flow.Flow(data=flow_pb_error, context=True)
MOCK_FLOW_RUNNING = flow.Flow(data=flow_pb_running, context=True)

hunt_pb = hunt_pb2.ApiHunt(
    urn="hunts/12345",
    hunt_id="F:12345",
    state=1
)

MOCK_HUNT = hunt.Hunt(data=hunt_pb, context=None)

MOCK_YARASCAN_PAYLOAD = flows_pb2.YaraProcessScanMatch(
    process=sysinfo_pb2.Process(
        pid=12345,
        exe='C:\\temp\\bad.exe',
        username='tomchop',
        cwd='C:\\temp',
        cmdline=['C:\\temp\\bad.exe', 'arg1', 'arg2'],
    ),
    match=[
        flows_pb2.YaraMatch(
            rule_name='badstring',
            string_matches=[
                flows_pb2.YaraStringMatch(string_id='$badstring1'),
                flows_pb2.YaraStringMatch(string_id='$badstring1'),
                flows_pb2.YaraStringMatch(string_id='$badstring1'),
                flows_pb2.YaraStringMatch(string_id='$badstring1'),
                flows_pb2.YaraStringMatch(string_id='$badstring2')
            ]
        ),
        flows_pb2.YaraMatch(
            rule_name='superbadstring',
            string_matches=[
                flows_pb2.YaraStringMatch(string_id='$superbadstring1'),
                flows_pb2.YaraStringMatch(string_id='$superbadstring2')
            ]
        )
    ]
)

MOCK_CFF_PAYLOAD_DIRECTORY_TEXT = """
payload: {
  [type.googleapis.com/grr.FileFinderResult] {
    stat_entry {
      st_mode: 17901
      pathspec {
        pathtype: OS
        path: "/directory"
        path_options: CASE_LITERAL
      }
    }
  }
}
"""
MOCK_CFF_PAYLOAD_DIRECTORY = flow.FlowResult(
    data=text_format.Parse(
        MOCK_CFF_PAYLOAD_DIRECTORY_TEXT, flow_pb2.ApiFlowResult()))

MOCK_CFF_PAYLOAD_FILE_TEXT = """
payload: {
  [type.googleapis.com/grr.FileFinderResult] {
    stat_entry {
      st_mode: 33184
      st_size: 1024
      pathspec {
        pathtype: OS
        path: "/directory/file"
        path_options: CASE_LITERAL
      }
    }
  }
}
"""
MOCK_CFF_PAYLOAD_FILE = flow.FlowResult(
    data=text_format.Parse(
        MOCK_CFF_PAYLOAD_FILE_TEXT, flow_pb2.ApiFlowResult()))

MOCK_CFF_RESULTS = [
    MOCK_CFF_PAYLOAD_DIRECTORY,
    MOCK_CFF_PAYLOAD_FILE
]
