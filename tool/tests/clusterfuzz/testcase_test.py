"""Test the 'testcase' module and class."""
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

import os
import mock

from clusterfuzz import common
from clusterfuzz import testcase
from test_libs import helpers


def build_base_testcase(stacktrace_lines=None, revision=None, build_url=None,
                        window_arg='', minimized_args='', extension='.js',
                        gestures=None, job_type='linux_asan_d8_dbg'):
  """Builds a testcase instance that can be used for testing."""
  if extension is not None:
    extension = '.%s' % extension
  else:
    extension = ''
  if stacktrace_lines is None:
    stacktrace_lines = []
  testcase_json = {
      'id': '12345',
      'crash_stacktrace': {'lines': stacktrace_lines, 'revision': 'bad'},
      'crash_type': 'bad_crash',
      'crash_state': 'halted',
      'crash_revision': revision,
      'metadata': {'build_url': build_url, 'gn_args': 'use_goma = true\n'},
      'testcase': {'window_argument': window_arg,
                   'job_type': job_type,
                   'one_time_crasher_flag': False,
                   'minimized_arguments': minimized_args,
                   'absolute_path': '/absolute/path%s' % extension,
                   'platform': 'linux'},
      'timestamp': 123}
  if gestures:
    testcase_json['testcase']['gestures'] = []

  return testcase.create(testcase_json)


class TestcaseSetupTest(helpers.ExtendedTestCase):
  """Tests populating the testcase parameters."""

  def setUp(self):
    helpers.patch(self, [
        'clusterfuzz.testcase.get_command_line_file_path',
        'clusterfuzz.testcase.get_environment_sections',
        'clusterfuzz.testcase.get_file_contents_for_android',
        'clusterfuzz.testcase.get_package_and_main_class_names',
    ])

  def test_parsing_json(self):
    """Ensures the JSON is parsed correctly."""

    stacktrace_lines = [
        {'content': '[Environment] TEST_ARGS = first=1:second = 2'},
        {'content': 'Not an env line'},
        {'content': '[Environment] This is ignored.'},
        {'content': '[Environment] ASAN_OPTIONS = x=1:symbolize=0'},
        {'content': '[Environment] LSAN_OPTIONS = y=1'},
        {'content': ('Running command: /path/to/binary --random-seed=23 '
                     '--turbo /path/to/testcase')},
        {'content': '[Environment] TEST_TWO = third=3:fourth=4'}]
    result = build_base_testcase(
        stacktrace_lines=stacktrace_lines, revision=5, build_url='build_url',
        gestures=True)
    self.assertEqual(result.id, '12345')
    self.assertEqual(result.revision, 5)
    self.assertEqual(result.environment, {'TEST_ARGS': 'first=1:second = 2',
                                          'TEST_TWO': 'third=3:fourth=4',
                                          'ASAN_OPTIONS': 'x=1:symbolize=1',
                                          'LSAN_OPTIONS': 'y=1:symbolize=1'})
    self.assertEqual(result.reproduction_args, '--random-seed=23 --turbo')
    self.assertEqual(result.build_url, 'build_url')
    self.assertTrue(result.reproducible)
    self.assertEqual(result.gestures, [])

  def test_parsing_json_with_piped_input(self):
    """Ensures the JSON is parsed correctly."""

    stacktrace_lines = [
        {'content': '[Environment] TEST_ARGS = first=1:second = 2'},
        {'content': 'Not an env line'},
        {'content': '[Environment] This is ignored.'},
        {'content': '[Environment] ASAN_OPTIONS = x=1:symbolize=0'},
        {'content': '[Environment] LSAN_OPTIONS = y=1'},
        {'content': ('Running command: /path/to/binary '
                     '--random-seed=&quot;23&quot; '
                     '--turbo &lt; /path/to/testcase')},
        {'content': '[Environment] TEST_TWO = third=3:fourth=4'}]
    result = build_base_testcase(
        stacktrace_lines=stacktrace_lines, revision=5, build_url='build_url',
        gestures=True)
    self.assertEqual(result.id, '12345')
    self.assertEqual(result.revision, 5)
    self.assertEqual(result.environment, {'TEST_ARGS': 'first=1:second = 2',
                                          'TEST_TWO': 'third=3:fourth=4',
                                          'ASAN_OPTIONS': 'x=1:symbolize=1',
                                          'LSAN_OPTIONS': 'y=1:symbolize=1'})
    self.assertEqual(result.reproduction_args, '--random-seed="23" --turbo <')
    self.assertEqual(result.build_url, 'build_url')
    self.assertTrue(result.reproducible)
    self.assertEqual(result.gestures, [])

  def test_android(self):
    """Tests android testcase."""
    self.mock.get_environment_sections.return_value = 'ENV-SECTION'
    self.mock.get_file_contents_for_android.return_value = {
        'file': 'file-content'}
    self.mock.get_command_line_file_path.return_value = 'path'
    self.mock.get_package_and_main_class_names.return_value = (
        'package', 'class')

    stacktrace_lines = [{'content': 'trace'}]
    result = build_base_testcase(
        stacktrace_lines=stacktrace_lines, revision=5, build_url='build_url',
        gestures=True, job_type='android_something')
    self.assertEqual(result.id, '12345')
    self.assertEqual(result.revision, 5)
    self.assertEqual(result.environment, {})
    self.assertEqual(result.reproduction_args, '')
    self.assertEqual(result.build_url, 'build_url')
    self.assertTrue(result.reproducible)
    self.assertEqual(result.gestures, [])
    self.assertEqual(result.files, {'file': 'file-content'})
    self.assertEqual(result.command_line_file_path, 'path')
    self.assertEqual(result.android_package_name, 'package')
    self.assertEqual(result.android_main_class_name, 'class')
    self.mock.get_file_contents_for_android.assert_called_once_with(
        'ENV-SECTION')
    self.mock.get_environment_sections.assert_called_once_with(
        [{'content': 'trace'}])


