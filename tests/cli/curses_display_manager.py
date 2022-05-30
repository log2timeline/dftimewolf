#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the CursesDisplayManager."""

from contextlib import redirect_stdout
import io
import unittest
from unittest import mock

from dftimewolf.cli.curses_display_manager import CursesDisplayManager, \
    Message, Module, Status

# pylint: disable=protected-access


class CursesDisplayManagerModuleTest(unittest.TestCase):
  """Tests for the Module helper class of the CursesDisplayManager."""

  def setUp(self):
    self.m = Module('ModuleName', ['Dependency1', 'Dependency2'], 'RuntimeName')

  def tearDown(self):
    self.m = None

  def testInit(self):
    """Tests cdm.Module initialisation."""
    self.assertEqual(self.m.name, 'ModuleName')
    self.assertEqual(self.m.runtime_name, 'RuntimeName')
    self.assertEqual(self.m.status, Status.PENDING)
    self.assertEqual(self.m._dependencies, ['Dependency1', 'Dependency2'])
    self.assertEqual(self.m._error_message, '')
    self.assertEqual(self.m._threads, {})
    self.assertEqual(self.m._threads_containers_max, 0)
    self.assertEqual(self.m._threads_containers_completed, 0)

  def testSetStatus(self):
    """Test setting cdm.Module status."""
    self.m.SetStatus(Status.SETTINGUP)
    self.assertEqual(self.m.status, Status.SETTINGUP)
    self.m.SetStatus(Status.RUNNING)
    self.assertEqual(self.m.status, Status.RUNNING)

    # Should not be able to change status after COMPLETED
    self.m.SetStatus(Status.COMPLETED)
    self.assertEqual(self.m.status, Status.COMPLETED)
    self.m.SetStatus(Status.RUNNING)
    self.assertEqual(self.m.status, Status.COMPLETED)

  def testSetError(self):
    """Test setting a cdm.Module error."""
    self.m.SetError('Sample error message')

    self.assertEqual(self.m._error_message, 'Sample error message')
    self.assertEqual(self.m.status, Status.ERROR)

    # Should not be able to change status after ERROR
    self.m.SetStatus(Status.RUNNING)
    self.assertEqual(self.m.status, Status.ERROR)

    self.assertEqual(
        self.m.Stringify(),
        ['     RuntimeName: Error: Sample error message'])

  def testTheadedModule(self):
    """Tests the thread tracking components of the cdm.Module."""
    self.m.SetContainerCount(5)
    self.m.SetStatus(Status.PROCESSING)

    self.assertEqual(self.m._threads_containers_max, 5)

    self.m.SetThreadState('Thread1', Status.PROCESSING, 'container1')
    self.m.SetThreadState('Thread2', Status.PROCESSING, 'container2')
    self.m.SetThreadState('Thread3', Status.PROCESSING, 'container3')

    self.assertEqual(self.m._threads_containers_completed, 0)
    self.assertEqual(
        self.m._threads,
        {'Thread1': {'status': Status.PROCESSING,'container': 'container1'},
         'Thread2': {'status': Status.PROCESSING,'container': 'container2'},
         'Thread3': {'status': Status.PROCESSING,'container': 'container3'}})
    self.assertEqual(
        self.m.Stringify(),
        ['     RuntimeName: Processing - 0 of 5 containers completed',
         '       Thread1: Processing (container1)',
         '       Thread2: Processing (container2)',
         '       Thread3: Processing (container3)'])

    self.m.SetThreadState('Thread1', Status.COMPLETED, 'container1')
    self.m.SetThreadState('Thread2', Status.COMPLETED, 'container2')
    self.m.SetThreadState('Thread3', Status.COMPLETED, 'container3')

    self.assertEqual(self.m._threads_containers_completed, 3)
    self.assertEqual(
        self.m._threads,
        {'Thread1': {'status': Status.COMPLETED,'container': 'container1'},
         'Thread2': {'status': Status.COMPLETED,'container': 'container2'},
         'Thread3': {'status': Status.COMPLETED,'container': 'container3'}})
    self.assertEqual(
        self.m.Stringify(),
        ['     RuntimeName: Processing - 3 of 5 containers completed',
         '       Thread1: Completed (container1)',
         '       Thread2: Completed (container2)',
         '       Thread3: Completed (container3)'])


  def testStringifyPending(self):
    """Tests the string representation of the module when Pending."""
    self.assertEqual(
        self.m.Stringify(),
        ['     RuntimeName: Pending (Dependency1, Dependency2)'])

  def testStringifyComplete(self):
    """Tests the string representation of the module when Completed."""
    self.m.SetStatus(Status.COMPLETED)
    self.assertEqual(
        self.m.Stringify(),
        ['     RuntimeName: Completed'])

  def testStringifyCompleted(self):
    """Tests the string representation of the module when Cancelled."""
    self.m.SetStatus(Status.CANCELLED)
    self.assertEqual(
        self.m.Stringify(),
        ['     RuntimeName: Cancelled'])

  def testStringifySettingUp(self):
    """Tests the string representation of the module when Setting Up."""
    self.m.SetStatus(Status.SETTINGUP)
    self.assertEqual(
        self.m.Stringify(),
        ['     RuntimeName: Setting Up'])

  def testStringifyRunning(self):
    """Tests the string representation of the module in running modes."""
    self.m.SetStatus(Status.RUNNING)
    self.assertEqual(
        self.m.Stringify(),
        ['     RuntimeName: Running'])

    self.m.SetStatus(Status.PREPROCESSING)
    self.assertEqual(
        self.m.Stringify(),
        ['     RuntimeName: Preprocessing'])

    self.m.SetStatus(Status.POSTPROCESSING)
    self.assertEqual(
        self.m.Stringify(),
        ['     RuntimeName: Postprocessing'])


