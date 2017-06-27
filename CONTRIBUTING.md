How to contribute
====================================

We'd love to accept your patches and contributions to this project. There are
just a few small guidelines you need to follow.


Contributor License Agreement
---------------------------------

Contributions to any Google project must be accompanied by a Contributor License
Agreement. This is necessary because you own the copyright to your changes, even
after your contribution becomes part of this project. So this agreement simply
gives us permission to use and redistribute your contributions as part of the
project. Head over to <https://cla.developers.google.com/> to see your current
agreements on file or to sign a new one.

You generally only need to submit a CLA once, so if you've already submitted one
(even if it was for a different project), you probably don't need to do it
again.


Code reviews
--------------

All submissions, including submissions by project members, require review. We
use GitHub pull requests for this purpose. Consult [GitHub Help] for more
information on using pull requests.

[GitHub Help]: https://help.github.com/articles/about-pull-requests/


Develop
------------

1. `./pants -V` to bootstrap [Pants](http://www.pantsbuild.org/).
2. Run the tool's tests: `./pants test.pytest --coverage=1 tool:test`.
3. Run the ci's tests: `./pants test.pytest --coverage=1 ci/continuous_integration:test`.
4. Run the tool binary: `./pants run tool:clusterfuzz-ci -- reproduce -h`.


Create a CI image
------------------

From the `ci` directory, perform the below steps:

1. Modify `image.yml` and increment the version of `image_name` in `group_vars/all`.
2. Create and merge the pull request.
3. Run `ansible-playbook image.yml` to create an image.
4. Re-deploy all CI instances.


Deploy CI
------------

From the `ci` directory, perform the below steps:

1. Ensure all the latest binaries are present and symlinked in
   `/google/data/ro/teams/clusterfuzz-tools/releases`.
2. Run `ansible-playbook playbook.yml -e release=<release-type> -e machine=<machine-name>`
   where `release-type` is one of `[release, release-candidate, master]` and
   `machine-name` is the prefix of the machine you wish to update or deploy
   (for example, `machine=release` corresponds to the boot disk
   `release-ci-boot` and the machine `release-ci`).

The CI log is at `/var/log/python-daemon/current`. The reproduce tool's log is
at `/home/clusterfuzz/.clusterfuzz/logs/output.log`.


Publish
----------

We publish our binary to 2 places: Cloud Storage (for public) and X20 (for Googlers).

1. Increment the version number in `tool/clusterfuzz/resources/VERSION`.
2. Create and merge a pull request to increase the version number.
3. Run `./pants run butler -- release`.


Analytics
--------------

To see the usage from our users, please see [the data in BigQuery](https://bigquery.cloud.google.com/table/clusterfuzz-tools:usage.client_20170612).
Here are useful links:

- [Usage by users (excluding our team
  members)](https://bigquery.cloud.google.com/savedquery/981641712411:20b7242585c1470f8a485eb1ce3be37a)
- [Successful usage by users and testcases (excluding our team
  members)](https://bigquery.cloud.google.com/savedquery/981641712411:e8ec7ebcc9304eb7aba83375e18a974e)
- [Usage logs (excluding
  our team
  members)](https://pantheon.corp.google.com/logs/viewer?project=clusterfuzz-tools&organizationId=433637338589&minLogLevel=0&expandAll=false&resource=project&logName=projects%2Fclusterfuzz-tools%2Flogs%2Fclient&advancedFilter=resource.type%3D%22project%22%0AlogName%3D%22projects%2Fclusterfuzz-tools%2Flogs%2Fclient%22%0AjsonPayload.user!%3D%22CI%22%0AjsonPayload.user!%3D%22tanin%22%0AjsonPayload.user!%3D%22aarya%22%0AjsonPayload.user!%3D%22clusterfuzz%22%0AjsonPayload.user!%3D%22ochang%22%0AjsonPayload.user!%3D%22mmoroz%22%0AjsonPayload.user!%3D%22mbarbella%22%0AjsonPayload.user!%3D%22tjbecker%22%0AjsonPayload.user!%3D%22everestmz%22)
- [CI
  logs](https://pantheon.corp.google.com/logs/viewer?project=clusterfuzz-tools&organizationId=433637338589&minLogLevel=0&expandAll=false&resource=project&logName=projects%2Fclusterfuzz-tools%2Flogs%2Fci)


Useful links for investigation
-----------------------------------

- [Query a specific testcase
  id](https://bigquery.cloud.google.com/savedquery/981641712411:dc2e55b3c47a440a96637a18ee98986b)
