## DFTimewolf

![dftimewolf](https://cloud.githubusercontent.com/assets/13300571/17257013/0065185c-5575-11e6-957d-5e662ec78d8c.png)

A framework for orchestrating forensic collection, processing and data export.

### Configuration

DFTimewolf has a minimal configuration file. DFTimewolf looks in the current
directory, your home directory, or a directory pointed to by the
`DFTIMEWOLF_CONFIG` environment variable and tries to load a JSON object from
either `dftimewolf.json` or `.dftimewolfrc`.

See `/dftimewolf/dftimewolf.json` for an example configuration file.
