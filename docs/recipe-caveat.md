# Recipe caveats

## vt_pcap_ts

This recipe will take a list of hashes (md5, sha256...) and check if they are known to Virustotal.
If a hash is known to Virustotal, the recipe will check if there is one or more pcaps available for that hash from a sandbox run.
Each available pcap will be downloaded and parsed. After the parsing, the data will be passed to Timesketch.

Be careful, large pcap files might take a long time to process.

To use this recipe, the user needs to provide an [Virustotal Premium API key](https://developers.virustotal.com/v3.0/reference#public-vs-premium-api) either via argument or in `~/.dftimewolfrc` as `vt_api_key` Each parsed pcap will generate a new timeline in Timesketch in a given sketch.