class GetEnvironmentSectionsTest(helpers.ExtendedTestCase):
  """Tests get_environment_sections."""

  def test_get(self):
    """Tests get."""
    # pylint: disable=line-too-long
    stacktrace = [
        {'content': ''},
        {'content': '[Environment] Build fingerprint = google/hammerhead/hammerhead:6.0.1/MOB31V/3693677:userdebug/dev-keys'},
        {'content': '[Environment] Patch level: 2017-03-05'},
        {'content': '[Environment] Local properties file = /data/local.prop with contents:'},
        {'content': 'ro.audio.silent=1'},
        {'content': 'ro.monkey=1'},
        {'content': 'ro.setupwizard.mode=DISABLED'},
        {'content': 'ro.test_harness=1'},
        {'content': 'ro.telephony.disable-call=true'},
        {'content': 'dalvik.vm.enableassertions='},
        {'content': 'debug.assert=0'},
        {'content': 'dalvik.vm.checkjni=true'},
        {'content': 'debug.checkjni=1'},
        {'content': '[Environment] Command line file = /data/local/tmp/chrome-command-line with contents:'},
        {'content': 'chrome --disable-in-process-stack-traces --disable-gpu-watchdog --disable-document-mode --enable-test-intents --disable-fre --no-restore-state --js-flags="--expose-gc" /sdcard/fuzzer-testcases/clusterfuzz-testcase-minimized-5883294062477312.html'},
        {'content': '[Environment] ASAN Options file = /data/local/tmp/asan.options with contents redzone=128:allow_user_segv_handler=1:fast_unwind_on_fatal=1:alloc_dealloc_mismatch=0:detect_leaks=0:print_scariness=1:check_malloc_usable_size=0:abort_on_error=0:allocator_may_return_null=1:strict_memcmp=0:detect_container_overflow=0:coverage=0:detect_odr_violation=0:symbolize=0:handle_segv=1:use_sigaltstack=1'},
        {'content': ''},
    ]

    expected = [
        'Build fingerprint = google/hammerhead/hammerhead:6.0.1/MOB31V/3693677:userdebug/dev-keys',
        'Patch level: 2017-03-05',
        ('Local properties file = /data/local.prop with contents:\n'
         'ro.audio.silent=1\n'
         'ro.monkey=1\n'
         'ro.setupwizard.mode=DISABLED\n'
         'ro.test_harness=1\n'
         'ro.telephony.disable-call=true\n'
         'dalvik.vm.enableassertions=\n'
         'debug.assert=0\n'
         'dalvik.vm.checkjni=true\n'
         'debug.checkjni=1'),
        ('Command line file = /data/local/tmp/chrome-command-line with contents:\n'
         'chrome --disable-in-process-stack-traces --disable-gpu-watchdog --disable-document-mode --enable-test-intents --disable-fre --no-restore-state --js-flags="--expose-gc" /sdcard/fuzzer-testcases/clusterfuzz-testcase-minimized-5883294062477312.html'),
        'ASAN Options file = /data/local/tmp/asan.options with contents redzone=128:allow_user_segv_handler=1:fast_unwind_on_fatal=1:alloc_dealloc_mismatch=0:detect_leaks=0:print_scariness=1:check_malloc_usable_size=0:abort_on_error=0:allocator_may_return_null=1:strict_memcmp=0:detect_container_overflow=0:coverage=0:detect_odr_violation=0:symbolize=0:handle_segv=1:use_sigaltstack=1',
    ]
    # pylint: enable=line-too-long
    self.assertEqual(expected, testcase.get_environment_sections(stacktrace))