class CursesDisplayManagerMessageTest(unittest.TestCase):
  """Tests for the Message helper class of the CursesDisplayManager."""

  def setUp(self):
    self.message = Message('message_source', 'message content')
    self.error_message = Message('error_source', 'error content', True)

  def tearDown(self):
    self.message = None
    self.error_message = None

  def testInit(self):
    """Tests initialisation."""
    self.assertEqual(self.message.source, 'message_source')
    self.assertEqual(self.error_message.source, 'error_source')
    self.assertEqual(self.message.content, 'message content')
    self.assertEqual(self.error_message.content, 'error content')
    self.assertEqual(self.message.is_error, False)
    self.assertEqual(self.error_message.is_error, True)

  def testStringify(self):
    """Tests Stringify of cdm.Message."""
    self.assertEqual(
        self.message.Stringify(), '[ message_source ] message content')
    self.assertEqual(
        self.message.Stringify(20), '[ message_source       ] message content')
    self.assertEqual(
        self.error_message.Stringify(), '[ error_source ] error content')
    self.assertEqual(
        self.error_message.Stringify(0, True),
        '[ error_source ] \x1b[31;1merror content\x1b[0m')


class CursesDisplayManagerTest(unittest.TestCase):
  """Tests for the CursesDisplayManager."""

  def setUp(self):
    self.maxDiff = None  # pylint: disable=invalid-name
    self.cdm = CursesDisplayManager()

  def tearDown(self):
    self.cdm = None

  def testInitialisation(self):
    """Tests initialisation."""
    with mock.patch('threading.Lock') as mock_lock:
      cdm = CursesDisplayManager()

      self.assertEqual(cdm._recipe_name, '')
      self.assertEqual(cdm._exception, None)
      self.assertEqual(cdm._preflights, {})
      self.assertEqual(cdm._modules, {})
      self.assertEqual(cdm._messages, [])
      self.assertEqual(cdm._messages_longest_source_len, 0)
      self.assertEqual(cdm._stdscr, None)
      mock_lock.assert_called_once()

  def testStartAndEndCurses(self):
    """Tests the curses set up and tear down."""
    with mock.patch('curses.cbreak') as mock_cbreak, \
        mock.patch('curses.noecho') as mock_noecho, \
        mock.patch('curses.initscr') as mock_initscr:
      self.cdm.StartCurses()

      mock_initscr.assert_called_once_with()
      mock_noecho.assert_called_once_with()
      mock_cbreak.assert_called_once_with()

    with mock.patch('curses.nocbreak') as mock_nocbreak, \
        mock.patch('curses.echo') as mock_echo, \
        mock.patch('curses.endwin') as mock_endwin:
      self.cdm.EndCurses()

      mock_nocbreak.assert_called_once_with()
      mock_echo.assert_called_once_with()
      mock_endwin.assert_called_once_with()

    # An error should trigger a pause
    with mock.patch('curses.nocbreak') as mock_nocbreak, \
        mock.patch('curses.echo') as mock_echo, \
        mock.patch('curses.endwin') as mock_endwin, \
        mock.patch.object(self.cdm, 'Pause') as mock_pause, \
        mock.patch.object(self.cdm._stdscr, 'getmaxyx') as mock_getmaxyx:

      self.cdm.Draw = mock.MagicMock()
      mock_getmaxyx.return_value = 30, 140

      self.cdm.EnqueueMessage('source', 'content', True)
      self.cdm.EndCurses()

      mock_nocbreak.assert_called_once_with()
      mock_echo.assert_called_once_with()
      mock_endwin.assert_called_once_with()
      mock_pause.assert_called_once_with()

  def testSetters(self):
    """Tests the various Set* methods."""
    self.cdm.Draw = mock.MagicMock()

    with mock.patch('curses.cbreak'), \
        mock.patch('curses.noecho'), \
        mock.patch('curses.initscr'):
      self.cdm.StartCurses()

    # Set an exception
    e = Exception('test exception')
    self.cdm.SetException(e)
    self.assertEqual(self.cdm._exception, e)

    # Set recipe name
    self.cdm.SetRecipe('Recipe name')
    self.assertEqual(self.cdm._recipe_name, 'Recipe name')

    # Set error
    with mock.patch.object(self.cdm._stdscr, 'getmaxyx') as mock_getmaxyx:
      mock_getmaxyx.return_value = 30, 140
      self.cdm.EnqueueModule('module_name', [], None)
      self.cdm.SetError('module_name', 'Error message')

    self.assertEqual(self.cdm._modules['module_name'].status, Status.ERROR)
    self.assertEqual(
        self.cdm._modules['module_name']._error_message, 'Error message')
    self.assertEqual(len(self.cdm._messages), 1)
    self.assertEqual(self.cdm._messages[0].source, 'module_name')
    self.assertEqual(self.cdm._messages[0].is_error, True)
    self.assertEqual(self.cdm._messages[0].content, 'Error message')

  def testModules(self):
    """Tests enqueueing of modules."""
    self.cdm.EnqueuePreflight('First Preflight', [], '1st Preflight')
    self.cdm.EnqueuePreflight('Second Preflight', [], '2nd Preflight')
    self.cdm.EnqueueModule('First Module', [], '1st Module')
    self.cdm.EnqueueModule('Second Module', [], '2nd Module')
    self.cdm.EnqueueModule('Third Module', [], '3rd Module')

    self.assertEqual(len(self.cdm._preflights), 2)
    self.assertEqual(len(self.cdm._modules), 3)

    self.assertEqual(
        ['1st Preflight', '2nd Preflight'], list(self.cdm._preflights))
    self.assertEqual(
        ['1st Module', '2nd Module', '3rd Module'], list(self.cdm._modules))

    self.cdm.UpdateModuleStatus('1st Preflight', Status.COMPLETED)
    self.cdm.UpdateModuleStatus('1st Module', Status.COMPLETED)
    self.cdm.SetThreadedModuleContainerCount('2nd Module', 5)
    with mock.patch.object(self.cdm._modules['2nd Module'], 'SetThreadState') \
        as mock_set_thread_state:
      self.cdm.UpdateModuleThreadState(
          '2nd Module', Status.PROCESSING, 'thread1', 'container1')

      self.assertEqual(
          self.cdm._preflights['1st Preflight'].status, Status.COMPLETED)
      self.assertEqual(
          self.cdm._modules['1st Module'].status, Status.COMPLETED)
      self.assertEqual(
          self.cdm._modules['2nd Module']._threads_containers_max, 5)
      mock_set_thread_state.assert_called_once_with(
          'thread1', Status.PROCESSING, 'container1')

  def testPause(self):
    """Tests the pause method."""
    with mock.patch('curses.cbreak'), \
        mock.patch('curses.noecho'), \
        mock.patch('curses.initscr'):
      self.cdm.StartCurses()

    with mock.patch.object(self.cdm._stdscr, 'getmaxyx') as mock_getmaxyx, \
        mock.patch.object(self.cdm._stdscr, 'addstr') as mock_addstr, \
        mock.patch.object(self.cdm._stdscr, 'getkey') as mock_getkey:
      mock_getmaxyx.return_value = 30, 40

      self.cdm.Pause()

      mock_getmaxyx.assert_called_once_with()
      mock_getkey.assert_called_once_with()
      mock_addstr.assert_has_calls([
          mock.call(29, 0, 'Press any key to continue'),
          mock.call(29, 0, '                         ')])

  def testMessages(self):
    """Tests messages usage."""
    self.cdm.Draw = mock.MagicMock()

    with mock.patch('curses.cbreak'), \
        mock.patch('curses.noecho'), \
        mock.patch('curses.initscr'):
      self.cdm.StartCurses()

    with mock.patch.object(self.cdm._stdscr, 'getmaxyx') as mock_getmaxyx:
      mock_getmaxyx.return_value = 30, 60
      self.cdm.EnqueueMessage('source 1', 'content 1')
      self.cdm.EnqueueMessage('a longer source name', 'error message', True)
      self.cdm.EnqueueMessage('source 2', 'this message is longer than the screen width, 60 characters, and will need to be printed on multiple lines.')  # pylint: disable=line-too-long
      self.cdm.EnqueueMessage('source 3', 'this message\nhas a newline in it')

    try:
      raise RuntimeError('Test Exception')
    except RuntimeError as e:
      self.cdm.SetException(e)

    with mock.patch('traceback.format_exception') as mock_format_exception:
      mock_format_exception.return_value = ['line 1\n', 'line 2\n', 'line 3']
      with io.StringIO() as sio, redirect_stdout(sio):
        self.cdm.PrintMessages()
        expected = '\n'.join([
          'Messages',
          '  [ source 1             ] content 1',
          '  [ a longer source name ] \u001b[31;1merror message\u001b[0m',
          '  [ source 2             ] this message is longer than the',
          '  [ source 2             ]   screen width, 60 characters,',
          '  [ source 2             ]   and will need to be printed on',
          '  [ source 2             ]   multiple lines.',
          '  [ source 3             ] this message',
          '  [ source 3             ] has a newline in it',
          '',
          'Exception encountered during execution:',
          'line 1',
          'line 2',
          'line 3\n'])
        self.assertEqual(sio.getvalue(), expected)

  def testDraw(self):
    """Tests drawing to the console via curses."""
    with mock.patch('curses.cbreak'), \
        mock.patch('curses.noecho'), \
        mock.patch('curses.initscr'):
      self.cdm.StartCurses()

    with mock.patch.object(self.cdm._stdscr, 'getmaxyx') as mock_getmaxyx, \
        mock.patch.object(self.cdm, 'Draw'):
      mock_getmaxyx.return_value = 30, 140

      self.cdm.SetRecipe('Recipe name')
      self.cdm.EnqueuePreflight('First Preflight', [], '1st Preflight')
      self.cdm.EnqueuePreflight('Second Preflight', [], '2nd Preflight')
      self.cdm.EnqueueModule('First Module', [], '1st Module')
      self.cdm.EnqueueModule('Second Module', ['1st Module'], '2nd Module')
      self.cdm.EnqueueModule('Third Module', ['1st Module'], '3rd Module')
      self.cdm.EnqueueModule('Fourth Module', ['1st Module'], '4th Module')
      self.cdm.EnqueueModule('Fifth Module',
          ['2nd Module', '3rd Module', '4th Module'], '5th Module')
      self.cdm.UpdateModuleStatus('1st Preflight', Status.COMPLETED)
      self.cdm.UpdateModuleStatus('2nd Preflight', Status.COMPLETED)
      self.cdm.UpdateModuleStatus('1st Module', Status.COMPLETED)
      self.cdm.UpdateModuleStatus('2nd Module', Status.RUNNING)
      self.cdm.UpdateModuleStatus('3rd Module', Status.PROCESSING)
      self.cdm.UpdateModuleStatus('4th Module', Status.PROCESSING)
      self.cdm.SetThreadedModuleContainerCount('3rd Module', 5)
      self.cdm.SetThreadedModuleContainerCount('4th Module', 8)
      self.cdm.UpdateModuleThreadState('3rd Module', Status.RUNNING,
          'thread_3_0', 'container_3_0')
      self.cdm.UpdateModuleThreadState('3rd Module', Status.RUNNING,
          'thread_3_1', 'container_3_1')
      self.cdm.UpdateModuleThreadState('3rd Module', Status.RUNNING,
          'thread_3_2', 'container_3_2')
      self.cdm.UpdateModuleThreadState('3rd Module', Status.COMPLETED,
          'thread_3_0', 'container_3_0')
      self.cdm.UpdateModuleThreadState('3rd Module', Status.RUNNING,
          'thread_3_0', 'container_3_4')
      self.cdm.UpdateModuleThreadState('4th Module', Status.RUNNING,
          'thread_4_0', 'container_4_0')
      self.cdm.UpdateModuleThreadState('4th Module', Status.RUNNING,
          'thread_4_1', 'container_4_1')
      self.cdm.UpdateModuleThreadState('4th Module', Status.RUNNING,
          'thread_4_2', 'container_4_2')
      self.cdm.UpdateModuleThreadState('4th Module', Status.COMPLETED,
          'thread_4_0', 'container_4_0')
      self.cdm.UpdateModuleThreadState('4th Module', Status.RUNNING,
          'thread_4_0', 'container_4_4')

      try:
        raise RuntimeError('Test Exception')
      except RuntimeError as e:
        self.cdm.SetException(e)

      for i in range(10):
        self.cdm.EnqueueMessage('source', f'Message {i}')

    with mock.patch.object(self.cdm._stdscr, 'getmaxyx') as mock_getmaxyx, \
        mock.patch.object(self.cdm._stdscr, 'clear') as mock_clear, \
        mock.patch.object(self.cdm._stdscr, 'addstr') as mock_addstr:
      mock_getmaxyx.return_value = 30, 140

      self.cdm.Draw()

      mock_clear.assert_called_once_with()
      # pylint: disable=line-too-long
      mock_addstr.assert_has_calls([
          mock.call(1, 0,  ' Recipe name'),
          mock.call(2, 0,  '   Preflights:'),
          mock.call(3, 0,  '     1st Preflight: Completed'),
          mock.call(4, 0,  '     2nd Preflight: Completed'),
          mock.call(5, 0,  '   Modules:'),
          mock.call(6, 0,  '     1st Module: Completed'),
          mock.call(7, 0,  '     2nd Module: Running'),
          mock.call(8, 0,  '     3rd Module: Processing - 1 of 5 containers completed'),
          mock.call(9, 0,  '       thread_3_0: Running (container_3_4)'),
          mock.call(10, 0, '       thread_3_1: Running (container_3_1)'),
          mock.call(11, 0, '       thread_3_2: Running (container_3_2)'),
          mock.call(12, 0, '     4th Module: Processing - 1 of 8 containers completed'),
          mock.call(13, 0, '       thread_4_0: Running (container_4_4)'),
          mock.call(14, 0, '       thread_4_1: Running (container_4_1)'),
          mock.call(15, 0, '       thread_4_2: Running (container_4_2)'),
          mock.call(16, 0, '     5th Module: Pending (2nd Module, 3rd Module, 4th Module)'),
          mock.call(18, 0, ' Messages:'),
          mock.call(19, 0, '  [ source ] Message 3'),
          mock.call(20, 0, '  [ source ] Message 4'),
          mock.call(21, 0, '  [ source ] Message 5'),
          mock.call(22, 0, '  [ source ] Message 6'),
          mock.call(23, 0, '  [ source ] Message 7'),
          mock.call(24, 0, '  [ source ] Message 8'),
          mock.call(25, 0, '  [ source ] Message 9'),
          mock.call(28, 0, ' Exception encountered: Test Exception')])
      self.assertEqual(mock_addstr.call_count, 25)
      # pylint: enable=line-too-long
