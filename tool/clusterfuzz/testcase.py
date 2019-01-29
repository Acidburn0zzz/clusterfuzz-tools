"""Module for the Testcase class."""
# Copyright 2016 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import os
import re
import shutil
import tempfile
import zipfile

from clusterfuzz import common


CLUSTERFUZZ_TESTCASE_URL = (
    'https://%s/testcase-detail/download-testcase?id=%s' %
    (common.DOMAIN_NAME, '%s'))
DOWNLOAD_TIMEOUT = 100
TESTCASE_CACHE_TTL = 6 * 60 * 60  # The testcase file is cached for 6 hours.


logger = logging.getLogger('clusterfuzz')


def _unescape(string):
  """Un-escape a string."""
  string = string.replace("&lt;", "<")
  string = string.replace("&gt;", ">")
  string = string.replace("&apos;", "'")
  string = string.replace("&quot;", "\"")
  # This has to be last call.
  string = string.replace("&amp;", "&")
  return string


def get_environment_and_args(stacktrace_lines):
  """Sets up the environment by parsing stacktrace lines."""

  new_env = {}
  args = ''
  stacktrace_lines = [
      _unescape(line['content']) for line in stacktrace_lines]
  for line in stacktrace_lines:
    if '[Environment] ' in line:
      line = line.replace('[Environment] ', '')
      tokens = line.split(' = ', 1)
      if len(tokens) != 2:
        continue
      name, value = tokens

      # TODO(tanin): we shouldn't flip the symbolize value here. We can flip it
      # in a reproducer after deserializing the sanitizer's options.
      if '_OPTIONS' in name:
        value = value.replace('symbolize=0', 'symbolize=1')
        if 'symbolize=1' not in value:
          value += ':symbolize=1'
      new_env[name] = value

    elif 'Running command: ' in line:
      line = line.replace('Running command: ', '').split(' ')

      # Strip off the binary & testcase paths.
      line = line[1:len(line)-1]

      args = " ".join(line)

  return new_env, args


def get_environment_sections(lines):
  """Get the environment-variable section. The section starts with a line
    starting with [Environment] and ends with a blank line."""
  lines = [_unescape(line['content']) for line in lines]

  is_in_environment = False
  results = []
  for line in lines:
    if line.startswith('[Environment]'):
      is_in_environment = True

    if is_in_environment and not line.strip():
      break

    if is_in_environment:
      results.append(line)

  sections = []
  for section in '\n'.join(results).split('[Environment]'):
    section = section.strip()

    if not section:
      continue
    sections.append(section)

  return sections


def parse_env_file(prefix, raw_text):
  """Parse an env file in an Android's stacktrace."""
  lines = raw_text.split('\n')
  m = re.match('%s file = ([^ ]+) with contents:' % prefix, lines[0])
  return m.group(1), '\n'.join(lines[1:])


def parse_asan_options(raw_text):
  """Parses the ASAN options in an Android's stacktrace."""
  m = re.match('ASAN Options file = ([^ ]+) with contents ([^ ]+)', raw_text)
  return m.group(1), m.group(2)


def get_command_line_file_path(environment_sections):
  """Get command line file from raw environment section in the stacktrace
    (for android)."""
  for section in environment_sections:
    section = section.strip()
    if section.startswith('Command line'):
      path, _ = parse_env_file('Command line', section)
      return path

  raise Exception(
      '"[Environment] Command line file = ..." is not found in the stacktrace.')


def get_file_contents_for_android(environment_sections):
  """Sets up the environment variables by parsing stacktrace lines (for
    android)."""
  file_contents = {}
  for section in environment_sections:
    section = section.strip()
    if section.startswith('Local properties'):
      path, value = parse_env_file('Local properties', section)
      file_contents[path] = value
    elif section.startswith('ASAN Options'):
      path, value = parse_asan_options(section)
      file_contents[path] = value
  return file_contents


def get_package_and_main_class_names(stacktrace_lines):
  """Get package and main class names."""
  for line in stacktrace_lines:
    content = line['content'].strip()
    if 'shell am start' not in content:
      continue

    match = re.match(
        r'.*shell am start -a [^\s]+ -n ([^/]+)/([^\s]+) .+', content)

    if match:
      return (match.group(1), match.group(2))

  raise Exception('Cannot find the package and main class in the stacktrace.')