class GetFileContentsForAndroidTest(helpers.ExtendedTestCase):
  """Tests get_file_contents_for_android."""

  def test_get(self):
    """Tests get."""
    # pylint: disable=line-too-long
    sections = [
        'Build fingerprint = google/hammerhead/hammerhead:6.0.1/MOB31V/3693677:userdebug/dev-keys\n',
        'Patch level: 2017-03-05\n',
        ('Local properties file = /data/local.prop with contents:\n'
         'ro.audio.silent=1\n'
         'ro.monkey=1\n'
         'ro.setupwizard.mode=DISABLED\n'
         'ro.test_harness=1\n'
         'ro.telephony.disable-call=true\n'
         'dalvik.vm.enableassertions=\n'
         'debug.assert=0\n'
         'dalvik.vm.checkjni=true\n'
         'debug.checkjni=1'),
        ('Command line file = /data/local/tmp/chrome-command-line with contents:\n'
         'chrome --disable-in-process-stack-traces --disable-gpu-watchdog --disable-document-mode --enable-test-intents --disable-fre --no-restore-state --js-flags="--expose-gc" /sdcard/fuzzer-testcases/clusterfuzz-testcase-minimized-5883294062477312.html'),
        'ASAN Options file = /data/local/tmp/asan.options with contents redzone=128:allow_user_segv_handler=1:fast_unwind_on_fatal=1:alloc_dealloc_mismatch=0:detect_leaks=0:print_scariness=1:check_malloc_usable_size=0:abort_on_error=0:allocator_may_return_null=1:strict_memcmp=0:detect_container_overflow=0:coverage=0:detect_odr_violation=0:symbolize=0:handle_segv=1:use_sigaltstack=1',
    ]

    expected = {
        '/data/local.prop': (
            'ro.audio.silent=1\n'
            'ro.monkey=1\n'
            'ro.setupwizard.mode=DISABLED\n'
            'ro.test_harness=1\n'
            'ro.telephony.disable-call=true\n'
            'dalvik.vm.enableassertions=\n'
            'debug.assert=0\n'
            'dalvik.vm.checkjni=true\n'
            'debug.checkjni=1'),
        '/data/local/tmp/asan.options': (
            'redzone=128:allow_user_segv_handler=1:fast_unwind_on_fatal=1:alloc_dealloc_mismatch=0:detect_leaks=0:print_scariness=1:check_malloc_usable_size=0:abort_on_error=0:allocator_may_return_null=1:strict_memcmp=0:detect_container_overflow=0:coverage=0:detect_odr_violation=0:symbolize=0:handle_segv=1:use_sigaltstack=1'),
    }
    # pylint: enable=line-too-long

    self.assertEqual(
        expected, testcase.get_file_contents_for_android(sections))


class GetCommandLineFilePathTest(helpers.ExtendedTestCase):
  """Tests get_command_line_file_path."""

  def test_get(self):
    """Tests get."""
    sections = [
        ('Command line file = '
         '/data/local/tmp/chrome-command-line with contents:\n'
         "doesn't matter"),
    ]
    self.assertEqual(
        '/data/local/tmp/chrome-command-line',
        testcase.get_command_line_file_path(sections))

  def test_no_command_line(self):
    """Tests no command line."""
    sections = ['Test test']

    with self.assertRaises(Exception):
      testcase.get_command_line_file_path(sections)


