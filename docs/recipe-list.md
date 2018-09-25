# Recipe list

dfTimewolf uses recipes, which are a way to configure Collectors, Processors,
and Exporters (called Modules).

## grr_artifact_hosts

Use this recipe to collect a predefined set of artifacts from a specific list of
hosts. If you want to collect the `BrowserHistory` and `LinuxLogFiles` from
`tomchop.greendale.xyz` and `admin.greendale.xyz`, use this
command:

    $ dftimewolf grr_artifact_hosts tomchop.greendale.xyz,admin.greendale.xyz --artifacts BrowserHistory,LinuxLogFiles

If `artifact_list` is not provided, the list defaults to:

*   Linux
    *   AllUsersShellHistory
    *   BrowserHistory
    *   LinuxLogFiles
    *   AllLinuxScheduleFiles
    *   LinuxScheduleFiles
    *   ZeitgeistDatabase
    *   AllShellConfigs
*   Mac OS
    *   MacOSRecentItems
    *   MacOSBashHistory
    *   MacOSLaunchAgentsPlistFiles
    *   MacOSAuditLogFiles
    *   MacOSSystemLogFiles
    *   MacOSAppleSystemLogFiles
    *   MacOSMiscLogs
    *   MacOSSystemInstallationTime
    *   MacOSQuarantineEvents
    *   MacOSLaunchDaemonsPlistFiles
    *   MacOSInstallationHistory
    *   MacOSUserApplicationLogs
    *   MacOSInstallationLogFile
*   Windows
    *   WindowsAppCompatCache
    *   WindowsEventLogs
    *   WindowsPrefetchFiles
    *   WindowsScheduledTasks
    *   WindowsSearchDatabase
    *   WindowsSuperFetchFiles
    *   WindowsSystemRegistryFiles
    *   WindowsUserRegistryFiles
    *   WindowsXMLEventLogTerminalServices

## grr_flow_download

Use this recipe to download the results of a given GRR flow.

If because of `test_reason` you want to fetch flow `F:920AFD8` from
`tomchop.greendale.xyz` and dump results into `/tmp/tomflow/`,
use the following command:

    $ dftimewolf grr_flow_download tomchop.greendale.xyz F:920AFD8 test_reason /tmp/tomflow

## grr_hunt_artifacts

Launches a hunt for specific artifacts. The hunt is launched with a client limit
set to 100 hosts.

If because of `test_reason` you want to launch a fleet-wide artifact hunt on
`BrowserHistory` artifacts, use the following command:

    $ dftimewolf grr_hunt_artifacts BrowserHistory test_reason

NOTE: Since hunts take time to complete, dfTimewolf will launch the hunt and
return a Hunt ID that you can then feed to `grr_huntresults_plaso_timesketch`.

## grr_hunt_file

Launches a hunt for specific files. The hunt is launched with a client limit set
to 100 hosts. This is standard procedure for creating new hunts anyways.

If because of `test_reason` you want to launch a fleet-wide file hunt on
`/tmp/billgates.pl` files, use the following command:

    $ dftimewolf grr_hunt_file /tmp/billgates.pl test_reason

<div class="admonition note">
  <p class="first admonition-title">Note</p>
  <p class="last">Since hunts take time to complete, dfTimewolf will launch
  the hunt and return a Hunt ID that you can then feed to
  <code>grr_huntresults_plaso_timesketch</code>.</p>
</div>

## grr_huntresults_plaso_timesketch

Use this recipe to collect results from a GRR Hunt, process them with a local
instance of plaso, and send them to our Timesketch server.

If you want to fetch results for `H:7481F262` because of `test_reason`, use the
following command:

    $ dftimewolf grr_huntresults_plaso_timesketch H:7481F262 test_reason

## local_plaso

Use this recipe to process a local file using plaso and send the results to our
Timesketch server.

If because of `test_reason` you want to process all files in `/mnt/winroot` with
plaso and send results to Timesketch, use the following command:

    $ dftimewolf local_plaso /mnt/winroot test_reason

## timesketch_upload

Use this recipe to upload a `.plaso` or `.csv` file to Timesketch:

    $ dftimewolf timesketch_upload ~/cases/sem12345/sdb1.plaso
