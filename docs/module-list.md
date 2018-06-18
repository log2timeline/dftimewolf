# Module list

This is a list of existing dfTimewolf modules. To see how well they play
together, see the [recipe list](recipe-list.md).

## Collectors

* `FilesystemCollector` - a simple collector that just passes a local path on to
the processors.

### GRR hunts

Launch or fetch results from fleet-wide GRR hunts.
  * `GRRHuntArtifactCollector` - Launches a fleet-wide GRR
  `ArtifactCollectorFlow`
  * `GRRHuntFileCollector` - Launches a fleet-wide GRR `FileFinder`
  * `GRRHuntDownloader` - Downloads results from a GRR hunt.

### GRR flows

Launch and fetch flows on a specific list of hosts.

 * `GRRArtifactCollector` - Launches a GRR `ArtifactCollectorFlow` on specific
   hosts.
 * `GRRFileCollector` - Launches a `FileFinder` flow on specific hosts.
 * `GRRFlowCollector` - Downloads the results of an arbitrary flow.

**NOTE:** As a general rule, `GRRHuntArtifactCollector` and
`GRRHuntFileCollector` collectors are asynchronous. They will create a hunt and
return the hunt ID that should be used with `GRRHuntDownloader` once the hunt is
complete. `GRRArtifactCollector`, `GRRFileCollector` and `GRRFlowCollector` will
wait for results before exiting.

## Processors

* `LocalPlasoProcessor` - processes a list of file paths with a local plaso
(`log2timeline.py`) instance.

## Exporters

* `TimesketchExporter` - exports the result of a processor to a remote Timesketch
instance.
* `LocalFileSystemExporter` - exports the results of a processor to the local
filesystem.