def download_testcase(url):
  """Download the testcase into dest_dir."""
  tmp_dir_path = tempfile.mkdtemp(dir=common.CLUSTERFUZZ_TMP_DIR)
  logger.info('Downloading testcase files...')

  auth_header = common.get_stored_auth_header()
  # Do not use curl because curl doesn't support downloading an empty file.
  # See: https://github.com/google/clusterfuzz-tools/issues/326
  args = (
      '--no-verbose --waitretry=%s --retry-connrefused --content-disposition '
      '--header="Authorization: %s" "%s"' %
      (DOWNLOAD_TIMEOUT, auth_header, url))
  common.execute('wget', args, tmp_dir_path)
  return os.path.join(tmp_dir_path, os.listdir(tmp_dir_path)[0])


def create(testcase_json, force=False):
  """Parse testcase json and instantiate a Testcase."""
  stacktrace_lines = testcase_json['crash_stacktrace']['lines']

  envs = {}
  reproduction_args = ''
  files = {}
  command_line_file_path = None
  android_package_name = None
  android_main_class_name = None

  if 'android' in testcase_json['testcase']['job_type']:
    environment_sections = get_environment_sections(stacktrace_lines)
    files = get_file_contents_for_android(environment_sections)
    command_line_file_path = get_command_line_file_path(environment_sections)
    android_package_name, android_main_class_name = (
        get_package_and_main_class_names(stacktrace_lines))
  else:
    envs, reproduction_args = get_environment_and_args(stacktrace_lines)

  if not reproduction_args and not force:
    reproduction_args = (
        '%s %s' % (testcase_json['testcase']['window_argument'],
                   testcase_json['testcase']['minimized_arguments'])).strip()
  absolute_path = testcase_json['testcase']['absolute_path']

  return Testcase(
      testcase_id=testcase_json['id'],
      stacktrace_lines=stacktrace_lines,
      environment=envs,
      reproduction_args=reproduction_args,
      revision=testcase_json['crash_revision'],
      build_url=testcase_json['metadata']['build_url'],
      job_type=testcase_json['testcase']['job_type'],
      absolute_path=absolute_path,
      reproducible=not testcase_json['testcase']['one_time_crasher_flag'],
      gestures=testcase_json['testcase'].get('gestures'),
      crash_type=testcase_json['crash_type'],
      crash_state=testcase_json['crash_state'],
      raw_gn_args=testcase_json['metadata'].get('gn_args', '').strip(),
      files=files,
      command_line_file_path=command_line_file_path,
      android_package_name=android_package_name,
      android_main_class_name=android_main_class_name,
      created_at=testcase_json['timestamp'],
      platform=testcase_json['testcase']['platform'])


def get_true_testcase_path(
    testcase_dir_path, testcase_absolute_path, downloaded_file_path):
  """Return actual testcase path, unzips testcase if required."""
  filename = os.path.basename(testcase_absolute_path)
  if downloaded_file_path.endswith('.zip'):
    zipped_file = zipfile.ZipFile(downloaded_file_path, 'r')
    zipped_file.extractall(testcase_dir_path)
    zipped_file.close()
    return common.find_file(filename, testcase_dir_path)
  else:
    dest_path = os.path.join(testcase_dir_path, filename)
    shutil.move(downloaded_file_path, dest_path)
    return dest_path


class Testcase(object):
  """The Testase module, to abstract away logic using the testcase JSON."""

  def __init__(
      self, testcase_id, stacktrace_lines, environment, reproduction_args,
      revision, build_url, job_type, absolute_path, reproducible, gestures,
      crash_type, crash_state, raw_gn_args, files, command_line_file_path,
      android_package_name, android_main_class_name, created_at, platform):
    self.id = testcase_id
    self.stacktrace_lines = stacktrace_lines
    self.environment = environment
    self.reproduction_args = reproduction_args
    self.revision = revision
    self.build_url = build_url
    self.job_type = job_type
    self.absolute_path = absolute_path
    self.reproducible = reproducible
    self.gestures = gestures
    self.crash_type = crash_type
    self.crash_state = crash_state
    self.raw_gn_args = raw_gn_args
    self.files = files
    self.command_line_file_path = command_line_file_path
    self.android_package_name = android_package_name
    self.android_main_class_name = android_main_class_name
    self.created_at = created_at
    self.platform = platform

    self.testcase_dir_path = os.path.join(
        common.CLUSTERFUZZ_TESTCASES_DIR, str(self.id) + '_testcase')

  @common.memoize
  def get_testcase_path(self):
    """Downloads & returns the location of the testcase file."""
    downloaded_file_path = download_testcase(CLUSTERFUZZ_TESTCASE_URL % self.id)

    common.delete_if_exists(self.testcase_dir_path)
    os.makedirs(self.testcase_dir_path)

    return get_true_testcase_path(
        self.testcase_dir_path, self.absolute_path, downloaded_file_path)
