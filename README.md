# logdrift

A minimal log tailing utility that highlights anomalies and rate spikes in real-time from local or remote sources.

---

## Installation

```bash
pip install logdrift
```

Or install from source:

```bash
git clone https://github.com/yourname/logdrift.git && cd logdrift && pip install .
```

---

## Usage

Tail a local log file and detect anomalies:

```bash
logdrift tail /var/log/app.log
```

Monitor a remote source over SSH:

```bash
logdrift tail user@host:/var/log/nginx/access.log
```

Adjust the sensitivity threshold for rate spike detection:

```bash
logdrift tail /var/log/app.log --threshold 2.5
```

Use it as a library:

```python
from logdrift import Tailer

tailer = Tailer("/var/log/app.log", threshold=2.0)
for event in tailer.stream():
    if event.is_anomaly:
        print(f"[ALERT] {event.line}")
```

---

## Features

- Real-time log tailing from local files or remote hosts (SSH)
- Automatic rate spike detection using rolling window statistics
- Anomaly highlighting with configurable sensitivity
- Lightweight with no heavy dependencies

---

## License

MIT © 2024 yourname