#!/usr/bin/env python3
import unittest
import time
import math
import threading
from dataclasses import dataclass
from tabulate import tabulate
from typing import List

import cereal.messaging as messaging
from cereal.services import service_list
from system.hardware import HARDWARE, TICI
from system.hardware.tici.power_monitor import get_power
from selfdrive.manager.process_config import managed_processes
from selfdrive.manager.manager import manager_cleanup

SAMPLE_TIME = 8   # seconds to sample power

@dataclass
class Proc:
  name: str
  power: float
  msgs: List[str]
  rtol: float = 0.05
  atol: float = 0.12
  warmup: float = 6.

PROCS = [
  Proc('camerad', 2.1, msgs=['roadCameraState', 'wideRoadCameraState', 'driverCameraState']),
  Proc('modeld', 0.93, atol=0.2, msgs=['modelV2']),
  Proc('dmonitoringmodeld', 0.4, msgs=['driverStateV2']),
  Proc('encoderd', 0.23, msgs=[]),
  Proc('mapsd', 0.05, msgs=['mapRenderState']),
  Proc('navmodeld', 0.05, msgs=['navModel']),
]

def send_llk_msg(done):
  pm = messaging.PubMaster(['liveLocationKalman'])
  msg = messaging.new_message('liveLocationKalman')
  msg.liveLocationKalman.positionGeodetic = {'value': [32.7174, -117.16277, 0], 'std': [0., 0., 0.], 'valid': True}
  msg.liveLocationKalman.calibratedOrientationNED = {'value': [0., 0., 0.], 'std': [0., 0., 0.], 'valid': True}
  msg.liveLocationKalman.status = 'valid'

  # Send liveLocationKalman at 20hz
  while not done.is_set():
    msg.clear_write_flag()
    pm.send('liveLocationKalman', msg)
    time.sleep(1/20)


class TestPowerDraw(unittest.TestCase):

  @classmethod
  def setUpClass(cls):
    if not TICI:
      raise unittest.SkipTest

  def setUp(self):
    HARDWARE.initialize_hardware()
    HARDWARE.set_power_save(False)

    # wait a bit for power save to disable
    time.sleep(5)

  def tearDown(self):
    manager_cleanup()

  def test_camera_procs(self):
    baseline = get_power()
    done = threading.Event()
    thread = threading.Thread(target=send_llk_msg, args=(done,), daemon=True)
    thread.start()

    prev = baseline
    used = {}
    msg_counts = {}
    for proc in PROCS:
      socks = {msg: messaging.sub_sock(msg) for msg in proc.msgs}
      managed_processes[proc.name].start()
      time.sleep(proc.warmup)
      for sock in socks.values():
        messaging.drain_sock_raw(sock)

      now = get_power(SAMPLE_TIME)
      used[proc.name] = now - prev
      prev = now
      for msg,sock in socks.items():
        msg_counts[msg] = len(messaging.drain_sock_raw(sock))

    done.set()
    manager_cleanup()

    tab = [['process', 'expected (W)', 'measured (W)', '# msgs expected', '# msgs received']]
    for proc in PROCS:
      cur = used[proc.name]
      expected = proc.power
      msgs_received = sum(msg_counts[msg] for msg in proc.msgs)
      msgs_expected = int(sum(SAMPLE_TIME * service_list[msg].frequency for msg in proc.msgs))
      tab.append([proc.name, round(expected, 2), round(cur, 2), msgs_expected, msgs_received])
      with self.subTest(proc=proc.name):
        self.assertTrue(math.isclose(cur, expected, rel_tol=proc.rtol, abs_tol=proc.atol))
        self.assertTrue(math.isclose(msgs_expected, msgs_received, rel_tol=.02, abs_tol=2))
    print(tabulate(tab))
    print(f"Baseline {baseline:.2f}W\n")


if __name__ == "__main__":
  unittest.main()
