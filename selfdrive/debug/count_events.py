#!/usr/bin/env python3
import sys
import math
import datetime
from collections import Counter
from pprint import pprint
from tqdm import tqdm
from typing import List, Tuple, cast

from cereal.services import service_list
from tools.lib.route import Route
from tools.lib.logreader import LogReader

if __name__ == "__main__":
  r = Route(sys.argv[1])

  cnt_valid: Counter = Counter()
  cnt_events: Counter = Counter()

  cams = [s for s in service_list if s.endswith('CameraState')]
  cnt_cameras = dict.fromkeys(cams, 0)

  alerts: List[Tuple[float, str]] = []
  start_time = math.inf
  end_time = -math.inf
  ignition_off = None
  for q in tqdm(r.qlog_paths()):
    if q is None:
      continue
    lr = list(LogReader(q))
    for msg in lr:
      end_time = max(end_time, msg.logMonoTime)
      start_time = min(start_time, msg.logMonoTime)

      if msg.which() == 'carEvents':
        for e in msg.carEvents:
          cnt_events[e.name] += 1
      elif msg.which() == 'controlsState':
        if len(alerts) == 0 or alerts[-1][1] != msg.controlsState.alertType:
          t = (msg.logMonoTime - start_time) / 1e9
          alerts.append((t, msg.controlsState.alertType))
      elif msg.which() == 'pandaStates':
        if ignition_off is None:
          ign = any(ps.ignitionLine or ps.ignitionCan for ps in msg.pandaStates)
          if not ign:
            ignition_off = msg.logMonoTime
      elif msg.which() in cams:
        cnt_cameras[msg.which()] += 1

      if not msg.valid:
        cnt_valid[msg.which()] += 1

  duration = (end_time - start_time) / 1e9

  print("Events")
  pprint(cnt_events)

  print("\n")
  print("Not valid")
  pprint(cnt_valid)

  print("\n")
  print("Cameras")
  for k, v in cnt_cameras.items():
    s = service_list[k]
    expected_frames = int(s.frequency * duration / cast(float, s.decimation))
    print("  ", k.ljust(20), f"{v}, {v/expected_frames:.1%} of expected")

  print("\n")
  print("Alerts")
  for t, a in alerts:
    print(f"{t:8.2f} {a}")
  if ignition_off is not None:
    ignition_off = round((ignition_off - start_time) / 1e9, 2)
  print("Ignition off at",  ignition_off)

  print("\n")
  print("Route duration", datetime.timedelta(seconds=duration))