class DownloadTestcaseTest(helpers.ExtendedTestCase):
  """Test download_testcase."""

  def setUp(self):
    helpers.patch(self, [
        'clusterfuzz.common.execute',
        'clusterfuzz.common.get_stored_auth_header',
        'tempfile.mkdtemp',
        'os.listdir'
    ])
    self.mock.get_stored_auth_header.return_value = 'Bearer 1a2s3d4f'
    self.dir = os.path.join(
        common.CLUSTERFUZZ_TESTCASES_DIR, '12345_testcase')
    self.mock.mkdtemp.return_value = '/tmp/folder'
    self.mock.listdir.return_value = ['first-file']

  def test_downloading_testcase(self):
    """Tests the creation of folders & downloading of the testcase"""
    self.assertEqual(
        '/tmp/folder/first-file', testcase.download_testcase('url'))

    self.mock.get_stored_auth_header.assert_called_once_with()
    self.mock.execute.assert_called_once_with(
        'wget',
        ('--no-verbose --waitretry=%s --retry-connrefused '
         '--content-disposition --header="Authorization: %s" "url"' % (
             testcase.DOWNLOAD_TIMEOUT,
             self.mock.get_stored_auth_header.return_value)),
        '/tmp/folder'
    )
    self.mock.listdir.assert_called_once_with('/tmp/folder')


class GetTestcasePathTest(helpers.ExtendedTestCase):
  """Tests the get_testcase_path method."""

  def setUp(self):
    helpers.patch(self, [
        'clusterfuzz.common.delete_if_exists',
        'clusterfuzz.testcase.get_true_testcase_path',
        'clusterfuzz.testcase.download_testcase',
        'os.makedirs'
    ])
    self.test = build_base_testcase()
    self.testcase_dir = os.path.join(
        common.CLUSTERFUZZ_TESTCASES_DIR, '12345_testcase')

  def test_downloading_testcase(self):
    """Tests the creation of folders & downloading of the testcase"""
    self.mock.get_true_testcase_path.return_value = 'true_path'
    self.assertEqual('true_path', self.test.get_testcase_path())

    self.mock.download_testcase.assert_called_once_with(
        testcase.CLUSTERFUZZ_TESTCASE_URL % str(12345))
    self.mock.delete_if_exists.assert_called_once_with(self.testcase_dir)
    self.mock.makedirs.assert_called_once_with(self.testcase_dir)


class GetTrueTestcasePathTest(helpers.ExtendedTestCase):
  """Tests the get_true_testcase_path method."""

  def setUp(self):
    helpers.patch(self, [
        'clusterfuzz.common.find_file',
        'shutil.move',
        'zipfile.ZipFile',
    ])
    self.mock.ZipFile.return_value = mock.Mock()
    self.absolute_path = 'to/testcase.js'
    self.testcase_dir_path = os.path.join(
        common.CLUSTERFUZZ_TESTCASES_DIR, '12345_testcase')

  def test_zipfile(self):
    """Tests when the file is a zipfile."""
    self.mock.find_file.return_value = 'after-find-file'
    self.assertEqual(
        'after-find-file',
        testcase.get_true_testcase_path(
            self.testcase_dir_path, self.absolute_path, 'abcd.zip')
    )

    self.mock.ZipFile.assert_has_calls([
        mock.call('abcd.zip', 'r'),
        mock.call().extractall(self.testcase_dir_path)
    ])
    self.mock.find_file.assert_called_once_with(
        'testcase.js', self.testcase_dir_path)

  def test_no_zipfile(self):
    """Tests when the downloaded file is not zipped."""
    self.assertEqual(
        os.path.join(self.testcase_dir_path, 'testcase.js'),
        testcase.get_true_testcase_path(
            self.testcase_dir_path, self.absolute_path, 'abcd.js'))

    self.assert_n_calls(0, [self.mock.ZipFile])
    self.assert_exact_calls(self.mock.move, [
        mock.call(
            'abcd.js', os.path.join(self.testcase_dir_path, 'testcase.js'))
    ])


class GetPackageAndMainClassNamesTest(helpers.ExtendedTestCase):
  """Tests get_package_and_main_class_names."""

  def test_get(self):
    """Tests get."""
    lines = [
        {'content': 'random'},
        {'content': (
            '[Command line] shell am start -a android.intent.action.VIEW -n '
            'org.chromium.webview_shell/.WebViewBrowserActivity -d '
            "'file:///sdcard/fuzzer-testcases/fuzz-88.html'")}
    ]
    self.assertEqual(
        ('org.chromium.webview_shell', '.WebViewBrowserActivity'),
        testcase.get_package_and_main_class_names(lines))

  def test_error(self):
    """Tests error."""
    lines = [
        {'content': 'random'},
        {'content': 'another random'}
    ]
    with self.assertRaises(Exception):
      testcase.get_package_and_main_class_names(lines)
