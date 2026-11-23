"""Small, explicitly defined descriptive statistics shared by local experiments."""
import math, os, platform, statistics

def percentile(values, fraction):
    ordered = sorted(values)
    if not ordered: return None
    return ordered[max(0, math.ceil(len(ordered)*fraction)-1)]

def distribution(values):
    if not values: return {'n':0}
    return dict(n=len(values), mean=statistics.mean(values), median=statistics.median(values),
        p10=percentile(values,.1), p90=percentile(values,.9), minimum=min(values), maximum=max(values),
        sample_stddev=statistics.stdev(values) if len(values)>1 else None)

def machine():
    cpu = platform.processor() or 'not reported'
    try:
        for line in open('/proc/cpuinfo', encoding='utf-8'):
            if line.startswith('model name'): cpu=line.split(':',1)[1].strip();break
    except OSError: pass
    return dict(python=platform.python_version(), os=platform.system(), release=platform.release(),
        architecture=platform.machine(), cpu_model=cpu, logical_cpus=os.cpu_count(),
        note='Host-visible CPU count; container quota and other workloads may differ. No hostname collected.')
