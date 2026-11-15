# Third-party components

The Java artifacts below are the frozen binaries used by the archived experiments. SHA-256 checksums are recorded in `provenance/artifact_hashes.json`; the runners copy them without modification. Source and license links identify their upstream projects. Embedded LICENSE/NOTICE files are also extracted under `licenses/embedded/` for convenient inspection.

| Bundled component | Upstream source / terms |
|---|---|
| Modified EdgeCloudSim source | [EdgeCloudSim](https://github.com/CagataySonmez/EdgeCloudSim), GPLv3; full license in `ThreeBrains/LICENSE` |
| `cloudsim-7.0.0-alpha.jar` | [CloudSim](https://github.com/Cloudslab/cloudsim); upstream GPL license and source headers |
| `weka.jar` and six supplied Weka models | [Weka](https://weka.waikato.ac.nz/), [upstream licensing](https://waikato.github.io/weka-wiki/faqs/commercial_applications/); preserve its GPL terms |
| `jFuzzyLogic_v3.0.jar` | [jFuzzyLogic](https://github.com/pcingola/jFuzzyLogic), [upstream license information](https://jfuzzylogic.sourceforge.net/html/about.html), LGPLv3 |
| `mtj-1.0.4.jar` | [Matrix Toolkits for Java](https://github.com/fommil/matrix-toolkits-java), LGPLv3 |
| `commons-math3-3.6.1.jar` | [Apache Commons Math](https://commons.apache.org/proper/commons-math/); embedded Apache LICENSE/NOTICE retained |
| Jackson annotations/core/databind 2.18.2 | [FasterXML](https://github.com/FasterXML); embedded Apache LICENSE/NOTICE and core third-party notices retained |
| `colt.jar` | CERN Colt; [archived upstream license text](https://sources.debian.org/src/colt/1.2.0~nojar-2/xdocs/license.xml). Package-specific terms apply, including the additional restriction stated for `hep.aida.*`; do not describe the whole JAR as MIT or Apache licensed. |

The original binary filenames are retained; an unversioned filename is not evidence of a specific release number. This repository does not claim byte-for-byte reconstruction of third-party JARs from current upstream branches. Use the bundled, checksummed versions for the paper protocol. For redistribution beyond this research archive, retain the applicable component notices and obtain corresponding upstream source as required by those terms.

Python dependencies are installed from `requirements-reproducibility.txt`, not vendored or relicensed. MATLAB and Times New Roman are external user-installed software and are not included.
